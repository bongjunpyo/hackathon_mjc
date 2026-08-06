"""python-dotenv 없이 `.env`를 읽는다.

서버 실행 경로가 달라도 동작하게 파일 위치를 이 모듈 기준으로 잡는다.
셸에서 준 값이 파일보다 우선이다 (`setdefault`) — 테스트가 DATABASE_URL을 갈아끼우고,
데모 당일 임시로 덮어쓸 수도 있어야 한다.
"""

import os
from pathlib import Path

DEFAULT = Path(__file__).with_name(".env")


def load(path=None):
    """`.env`를 os.environ에 반영한다. 여러 번 불러도 안전하다."""
    target = Path(path) if path else DEFAULT
    if not target.is_file():
        return False

    for line in target.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        # `KEY = value` 처럼 등호 양쪽에 공백을 준 파일이 실제로 왔다
        os.environ.setdefault(key.strip(), value.strip())
    return True
