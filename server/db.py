"""DB 연결. 유저 데이터 전용 — 과목 데이터는 data/depts/*.json이 소스다.

**DB가 없어도 서버는 뜬다.** 코어(게스트 → 입력 → 로드맵)는 DB를 쓰지 않으므로
연결 실패를 앱 시작 실패로 만들지 않는다. 10:00에 로그인을 컷하려면 이래야 한다.
"""

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql+psycopg://mjc:mjc@localhost:5432/mjc"
)

_engine = None
_Session = None


class Base(DeclarativeBase):
    pass


def engine():
    global _engine
    if _engine is None:
        _engine = create_engine(DATABASE_URL, pool_pre_ping=True)
    return _engine


def session_factory():
    global _Session
    if _Session is None:
        _Session = sessionmaker(bind=engine(), expire_on_commit=False)
    return _Session


def init_db():
    """마이그레이션 없이 create_all (해커톤 범위).

    실패해도 예외를 밖으로 던지지 않는다 — DB가 안 떠 있는 상태에서도 코어는 살아야 한다.
    로그인 관련 요청만 그때 503으로 떨어진다.
    """
    import models  # noqa: F401  — 테이블 등록

    try:
        Base.metadata.create_all(engine())
        return True
    except Exception as e:
        print(f"[db] 연결 실패 — 로그인 기능만 비활성화됩니다: {e}")
        return False


def use(url):
    """테스트에서 SQLite로 갈아끼운다."""
    global DATABASE_URL, _engine, _Session
    DATABASE_URL, _engine, _Session = url, None, None
