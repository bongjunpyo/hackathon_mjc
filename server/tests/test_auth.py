from datetime import UTC, datetime, timedelta
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

import catalog
import db
import mailer

FIXTURES = Path(__file__).parent / "fixtures"

SIGNUP = {
    "student_id": "202512345",
    "name": "이동제",
    "email": "dj@example.com",
    "password": "hunter22!",
    "dept_id": "itc",
}


@pytest.fixture(autouse=True)
def fresh(monkeypatch, tmp_path):
    monkeypatch.setattr(catalog, "DATA_DIR", FIXTURES)
    db.use(f"sqlite:///{tmp_path / 'test.db'}")
    db.init_db()
    mailer.outbox.clear()
    yield


@pytest.fixture
def client():
    from main import app

    return TestClient(app, follow_redirects=False)


def link_code(client, payload=SIGNUP):
    """회원가입 → 메일함에서 인증 링크 꺼내 클릭 → 교환 코드 반환."""
    client.post("/auth/signup", json=payload)
    verify_url = mailer.outbox[-1]["link"]
    res = client.get(urlparse(verify_url).path + "?" + urlparse(verify_url).query)
    return parse_qs(urlparse(res.headers["location"]).query)["code"][0]


# --- 회원가입 ---


def test_회원가입하면_인증_메일이_나간다(client):
    res = client.post("/auth/signup", json=SIGNUP)

    assert res.status_code == 201
    assert len(mailer.outbox) == 1
    assert mailer.outbox[0]["to"] == "dj@example.com"
    assert "/auth/verify?token=" in mailer.outbox[0]["link"]


def test_회원가입_직후에는_토큰을_주지_않는다(client):
    # "인증해야 로그인 가능" — 가입만으로 로그인되면 인증이 무의미하다
    body = client.post("/auth/signup", json=SIGNUP).json()

    assert "access_token" not in body


def test_학번_중복은_거부한다(client):
    client.post("/auth/signup", json=SIGNUP)

    res = client.post("/auth/signup", json={**SIGNUP, "email": "other@example.com"})

    assert res.status_code == 409
    assert res.json()["error"]["code"]


def test_이메일_중복은_거부한다(client):
    client.post("/auth/signup", json=SIGNUP)

    res = client.post("/auth/signup", json={**SIGNUP, "student_id": "202599999"})

    assert res.status_code == 409


def test_비밀번호는_평문으로_저장하지_않는다(client):
    client.post("/auth/signup", json=SIGNUP)

    import models

    with db.session_factory()() as s:
        user = s.scalar(select(models.User))
    assert SIGNUP["password"] not in user.password_hash


# --- 인증 전 로그인 차단 ---


def test_인증하지_않으면_로그인할_수_없다(client):
    client.post("/auth/signup", json=SIGNUP)

    res = client.post(
        "/auth/login", json={"student_id": SIGNUP["student_id"], "password": SIGNUP["password"]}
    )

    assert res.status_code == 403
    assert "인증" in res.json()["error"]["message"]


# --- 인증 → 자동 로그인 ---


def test_인증_링크를_누르면_교환_코드와_함께_리다이렉트한다(client):
    client.post("/auth/signup", json=SIGNUP)
    verify_url = mailer.outbox[-1]["link"]

    res = client.get(urlparse(verify_url).path + "?" + urlparse(verify_url).query)

    assert res.status_code == 302
    query = parse_qs(urlparse(res.headers["location"]).query)
    assert query["code"][0]
    # JWT가 URL에 실리면 안 된다
    assert "access_token" not in res.headers["location"]


def test_교환_코드로_토큰을_받는다(client):
    code = link_code(client)

    body = client.post("/auth/exchange", json={"code": code}).json()

    assert body["access_token"]
    assert body["refresh_token"]


def test_교환_코드는_한_번만_쓸_수_있다(client):
    code = link_code(client)
    client.post("/auth/exchange", json={"code": code})

    res = client.post("/auth/exchange", json={"code": code})

    assert res.status_code == 400


def test_인증하면_그_뒤로는_로그인도_된다(client):
    link_code(client)

    res = client.post(
        "/auth/login", json={"student_id": SIGNUP["student_id"], "password": SIGNUP["password"]}
    )

    assert res.status_code == 200
    assert res.json()["access_token"]


def test_만료된_인증_링크는_거부한다(client):
    import models

    client.post("/auth/signup", json=SIGNUP)
    with db.session_factory()() as s:
        user = s.scalar(select(models.User))
        user.verification_expires_at = datetime.now(UTC) - timedelta(minutes=1)
        s.add(user)
        s.commit()

    verify_url = mailer.outbox[-1]["link"]
    res = client.get(urlparse(verify_url).path + "?" + urlparse(verify_url).query)

    assert res.status_code == 400


# --- 재발송 ---


def test_재발송하면_새_링크가_나가고_이전_링크는_죽는다(client):
    client.post("/auth/signup", json=SIGNUP)
    old = mailer.outbox[-1]["link"]

    client.post("/auth/resend", json={"email": SIGNUP["email"]})
    new = mailer.outbox[-1]["link"]

    assert new != old
    res = client.get(urlparse(old).path + "?" + urlparse(old).query)
    assert res.status_code == 400


def test_없는_이메일로_재발송해도_가입_여부를_알려주지_않는다(client):
    # 이메일 존재 여부가 새면 계정 열거에 쓰인다
    res = client.post("/auth/resend", json={"email": "nobody@example.com"})

    assert res.status_code == 200
    assert mailer.outbox == []


# --- 로그인 실패 ---


def test_비밀번호가_틀리면_401(client):
    link_code(client)

    res = client.post(
        "/auth/login", json={"student_id": SIGNUP["student_id"], "password": "틀린비밀번호"}
    )

    assert res.status_code == 401


# --- /me ---


def test_토큰_없이_me를_부르면_401(client):
    assert client.get("/me").status_code == 401


def test_me는_내_정보와_이수내역을_낸다(client):
    code = link_code(client)
    token = client.post("/auth/exchange", json={"code": code}).json()["access_token"]
    auth = {"Authorization": f"Bearer {token}"}

    client.put("/me/courses", json={"completed_courses": ["itc-자료구조"]}, headers=auth)
    body = client.get("/me", headers=auth).json()

    assert body["student_id"] == SIGNUP["student_id"]
    assert body["dept_id"] == "itc"
    assert body["completed_courses"] == ["itc-자료구조"]


def test_이수내역은_덮어쓴다(client):
    code = link_code(client)
    token = client.post("/auth/exchange", json={"code": code}).json()["access_token"]
    auth = {"Authorization": f"Bearer {token}"}

    client.put("/me/courses", json={"completed_courses": ["itc-자료구조"]}, headers=auth)
    client.put("/me/courses", json={"completed_courses": ["itc-운영체제"]}, headers=auth)

    assert client.get("/me", headers=auth).json()["completed_courses"] == ["itc-운영체제"]


# --- 코어는 인증과 무관하게 살아야 한다 ---


def test_토큰_없이도_로드맵은_생성된다(client):
    res = client.post(
        "/roadmap",
        json={
            "dept_id": "itc",
            "current_year": 1,
            "current_semester": 1,
            "completed_courses": [],
            "target_job": "네트워크 엔지니어",
        },
    )

    assert res.status_code == 200
