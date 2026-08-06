from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import catalog
from main import app

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture(autouse=True)
def fixture_data(monkeypatch):
    monkeypatch.setattr(catalog, "DATA_DIR", FIXTURES)


@pytest.fixture
def client():
    return TestClient(app)


def test_depts는_동결_스펙_4키를_낸다(client):
    body = client.get("/depts").json()

    assert isinstance(body, list)
    assert {"dept_id", "dept_name", "years", "tier"} <= set(body[0])


def test_roadmap은_동결_스펙_형태를_낸다(client):
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
    body = res.json()
    assert "semesters" in body
    assert set(body["validation"]) == {
        "passed",
        "total_credits",
        "major_credits",
        "liberal_credits",
        "semesters",
        "details",
    }


def test_roadmap_학기에_과목과_자격증_칸이_있다(client):
    body = client.post(
        "/roadmap",
        json={
            "dept_id": "itc",
            "current_year": 1,
            "current_semester": 1,
            "completed_courses": [],
            "target_job": "네트워크 엔지니어",
        },
    ).json()

    first = body["semesters"][0]
    assert {"year", "semester", "courses", "certificates", "notes"} <= set(first)


def test_이수_과목을_보내면_검증에_반영된다(client):
    """2학년 1학기 학생. 1학년 과목을 이수했다고 보내면 그 학점이 합산돼야 한다."""
    dept = catalog.load_dept("itc", root=FIXTURES)
    year1 = [c["course_id"] for c in dept["courses"] if c["year"] == 1]

    body = client.post(
        "/roadmap",
        json={
            "dept_id": "itc",
            "current_year": 2,
            "current_semester": 1,
            "completed_courses": year1,
            "target_job": "네트워크 엔지니어",
        },
    ).json()

    completed_credits = sum(c["credits"] for c in dept["courses"] if c["year"] == 1)
    assert body["validation"]["total_credits"] >= completed_credits
    assert body["validation"]["semesters"] >= 2


def test_교양선택_버킷이_교양_학점으로_집계된다(client):
    """교육과정표에 교양 과목이 열거되지 않는다(liberal_elective_credits 버킷으로만 온다).

    블록으로 안 깔면 교양 학점이 0으로 집계돼 **항상** 미달이고 max_retries만 태운다.
    """
    body = client.post(
        "/roadmap",
        json={
            "dept_id": "itc",
            "current_year": 1,
            "current_semester": 1,
            "completed_courses": [],
            "target_job": "네트워크 엔지니어",
        },
    ).json()

    blocks = [
        c
        for s in body["semesters"]
        for c in s["courses"]
        if c["category"] == "교양" and "교양선택" in c["name"]
    ]
    assert sum(b["credits"] for b in blocks) == 7  # 픽스처의 liberal_elective_credits
    # 교양필수 3 + 교양선택 7 = 10 (3년제 기준 충족)
    assert body["validation"]["liberal_credits"] == 10
    assert not any(d["rule"] == "liberal_credits" for d in body["validation"]["details"])


def test_없는_학과는_404와_에러_형식(client):
    res = client.post(
        "/roadmap",
        json={
            "dept_id": "없는학과",
            "current_year": 1,
            "current_semester": 1,
            "completed_courses": [],
            "target_job": "네트워크 엔지니어",
        },
    )

    assert res.status_code == 404
    # lib/api.js가 err?.error?.message를 읽는다
    assert res.json()["error"]["message"]
    assert res.json()["error"]["code"]


def test_모르는_course_id를_보내도_500이_아니다(client):
    """프론트 체크박스와 데이터가 어긋나도 코어 경로는 살아야 한다."""
    res = client.post(
        "/roadmap",
        json={
            "dept_id": "itc",
            "current_year": 1,
            "current_semester": 1,
            "completed_courses": ["itc-없는과목"],
            "target_job": "네트워크 엔지니어",
        },
    )

    assert res.status_code == 200


def test_report는_jobs_키를_낸다(client):
    body = client.get("/report/itc").json()

    assert "jobs" in body
