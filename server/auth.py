"""회원가입 · 이메일 인증 · 로그인.

흐름: 가입 → 인증 메일 → 링크 클릭 → 1회용 교환 코드로 리다이렉트 → 토큰 발급.
인증을 마쳐야 로그인할 수 있고, 인증하는 순간 자동으로 로그인된다.

**이 라우터는 코어(게스트 → 입력 → 로드맵)와 분리돼 있다.** 10:00에 로그인을 컷하려면
main.py에서 include_router 한 줄만 빼면 되게 유지한다.
"""

import json
import os
import secrets
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Header, Response
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select

import db
import mailer
import models
from errors import ApiError
from security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    new_verification,
    verify_password,
)

router = APIRouter()

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")
# 인증 직후 프론트가 교환 코드를 들고 도착하는 곳. 새 페이지를 만들지 않아도 되게
# 기존 라우트로 보낸다
LANDING_PATH = os.getenv("VERIFY_LANDING", "/app/input")
EXCHANGE_TTL = timedelta(seconds=60)

# 가입 전 이메일 인증번호. 유저 행이 아직 없어서 DB에 둘 자리가 없다 —
# 스키마를 늘리는 대신 프로세스 메모리에 TTL과 함께 들고 있는다.
# 재시작하면 사라진다(재발송하면 그만). 시도 횟수를 세서 무차별 대입을 막는다.
CODE_TTL = timedelta(minutes=10)
CODE_MAX_TRIES = 5
TICKET_TTL = timedelta(minutes=30)
_email_codes = {}  # email -> {"code", "expires_at", "tries"}
_email_tickets = {}  # ticket -> {"email", "expires_at"}


def _sweep(store):
    now = datetime.now(UTC)
    for key in [k for k, v in store.items() if v["expires_at"] < now]:
        store.pop(key, None)


class SignupIn(BaseModel):
    student_id: str = Field(min_length=4, max_length=32)
    name: str = Field(min_length=1, max_length=64)
    email: EmailStr
    password: str = Field(min_length=8, description="최소 8자")
    dept_id: str
    # 인증번호 방식으로 가입하면 발급되는 티켓. 있으면 가입과 동시에 인증·로그인된다
    email_ticket: str = ""


class LoginIn(BaseModel):
    student_id: str
    password: str


class CheckIdIn(BaseModel):
    student_id: str = Field(min_length=4, max_length=32)


class EmailIn(BaseModel):
    email: EmailStr


class CodeIn(BaseModel):
    code: str


class EmailCodeIn(BaseModel):
    email: EmailStr
    code: str = Field(min_length=6, max_length=6)


class RefreshIn(BaseModel):
    refresh_token: str


class CoursesIn(BaseModel):
    completed_courses: list[str] = []


class RoadmapIn(BaseModel):
    target_job: str = Field(min_length=1)
    roadmap: dict


def _session():
    try:
        return db.session_factory()()
    except Exception as e:
        raise ApiError("DB_UNAVAILABLE", "로그인 기능을 쓸 수 없습니다", status=503) from e


def _aware(value):
    """SQLite는 tz 정보를 잃는다. 비교 전에 UTC로 되돌린다."""
    return value if value.tzinfo else value.replace(tzinfo=UTC)


def _issue_verification(session, user):
    token, expires_at = new_verification()
    user.verification_token = token
    user.verification_expires_at = expires_at
    session.add(user)
    session.commit()
    mailer.send_verification(
        user.email, user.name, f"{BACKEND_URL}/auth/verify?token={token}"
    )


def current_user(session, authorization):
    if not authorization or not authorization.startswith("Bearer "):
        raise ApiError("UNAUTHORIZED", "로그인이 필요합니다", status=401)
    try:
        claims = decode_token(authorization.removeprefix("Bearer "))
    except Exception as e:
        raise ApiError("UNAUTHORIZED", "토큰이 유효하지 않습니다", status=401) from e
    if claims.get("type") != "access":
        raise ApiError("UNAUTHORIZED", "액세스 토큰이 아닙니다", status=401)

    user = session.get(models.User, int(claims["sub"]))
    if not user:
        raise ApiError("UNAUTHORIZED", "사용자를 찾을 수 없습니다", status=401)
    return user


@router.post("/auth/check-id")
def check_id(body: CheckIdIn):
    """가입 폼의 [중복 확인] 버튼. 아이디는 어차피 로그인 화면에서 열거 가능하다."""
    with _session() as session:
        taken = session.scalar(
            select(models.User).where(models.User.student_id == body.student_id)
        )
    return {"available": taken is None}


@router.post("/auth/signup", status_code=201)
def signup(body: SignupIn):
    with _session() as session:
        taken = session.scalar(
            select(models.User).where(
                (models.User.student_id == body.student_id)
                | (models.User.email == body.email)
            )
        )
        if taken:
            field = "아이디" if taken.student_id == body.student_id else "이메일"
            raise ApiError("ALREADY_REGISTERED", f"이미 가입된 {field}입니다", status=409)

        user = models.User(
            student_id=body.student_id,
            name=body.name,
            email=body.email,
            dept_id=body.dept_id,
            password_hash=hash_password(body.password),
        )

        # 인증번호로 이미 확인한 이메일이면 메일을 한 번 더 보내지 않는다.
        # 티켓의 이메일과 가입 이메일이 같아야 한다 — 다르면 남의 인증을 빌려 쓰는 것
        _sweep(_email_tickets)
        ticket = _email_tickets.get(body.email_ticket) if body.email_ticket else None
        if ticket and ticket["email"] == body.email:
            _email_tickets.pop(body.email_ticket, None)
            user.email_verified_at = datetime.now(UTC)
            session.add(user)
            session.commit()
            return _tokens(user)

        session.add(user)
        session.commit()
        _issue_verification(session, user)

    # 토큰을 주지 않는다. 인증을 마쳐야 로그인된다
    return {"message": "인증 메일을 보냈습니다. 메일함을 확인해 주세요."}


@router.post("/auth/email/code")
def send_email_code(body: EmailIn):
    """가입 화면을 떠나지 않고 이메일을 인증한다 — 6자리 번호를 보낸다.

    링크 방식(signup → 메일 → 클릭)은 화면을 벗어나 폼 입력이 날아간다.
    이미 가입된 이메일인지는 알려주지 않는다 (계정 열거 방지) — 번호는 어차피
    메일함 주인만 본다.
    """
    _sweep(_email_codes)
    code = f"{secrets.randbelow(1_000_000):06d}"
    _email_codes[body.email] = {
        "code": code,
        "expires_at": datetime.now(UTC) + CODE_TTL,
        "tries": 0,
    }
    mailer.send_code(body.email, code)
    return {"message": "인증번호를 보냈습니다. 메일함을 확인해 주세요.", "expires_in": 600}


@router.post("/auth/email/verify")
def verify_email_code(body: EmailCodeIn):
    _sweep(_email_codes)
    entry = _email_codes.get(body.email)
    if not entry:
        raise ApiError("CODE_EXPIRED", "인증번호가 만료됐습니다. 다시 받아 주세요", status=400)

    entry["tries"] += 1
    if entry["tries"] > CODE_MAX_TRIES:
        _email_codes.pop(body.email, None)
        raise ApiError("TOO_MANY_TRIES", "시도가 너무 많습니다. 번호를 다시 받아 주세요", status=429)
    if not secrets.compare_digest(entry["code"], body.code):
        raise ApiError("INVALID_CODE", "인증번호가 일치하지 않습니다", status=400)

    _email_codes.pop(body.email, None)
    _sweep(_email_tickets)
    ticket = secrets.token_urlsafe(24)
    _email_tickets[ticket] = {
        "email": body.email,
        "expires_at": datetime.now(UTC) + TICKET_TTL,
    }
    return {"verified": True, "email_ticket": ticket}


@router.post("/auth/resend")
def resend(body: EmailIn):
    with _session() as session:
        user = session.scalar(select(models.User).where(models.User.email == body.email))
        if user and not user.is_verified:
            _issue_verification(session, user)
    # 가입 여부를 알려주지 않는다 — 계정 열거 방지
    return {"message": "가입된 이메일이라면 인증 메일을 다시 보냈습니다."}


@router.get("/auth/verify")
def verify(token: str):
    with _session() as session:
        user = session.scalar(
            select(models.User).where(models.User.verification_token == token)
        )
        if not user or not user.verification_expires_at:
            raise ApiError("INVALID_TOKEN", "인증 링크가 유효하지 않습니다", status=400)
        if _aware(user.verification_expires_at) < datetime.now(UTC):
            raise ApiError(
                "TOKEN_EXPIRED", "인증 링크가 만료됐습니다. 재발송해 주세요", status=400
            )

        user.email_verified_at = datetime.now(UTC)
        user.verification_token = None
        user.verification_expires_at = None
        user.exchange_code = secrets.token_urlsafe(24)
        user.exchange_expires_at = datetime.now(UTC) + EXCHANGE_TTL
        session.add(user)
        session.commit()
        code = user.exchange_code

    return Response(
        status_code=302,
        headers={"location": f"{FRONTEND_URL}{LANDING_PATH}?code={code}"},
    )


@router.post("/auth/exchange")
def exchange(body: CodeIn):
    with _session() as session:
        user = session.scalar(
            select(models.User).where(models.User.exchange_code == body.code)
        )
        if not user or not user.exchange_expires_at:
            raise ApiError("INVALID_CODE", "코드가 유효하지 않습니다", status=400)
        if _aware(user.exchange_expires_at) < datetime.now(UTC):
            raise ApiError("CODE_EXPIRED", "코드가 만료됐습니다. 다시 로그인해 주세요", status=400)

        user.exchange_code = None  # 1회용
        user.exchange_expires_at = None
        session.add(user)
        session.commit()
        return _tokens(user)


@router.post("/auth/login")
def login(body: LoginIn):
    with _session() as session:
        user = session.scalar(
            select(models.User).where(models.User.student_id == body.student_id)
        )
        if not user or not verify_password(body.password, user.password_hash):
            raise ApiError("BAD_CREDENTIALS", "학번 또는 비밀번호가 틀렸습니다", status=401)
        if not user.is_verified:
            raise ApiError(
                "EMAIL_NOT_VERIFIED", "이메일 인증을 먼저 완료해 주세요", status=403
            )
        return _tokens(user)


@router.post("/auth/refresh")
def refresh(body: RefreshIn):
    try:
        claims = decode_token(body.refresh_token)
    except Exception as e:
        raise ApiError("UNAUTHORIZED", "리프레시 토큰이 유효하지 않습니다", status=401) from e
    if claims.get("type") != "refresh":
        raise ApiError("UNAUTHORIZED", "리프레시 토큰이 아닙니다", status=401)
    return {"access_token": create_access_token(int(claims["sub"]))}


@router.get("/me")
def me(authorization: str = Header(default=None)):
    with _session() as session:
        user = current_user(session, authorization)
        return {
            "student_id": user.student_id,
            "name": user.name,
            "email": user.email,
            "dept_id": user.dept_id,
            "email_verified": user.is_verified,
            "completed_courses": [c.course_id for c in user.completed],
            "saved_roadmaps": [
                {"target_job": r.target_job, "roadmap": json.loads(r.roadmap_json)}
                for r in user.roadmaps
            ],
        }


@router.put("/me/courses")
def put_courses(body: CoursesIn, authorization: str = Header(default=None)):
    with _session() as session:
        user = current_user(session, authorization)
        user.completed.clear()
        session.flush()
        for course_id in body.completed_courses:
            user.completed.append(
                models.CompletedCourse(course_id=course_id, year=0, semester=0)
            )
        session.add(user)
        session.commit()
        return {"completed_courses": [c.course_id for c in user.completed]}


@router.post("/me/roadmaps", status_code=201)
def save_roadmap(body: RoadmapIn, authorization: str = Header(default=None)):
    """같은 직무로 다시 저장하면 덮어쓴다 — 시연 중 여러 번 눌러도 목록이 쌓이지 않게."""
    with _session() as session:
        user = current_user(session, authorization)
        existing = next(
            (r for r in user.roadmaps if r.target_job == body.target_job), None
        )
        if existing:
            existing.roadmap_json = json.dumps(body.roadmap, ensure_ascii=False)
            session.add(existing)
        else:
            user.roadmaps.append(
                models.SavedRoadmap(
                    target_job=body.target_job,
                    roadmap_json=json.dumps(body.roadmap, ensure_ascii=False),
                )
            )
            session.add(user)
        session.commit()
        return {"target_job": body.target_job}


def _tokens(user):
    return {
        "access_token": create_access_token(user.id),
        "refresh_token": create_refresh_token(user.id),
    }
