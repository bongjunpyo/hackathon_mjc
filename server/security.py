"""비밀번호 해싱 · JWT · 이메일 인증 토큰.

passlib 대신 bcrypt를 직접 쓴다 — passlib 1.7.4가 bcrypt 5.x에서 깨진다
(8바이트 비밀번호에도 "72바이트 초과" 오류). 해싱 방식은 동일하다.
"""

import hashlib
import os
import secrets
from datetime import UTC, datetime, timedelta

import bcrypt
import jwt

import envfile

# 아래 os.getenv는 import 시점에 돈다. main.py의 load()에만 의존하면 이 모듈을 직접
# import하는 경로에서 .env의 JWT_SECRET이 무시되고 개발용 기본키로 토큰이 서명된다
envfile.load()

SECRET = os.getenv("JWT_SECRET", "dev-only-secret-바꿔야-한다")
ALGORITHM = "HS256"

ACCESS_TTL = timedelta(hours=12)  # 해커톤 시연 동안 만료되지 않게
REFRESH_TTL = timedelta(days=7)
VERIFICATION_TTL = timedelta(minutes=30)


class TokenError(Exception):
    pass


def hash_password(password):
    return bcrypt.hashpw(_bcrypt_safe(password), bcrypt.gensalt()).decode()


def verify_password(password, hashed):
    return bcrypt.checkpw(_bcrypt_safe(password), hashed.encode())


def _bcrypt_safe(password):
    """bcrypt는 72바이트를 넘기면 거부한다. 한글은 자당 3바이트라 24자면 넘는다.

    잘라내면 뒷부분이 무시되므로, 넘칠 때만 sha256으로 한 번 접어 길이를 고정한다.
    """
    raw = password.encode()
    if len(raw) <= 72:
        return raw
    return hashlib.sha256(raw).hexdigest().encode()


def _create(user_id, token_type, ttl, expires_at=None):
    return jwt.encode(
        {
            "sub": str(user_id),
            "type": token_type,
            "exp": expires_at or datetime.now(UTC) + ttl,
        },
        SECRET,
        algorithm=ALGORITHM,
    )


def create_access_token(user_id, expires_at=None):
    return _create(user_id, "access", ACCESS_TTL, expires_at)


def create_refresh_token(user_id, expires_at=None):
    return _create(user_id, "refresh", REFRESH_TTL, expires_at)


def decode_token(token):
    try:
        return jwt.decode(token, SECRET, algorithms=[ALGORITHM])
    except jwt.PyJWTError as e:
        raise TokenError(str(e)) from e


def new_verification():
    """(토큰, 만료시각). 재발송하면 이전 토큰은 덮어써져 무효가 된다."""
    return secrets.token_urlsafe(32), datetime.now(UTC) + VERIFICATION_TTL
