"""에러 응답 형식 — `{ error: { code, message } }`.

동결 스펙에는 없지만 프론트 `lib/api.js`가 `err?.error?.message`를 읽는다.
구현이 기준이므로 여기 맞춘다 (PR #7 협의).
"""

from fastapi import Request
from fastapi.responses import JSONResponse


class ApiError(Exception):
    def __init__(self, code, message, status=400):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = status


async def api_error_handler(_: Request, exc: ApiError):
    return JSONResponse(
        status_code=exc.status,
        content={"error": {"code": exc.code, "message": exc.message}},
    )


# 입력 검증 실패는 FastAPI 기본 형식(`{detail: [...]}`)으로 나가서 프론트가 못 읽는다.
# 사람이 읽을 한 줄로 접어 같은 봉투에 담는다
_FIELD_NAMES = {
    "password": "비밀번호",
    "email": "이메일",
    "student_id": "학번",
    "name": "이름",
    "dept_id": "학과",
    "target_job": "목표 직무",
}


async def validation_error_handler(_: Request, exc):
    first = exc.errors()[0]
    field = str(first["loc"][-1])
    message = f"{_FIELD_NAMES.get(field, field)}: {first['msg']}"
    return JSONResponse(
        status_code=422,
        content={"error": {"code": "VALIDATION_ERROR", "message": message}},
    )


async def db_error_handler(_: Request, exc):
    """SQLAlchemy는 세션 생성이 아니라 **첫 쿼리에서** 연결한다.

    세션 생성만 try로 감싸면 OperationalError가 라우트 밖에서 터져 500 + 프론트가
    못 읽는 형식이 된다. DB가 없어도 코어는 돌아야 하므로, 로그인 계열만 503으로
    떨어뜨리고 형식을 맞춘다.
    """
    return JSONResponse(
        status_code=503,
        content={
            "error": {
                "code": "DB_UNAVAILABLE",
                "message": "로그인 기능을 쓸 수 없습니다. 게스트로 계속 진행할 수 있습니다",
            }
        },
    )
