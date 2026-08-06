from datetime import UTC, datetime, timedelta

import pytest

from security import (
    TokenError,
    VERIFICATION_TTL,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    new_verification,
    verify_password,
)


# --- 비밀번호 ---


def test_해시는_원문을_담지_않는다():
    h = hash_password("hunter22")

    assert "hunter22" not in h
    assert verify_password("hunter22", h) is True


def test_틀린_비밀번호는_거부한다():
    assert verify_password("wrong", hash_password("hunter22")) is False


def test_같은_비밀번호도_해시가_매번_다르다():
    # salt가 붙는지. 같으면 레인보우 테이블에 그대로 노출된다
    assert hash_password("hunter22") != hash_password("hunter22")


def test_72바이트를_넘는_비밀번호도_처리한다():
    # bcrypt는 72바이트 초과를 거부한다. 한글은 3바이트라 24자면 넘는다
    long_korean = "비밀번호" * 10  # 120바이트

    h = hash_password(long_korean)

    assert verify_password(long_korean, h) is True


# --- JWT ---


def test_액세스_토큰에서_사용자를_꺼낸다():
    token = create_access_token(user_id=7)

    claims = decode_token(token)

    assert claims["sub"] == "7"
    assert claims["type"] == "access"


def test_리프레시_토큰은_종류가_다르다():
    claims = decode_token(create_refresh_token(user_id=7))

    assert claims["type"] == "refresh"


def test_만료된_토큰은_거부한다():
    past = datetime.now(UTC) - timedelta(hours=1)
    token = create_access_token(user_id=7, expires_at=past)

    with pytest.raises(TokenError):
        decode_token(token)


def test_변조된_토큰은_거부한다():
    token = create_access_token(user_id=7)
    tampered = token[:-4] + ("aaaa" if not token.endswith("aaaa") else "bbbb")

    with pytest.raises(TokenError):
        decode_token(tampered)


# --- 이메일 인증 토큰 ---


def test_인증_토큰은_30분_뒤_만료된다():
    token, expires_at = new_verification()

    assert token
    delta = expires_at - datetime.now(UTC)
    assert timedelta(minutes=29) < delta <= VERIFICATION_TTL


def test_인증_토큰은_매번_다르다():
    assert new_verification()[0] != new_verification()[0]
