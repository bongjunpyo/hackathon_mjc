"""API 표면. 계약 원본은 ../docs/DESIGN.md §5 (동결).

라우트 등록 순서가 중요하다 — 정적 catch-all이 API 경로를 삼키면 화면 요청이
백엔드로 넘어가 502가 난다 (프론트에서 실제로 발생, PR #7).
API 라우터를 먼저 걸고 StaticFiles는 맨 마지막에 마운트한다.
"""

import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import auth
import catalog
import db
import envfile
from catalog import CatalogError
from sqlalchemy.exc import SQLAlchemyError

from errors import (
    ApiError,
    api_error_handler,
    db_error_handler,
    validation_error_handler,
)
from jobmap import choices as job_choices
from jobmap import match_labels
from loop import generate_roadmap
from planner import generate as generate_roadmap_plan
from report import build_report


@asynccontextmanager
async def lifespan(_):
    db.init_db()  # 실패해도 예외를 던지지 않는다 — 코어는 DB 없이 돈다
    yield


# DATABASE_URL·ANTHROPIC_API_KEY 등을 읽는 코드보다 먼저 와야 한다
envfile.load()

app = FastAPI(title="MJC 취업 로드맵 에이전트", lifespan=lifespan)
app.add_exception_handler(ApiError, api_error_handler)
app.add_exception_handler(RequestValidationError, validation_error_handler)
app.add_exception_handler(SQLAlchemyError, db_error_handler)

# 부가 기능. 10:00 컷 시 이 한 줄만 빼면 코어는 그대로 돈다
app.include_router(auth.router)


class RoadmapRequest(BaseModel):
    dept_id: str
    current_year: int
    current_semester: int
    completed_courses: list[str] = []
    target_job: str


@app.get("/depts")
def get_depts():
    return catalog.list_depts()


@app.post("/roadmap")
def post_roadmap(req: RoadmapRequest):
    try:
        dept = catalog.load_dept(req.dept_id)
        completed, missing = catalog.resolve(req.dept_id, req.completed_courses)
    except CatalogError as e:
        raise ApiError("DEPT_NOT_FOUND", str(e), status=404) from e

    # 오타 하나로 조용히 일반 로드맵이 나가면 "직무 역산"이라는 주장이 무너진다.
    # careers가 비어 있으면(Tier 2 추출 누락) 비교 대상이 없으므로 막지 않는다
    # 데모 대본 직무는 talent_types에 있고 진로는 careers에 있다. 둘 다 받는다 (이슈 #40)
    allowed = job_choices(dept)
    if allowed and req.target_job not in allowed:
        raise ApiError(
            "UNKNOWN_JOB",
            f"'{req.target_job}'는 {dept['dept_name']}의 직무가 아닙니다. "
            f"고를 수 있는 직무: {', '.join(allowed)}",
            status=400,
        )

    spec = {
        "dept": dept,
        "target_job": req.target_job,
        "current_year": req.current_year,
        "current_semester": req.current_semester,
        "completed": completed,
        # 1학년 1학기면 0학기 이수. 학기는 연 2회로 고정 (2·3년제 공통)
        "completed_semesters": (req.current_year - 1) * 2 + (req.current_semester - 1),
    }

    result, generator = _run(spec)
    result["generator"] = generator
    # 진로에 대응하는 교육과정 라벨이 없을 수 있다. 로드맵은 내되 "직무 맞춤이 안 됐다"를
    # 숨기지 않는다 — 조용히 일반 로드맵을 주면 "직무 역산"이 거짓이 된다
    labels = sorted({c["talent_type"] for c in dept["courses"] if c.get("talent_type")})
    matched = set(match_labels(req.target_job, labels))
    # 생성기가 무엇이든 서버가 붙인다 — planner는 달지만 LLM 에이전트는 달지 않는다
    related = 0
    for semester in result["semesters"]:
        for course in semester["courses"]:
            course["job_related"] = course.get("talent_type") in matched
            related += course["job_related"]
    result["job_match"] = {
        "matched_labels": sorted(matched),
        "related_courses": related,
        "note": ""
        if matched
        else f"'{req.target_job}'에 대응하는 교육과정 인재양성유형이 없습니다. "
        "졸업요건만 맞춘 일반 로드맵입니다",
    }
    if missing:
        # 프론트 체크박스와 데이터가 어긋난 신호. 코어를 죽이지는 않되 숨기지도 않는다
        result["unknown_courses"] = missing
    return result


def pick_generator():
    """API 키가 있으면 LLM 에이전트, 없으면 결정론적 planner.

    두 생성기가 같은 계약(spec, feedback, attempt)이라 loop에 그대로 꽂힌다.
    키가 없어도 데모는 돌아야 하므로 planner가 항상 대기한다 — mailer가 SMTP 없으면
    콘솔로 떨어지는 것과 같은 구조다.
    """
    # .env가 아직 안 읽혔을 수도 있다 — 여러 번 불러도 안전하다
    envfile.load()
    if os.getenv("ANTHROPIC_API_KEY"):
        from agent import generate as llm_generate

        return llm_generate
    return generate_roadmap_plan


def _run(spec):
    """LLM이 죽어도 로드맵은 나온다. 무엇이 돌았는지는 응답에 남긴다."""
    chosen = pick_generator()
    label = "agent (LLM)" if getattr(chosen, "__module__", "") == "agent" else "planner"
    try:
        return generate_roadmap(spec, chosen), label
    except Exception as e:
        if chosen is generate_roadmap_plan:
            raise
        print(f"[roadmap] LLM 실패({e}) — planner로 대체", flush=True)
        return generate_roadmap(spec, generate_roadmap_plan), "planner (LLM 실패)"


@app.get("/report/{dept_id}")
def get_report(dept_id: str):
    try:
        dept = catalog.load_dept(dept_id)
    except CatalogError as e:
        raise ApiError("DEPT_NOT_FOUND", str(e), status=404) from e
    return build_report(dept)


# 정적 서빙은 반드시 맨 마지막. web/dist가 없어도 서버는 떠야 한다 (P3 빌드 전 API 테스트)
_dist = Path(__file__).parent.parent / "web" / "dist"
if _dist.is_dir():
    app.mount("/", StaticFiles(directory=_dist, html=True), name="web")
