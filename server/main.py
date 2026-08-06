"""API 표면. 계약 원본은 ../docs/DESIGN.md §5 (동결).

라우트 등록 순서가 중요하다 — 정적 catch-all이 API 경로를 삼키면 화면 요청이
백엔드로 넘어가 502가 난다 (프론트에서 실제로 발생, PR #7).
API 라우터를 먼저 걸고 StaticFiles는 맨 마지막에 마운트한다.
"""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import auth
import catalog
import db
from catalog import CatalogError
from errors import ApiError, api_error_handler
from loop import generate_roadmap
from planner import naive_generate


@asynccontextmanager
async def lifespan(_):
    db.init_db()  # 실패해도 예외를 던지지 않는다 — 코어는 DB 없이 돈다
    yield


app = FastAPI(title="MJC 취업 로드맵 에이전트", lifespan=lifespan)
app.add_exception_handler(ApiError, api_error_handler)

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

    spec = {
        "dept": dept,
        "target_job": req.target_job,
        "current_year": req.current_year,
        "current_semester": req.current_semester,
        "completed": completed,
        # 1학년 1학기면 0학기 이수. 학기는 연 2회로 고정 (2·3년제 공통)
        "completed_semesters": (req.current_year - 1) * 2 + (req.current_semester - 1),
    }

    result = generate_roadmap(spec, naive_generate)
    if missing:
        # 프론트 체크박스와 데이터가 어긋난 신호. 코어를 죽이지는 않되 숨기지도 않는다
        result["unknown_courses"] = missing
    return result


@app.get("/report/{dept_id}")
def get_report(dept_id: str):
    try:
        catalog.load_dept(dept_id)
    except CatalogError as e:
        raise ApiError("DEPT_NOT_FOUND", str(e), status=404) from e
    # 트랙 B는 6단계에서. 수치를 지어내지 않고 빈 목록을 낸다
    return {"jobs": []}


# 정적 서빙은 반드시 맨 마지막. web/dist가 없어도 서버는 떠야 한다 (P3 빌드 전 API 테스트)
_dist = Path(__file__).parent.parent / "web" / "dist"
if _dist.is_dir():
    app.mount("/", StaticFiles(directory=_dist, html=True), name="web")
