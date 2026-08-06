"""API 표면. 계약 원본은 ../docs/DESIGN.md §5 (동결).

라우트 등록 순서가 중요하다 — 정적 catch-all이 API 경로를 삼키면 화면 요청이
백엔드로 넘어가 502가 난다 (프론트에서 실제로 발생, PR #7).
API 라우터를 먼저 걸고 StaticFiles는 맨 마지막에 마운트한다.
"""

import envfile

# **다른 import보다 먼저 실행돼야 한다.** db·security·auth·mailer는 모듈 최상단에서
# os.getenv를 읽는데, 그 코드는 import 시점에 돈다. 아래 import들 뒤에서 load()를
# 부르면 이미 늦어서 .env의 JWT_SECRET·DATABASE_URL이 조용히 무시된다.
envfile.load()

import logging  # noqa: E402
import os  # noqa: E402
from contextlib import asynccontextmanager  # noqa: E402
from pathlib import Path  # noqa: E402

from fastapi import FastAPI  # noqa: E402
from fastapi.exceptions import RequestValidationError  # noqa: E402
from fastapi.responses import FileResponse  # noqa: E402
from fastapi.staticfiles import StaticFiles  # noqa: E402
from pydantic import BaseModel  # noqa: E402

import agent  # noqa: E402
import auth  # noqa: E402
import catalog  # noqa: E402
import db  # noqa: E402
from catalog import CatalogError  # noqa: E402
from sqlalchemy.exc import SQLAlchemyError  # noqa: E402

from errors import (  # noqa: E402
    ApiError,
    api_error_handler,
    db_error_handler,
    validation_error_handler,
)
from jobmap import choices as job_choices  # noqa: E402
from jobmap import match_labels  # noqa: E402
from loop import generate_roadmap  # noqa: E402
from planner import generate as generate_roadmap_plan  # noqa: E402
from report import build_report  # noqa: E402

log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_):
    db.init_db()  # 실패해도 예외를 던지지 않는다 — 코어는 DB 없이 돈다
    yield


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
    # 빈 값 = 직무 미정. 커버리지 1위 직무를 추천해 그걸로 짠다 (8/7 02시 팀 결정)
    target_job: str = ""


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

    # 직무 미정이면 커버리지(직무 라벨 학점 합) 1위 직무를 추천해 그걸로 짠다.
    # 막아버리면 "아직 못 정한" 학생 — 이 서비스가 가장 필요한 사용자 — 를 내쫓는 셈이다
    target_job = req.target_job
    recommended = _recommend_jobs(dept) if not target_job else None
    if recommended:
        target_job = recommended[0]["job"]

    # 오타 하나로 조용히 일반 로드맵이 나가면 "직무 역산"이라는 주장이 무너진다.
    # 둘 다 받는다 — talent_types는 교과과정표 비고 열의 라벨(과목과 직접 연결),
    # careers는 학과 소개 페이지의 진로다. 한쪽만 보면 다른 쪽 값이 전부 400이 된다.
    # 비어 있으면(Tier 2 추출 누락) 비교 대상이 없으므로 막지 않는다
    jobs = job_choices(dept)
    if req.target_job and jobs and req.target_job not in jobs:
        raise ApiError(
            "UNKNOWN_JOB",
            f"'{req.target_job}'는 {dept['dept_name']}의 직무가 아닙니다. "
            f"고를 수 있는 직무: {', '.join(jobs)}",
            status=400,
        )

    spec = {
        "dept": dept,
        "target_job": target_job,
        "current_year": req.current_year,
        "current_semester": req.current_semester,
        "completed": completed,
        # 1학년 1학기면 0학기 이수. 학기는 연 2회로 고정 (2·3년제 공통)
        "completed_semesters": (req.current_year - 1) * 2 + (req.current_semester - 1),
    }

    result = _generate(spec)
    # 직무를 지정했든 추천받았든 **항상** 넣는다. 추천일 때만 넣으면 프론트가
    # body.target_job을 그대로 못 읽고 분기해야 한다
    result["target_job"] = target_job
    if recommended:
        # 프론트가 "추천된 직무로 짰다"를 표시하고, 다른 후보로 바꿔 재생성할 수 있게
        result["job_recommended"] = True
        result["recommended_jobs"] = recommended[:5]
    # 진로에 대응하는 교육과정 라벨이 없을 수 있다. 로드맵은 내되 "직무 맞춤이 안 됐다"를
    # 숨기지 않는다 — 조용히 일반 로드맵을 주면 "직무 역산"이 거짓이 된다
    labels = sorted({c["talent_type"] for c in dept["courses"] if c.get("talent_type")})
    matched = set(match_labels(target_job, labels))
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
        else f"'{target_job}'에 대응하는 교육과정 인재양성유형이 없습니다. "
        "졸업요건만 맞춘 일반 로드맵입니다",
    }

    if missing:
        # 프론트 체크박스와 데이터가 어긋난 신호. 코어를 죽이지는 않되 숨기지도 않는다
        result["unknown_courses"] = missing
    return result


def _recommend_jobs(dept):
    """직무 미정 학생에게 줄 추천 순위. 라벨별 배정 학점이 근거다 — 트랙 B 커버리지와
    같은 계산이라, "왜 이 직무냐"에 학과 데이터로 답할 수 있다.

    **전공만 센다.** 트랙 B는 분모가 전공 학점이라, 전 과목을 세면 두 화면이 같은
    직무에 다른 숫자를 말한다 — 유아교육과에서 95학점 중 27학점이 비전공이었다.
    """
    by_job = {}
    for c in dept["courses"]:
        label = c.get("talent_type")
        if label and c.get("category") == "전공":
            entry = by_job.setdefault(label, {"job": label, "credits": 0, "courses": 0})
            entry["credits"] += c["credits"]
            entry["courses"] += 1
    return sorted(by_job.values(), key=lambda e: (-e["credits"], e["job"]))


def _generate(spec):
    """규칙 엔진이 메인이다 (8/7 02시 팀 결정 — 학교 실데이터 기반 결정론 추천).

    근거가 전부 데이터에 있어 "왜 이 과목이냐"에 답할 수 있고, 응답이 즉시이며,
    토큰 비용이 없다. LLM은 비교 데모용 보조로 남긴다 — `MJC_ENGINE=llm`일 때만
    시도하고, 실패하면 규칙으로 떨어진다. 검증기 루프는 어느 쪽이든 그대로 돈다.

    어느 엔진이 짰는지 `engine`으로 알린다. 조용히 바뀌면 결과의 출처를
    오인하게 된다.
    """
    envfile.load()  # 여러 번 불러도 안전하다
    if os.getenv("MJC_ENGINE") != "llm" or not os.getenv("ANTHROPIC_API_KEY"):
        return {**generate_roadmap(spec, generate_roadmap_plan), "engine": "rule"}
    try:
        return {**generate_roadmap(spec, agent.generate), "engine": "llm"}
    except Exception:
        log.exception("LLM 로드맵 생성 실패 — 규칙 플래너로 폴백")
        return {
            **generate_roadmap(spec, generate_roadmap_plan),
            "engine": "rule (llm-failed)",
        }


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

    # 화면 경로는 전부 /app/* 아래다 (PR #7). StaticFiles(html=True)는 루트만
    # index.html로 떨어뜨려서, 시연 중 /app/*에서 새로고침 한 번이면 404가 났다
    # (이슈 #50). API와 안 겹치는 /app/*만 SPA 폴백한다
    @app.get("/app/{rest:path}")
    def spa(rest: str):
        return FileResponse(_dist / "index.html")

    app.mount("/", StaticFiles(directory=_dist, html=True), name="web")
