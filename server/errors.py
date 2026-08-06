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
