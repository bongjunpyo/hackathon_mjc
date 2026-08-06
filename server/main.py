"""API 표면. 계약 원본은 ../docs/DESIGN.md §5 (동결).

라우트 등록 순서가 중요하다 — 정적 catch-all이 API 경로를 삼키면 화면 요청이
백엔드로 넘어가 502가 난다 (프론트에서 실제로 발생, PR #7).
API 라우터를 먼저 걸고 StaticFiles는 맨 마지막에 마운트한다.
"""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import agent
import auth
import catalog
import db
from catalog import CatalogError
from sqlalchemy.exc import SQLAlchemyError

from errors import (
    ApiError,
    api_error_handler,
    db_error_handler,
    validation_error_handler,
)
from loop import generate_roadmap
from planner import generate as generate_roadmap_plan
from report import build_report

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
    # 둘 다 받는다 — talent_types는 교과과정표 비고 열의 라벨(과목과 직접 연결),
    # careers는 학과 소개 페이지의 진로다. 한쪽만 보면 다른 쪽 값이 전부 400이 된다.
    # 비어 있으면(Tier 2 추출 누락) 비교 대상이 없으므로 막지 않는다
    jobs = (dept.get("talent_types") or []) + (dept.get("careers") or [])
    if jobs and req.target_job not in jobs:
        raise ApiError(
            "UNKNOWN_JOB",
            f"'{req.target_job}'는 {dept['dept_name']}의 직무가 아닙니다. "
            f"고를 수 있는 직무: {', '.join(jobs)}",
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

    result = _generate(spec)
    if missing:
        # 프론트 체크박스와 데이터가 어긋난 신호. 코어를 죽이지는 않되 숨기지도 않는다
        result["unknown_courses"] = missing
    return result


def _generate(spec):
    """LLM으로 짜고, 실패하면 규칙 플래너로 떨어진다.

    폴백을 두는 이유는 발표 중 API 키 만료·레이트리밋·네트워크로 데모가 통째로
    죽는 것을 막기 위해서다. 검증기 루프는 어느 쪽이든 그대로 돈다.

    어느 엔진이 짰는지 `engine`으로 알린다. 폴백이 조용히 일어나면 "LLM이 짠다"는
    주장을 확인할 방법이 없어진다 — 규칙 코드 결과를 LLM 결과로 오인하게 된다.
    """
    try:
        return {**generate_roadmap(spec, agent.generate), "engine": "llm"}
    except Exception:
        log.exception("LLM 로드맵 생성 실패 — 규칙 플래너로 폴백")
        return {**generate_roadmap(spec, generate_roadmap_plan), "engine": "rule"}


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
