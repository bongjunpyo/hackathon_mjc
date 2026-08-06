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
    # 필수 약관 동의 — 없으면 서버가 400으로 막는다
    "agreed_terms": True,
    "agreed_privacy": True,
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


# --- 비밀번호 규칙 ---


def test_짧은_비밀번호는_거부한다(client):
    res = client.post("/auth/signup", json={**SIGNUP, "password": "1234"})

    assert res.status_code == 422
    # 검증 실패도 lib/api.js가 읽는 형식이어야 한다
    assert res.json()["error"]["message"]
    assert res.json()["error"]["code"] == "VALIDATION_ERROR"


def test_이메일_형식이_아니면_거부한다(client):
    res = client.post("/auth/signup", json={**SIGNUP, "email": "골뱅이없음"})

    assert res.status_code == 422
    assert res.json()["error"]["message"]


# --- 로드맵 저장 ---


def logged_in(client):
    code = link_code(client)
    token = client.post("/auth/exchange", json={"code": code}).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


ROADMAP = {"semesters": [{"year": 1, "semester": 1, "courses": []}], "validation": {"passed": True}}


def test_로드맵을_저장하면_me에서_보인다(client):
    auth = logged_in(client)

    res = client.post(
        "/me/roadmaps",
        json={"target_job": "네트워크 엔지니어", "roadmap": ROADMAP},
        headers=auth,
    )

    assert res.status_code == 201
    saved = client.get("/me", headers=auth).json()["saved_roadmaps"]
    assert saved[0]["target_job"] == "네트워크 엔지니어"
    assert saved[0]["roadmap"]["validation"]["passed"] is True


def test_같은_직무로_다시_저장하면_덮어쓴다(client):
    # 시연 중 여러 번 저장해도 목록이 쌓이지 않게
    auth = logged_in(client)
    client.post("/me/roadmaps", json={"target_job": "네트워크 엔지니어", "roadmap": ROADMAP}, headers=auth)

    client.post(
        "/me/roadmaps",
        json={"target_job": "네트워크 엔지니어", "roadmap": {**ROADMAP, "v": 2}},
        headers=auth,
    )

    saved = client.get("/me", headers=auth).json()["saved_roadmaps"]
    assert len(saved) == 1
    assert saved[0]["roadmap"]["v"] == 2


def test_다른_직무는_따로_쌓인다(client):
    auth = logged_in(client)
    client.post("/me/roadmaps", json={"target_job": "네트워크 엔지니어", "roadmap": ROADMAP}, headers=auth)

    client.post("/me/roadmaps", json={"target_job": "AI 개발자", "roadmap": ROADMAP}, headers=auth)

    assert len(client.get("/me", headers=auth).json()["saved_roadmaps"]) == 2


def test_토큰_없이는_저장할_수_없다(client):
    res = client.post(
        "/me/roadmaps", json={"target_job": "네트워크 엔지니어", "roadmap": ROADMAP}
    )

    assert res.status_code == 401


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


# --- DB가 죽었을 때 ---


def test_DB가_없으면_500이_아니라_503을_낸다(client, monkeypatch):
    """SQLAlchemy는 세션 생성이 아니라 첫 쿼리에서 연결한다. 세션 생성만 감싸면
    OperationalError가 그대로 새어나가 500 + 프론트가 못 읽는 형식이 된다."""
    db.use("sqlite:////열-수-없는-경로/x.db")

    res = client.post("/auth/login", json={"student_id": "x", "password": "y1234567"})

    assert res.status_code == 503
    assert res.json()["error"]["code"] == "DB_UNAVAILABLE"


def test_DB가_없어도_코어는_돈다(client, monkeypatch):
    db.use("sqlite:////열-수-없는-경로/x.db")

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


def test_인증번호로_가입하면_메일_링크_없이_바로_로그인된다(client):
    """링크 방식은 화면을 떠나 폼 입력이 날아간다. 번호 방식은 가입 화면에서 끝난다."""
    import mailer

    email = "code-flow@mjc.ac.kr"
    client.post("/auth/email/code", json={"email": email})
    code = mailer.outbox[-1]["code"]

    verified = client.post("/auth/email/verify", json={"email": email, "code": code})
    assert verified.status_code == 200
    ticket = verified.json()["email_ticket"]

    res = client.post(
        "/auth/signup",
        json={
            "student_id": "20250901",
            "name": "코드",
            "email": email,
            "password": "password123",
            "dept_id": "itc",
            "email_ticket": ticket,
            "agreed_terms": True,
            "agreed_privacy": True,
        },
    )

    assert res.status_code == 201
    assert res.json()["access_token"]  # 인증이 끝났으니 토큰이 나온다


def test_틀린_인증번호는_티켓을_주지_않는다(client):
    client.post("/auth/email/code", json={"email": "wrong@mjc.ac.kr"})

    res = client.post("/auth/email/verify", json={"email": "wrong@mjc.ac.kr", "code": "000000"})

    assert res.status_code == 400
    assert res.json()["error"]["code"] == "INVALID_CODE"


def test_남의_이메일_티켓으로는_가입할_수_없다(client):
    """티켓의 이메일과 가입 이메일이 다르면 남의 인증을 빌려 쓰는 것이다."""
    import mailer

    client.post("/auth/email/code", json={"email": "owner@mjc.ac.kr"})
    code = mailer.outbox[-1]["code"]
    ticket = client.post(
        "/auth/email/verify", json={"email": "owner@mjc.ac.kr", "code": code}
    ).json()["email_ticket"]

    res = client.post(
        "/auth/signup",
        json={
            "student_id": "20250902",
            "name": "도둑",
            "email": "other@mjc.ac.kr",
            "password": "password123",
            "dept_id": "itc",
            "email_ticket": ticket,
            "agreed_terms": True,
            "agreed_privacy": True,
        },
    )

    # 가입은 되되 인증은 안 된 상태 — 토큰 없이 메일 안내만
    assert res.status_code == 201
    assert "access_token" not in res.json()


def test_아이디_중복_확인(client):
    assert client.post("/auth/check-id", json={"student_id": "202512345"}).json() == {
        "available": True
    }

    client.post("/auth/signup", json=SIGNUP)

    assert client.post("/auth/check-id", json={"student_id": "202512345"}).json() == {
        "available": False
    }


def test_약관에_동의하지_않으면_가입이_막힌다(client):
    """화면에서도 막지만 서버가 최종이다 — 클라이언트를 신뢰하지 않는다."""
    res = client.post(
        "/auth/signup", json={**SIGNUP, "agreed_terms": True, "agreed_privacy": False}
    )

    assert res.status_code == 400
    assert res.json()["error"]["code"] == "TERMS_REQUIRED"
