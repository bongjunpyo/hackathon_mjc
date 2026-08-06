"""유저 데이터 테이블. 스키마 원본은 ../docs/DESIGN.md §5.

`completed_courses`는 **course_id**로 저장한다 (이슈 #4). 과목명으로 저장하면
Ⅰ/I/1 표기 혼재 때문에 로그인 경로에서 매칭이 깨진다.
"""

from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db import Base


def _now():
    return datetime.now(UTC)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(64))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    dept_id: Mapped[str] = mapped_column(String(32))
    password_hash: Mapped[str] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    # 이메일 인증. 재발송하면 토큰이 덮어써져 이전 링크는 무효가 된다
    email_verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )
    verification_token: Mapped[str | None] = mapped_column(
        String(64), index=True, default=None
    )
    verification_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )

    # 인증 직후 1회용 교환 코드. JWT를 리다이렉트 URL에 싣지 않기 위한 것 —
    # 방문기록에 남아도 이미 소진돼 쓸모가 없다 (OAuth authorization code와 같은 방식)
    exchange_code: Mapped[str | None] = mapped_column(String(64), index=True, default=None)
    exchange_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )

    completed: Mapped[list["CompletedCourse"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    roadmaps: Mapped[list["SavedRoadmap"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )

    @property
    def is_verified(self):
        return self.email_verified_at is not None


class CompletedCourse(Base):
    __tablename__ = "completed_courses"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    course_id: Mapped[str] = mapped_column(String(128))
    year: Mapped[int] = mapped_column(Integer)
    semester: Mapped[int] = mapped_column(Integer)

    user: Mapped[User] = relationship(back_populates="completed")


class SavedRoadmap(Base):
    __tablename__ = "saved_roadmaps"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    target_job: Mapped[str] = mapped_column(String(128))
    roadmap_json: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    user: Mapped[User] = relationship(back_populates="roadmaps")
