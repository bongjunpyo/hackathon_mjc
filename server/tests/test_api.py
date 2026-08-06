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
        "remaining_credits",
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


def test_남은_학점을_알려준다(client):
    """교육과정표에 교양선택·일반선택이 없다. 지어내지 않고 몇 학점 남았는지만 알린다."""
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

    v = body["validation"]
    assert v["liberal_credits"] == 3  # 교양필수(인성채플1 + 성경과삶2)뿐
    assert v["remaining_credits"] == 110 - v["total_credits"]
    assert v["passed"] is True  # 전공·교양필수·학기는 충족


def test_depts가_목표_직무_선택지를_준다(client):
    itc = next(d for d in client.get("/depts").json() if d["dept_id"] == "itc")

    assert "네트워크 엔지니어" in itc["careers"]


def test_학과에_없는_직무는_400(client):
    """오타 하나로 조용히 일반 로드맵이 나가면, 직무 역산이라는 주장 자체가 무너진다."""
    res = client.post(
        "/roadmap",
        json={
            "dept_id": "itc",
            "current_year": 1,
            "current_semester": 1,
            "completed_courses": [],
            "target_job": "우주비행사",
        },
    )

    assert res.status_code == 400
    assert res.json()["error"]["code"] == "UNKNOWN_JOB"
    # 뭘 고를 수 있는지 알려준다
    assert "네트워크 엔지니어" in res.json()["error"]["message"]


def test_직무_목록이_비어_있으면_막지_않는다(client, tmp_path, monkeypatch):
    """Tier 2는 파이프라인 자동 통과라 talent_types 추출이 비어 있을 수 있다.
    비교 대상이 없는데 막으면 그 학과는 아무것도 못 한다."""
    import json

    data = json.loads((FIXTURES / "itc.json").read_text(encoding="utf-8"))
    data["talent_types"] = []
    (tmp_path / "itc.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    monkeypatch.setattr(catalog, "DATA_DIR", tmp_path)

    res = client.post(
        "/roadmap",
        json={
            "dept_id": "itc",
            "current_year": 1,
            "current_semester": 1,
            "completed_courses": [],
            "target_job": "아무 직무",
        },
    )

    assert res.status_code == 200


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


def test_키가_없으면_planner로_떨어진다(monkeypatch):
    """LLM은 켜는 경로다. 키가 빠져도 로드맵이 나와야 시연이 산다."""
    import main
    from planner import generate as planner_generate

    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setattr("agent._load_env", lambda: None)

    assert main._generator() is planner_generate


def test_키가_있으면_LLM_에이전트를_쓴다(monkeypatch):
    """agent.py가 main에 있는데 아무도 부르지 않던 적이 있다 (이슈 #36)."""
    import agent
    import main

    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    monkeypatch.setattr("agent._load_env", lambda: None)

    assert main._generator() is agent.generate


def test_roadmap_엔드포인트가_generator를_거친다(client, monkeypatch):
    """`_generator()`가 있어도 호출부가 planner를 직접 부르면 LLM은 영영 안 돈다.

    이슈 #36이 정확히 그 모양이었다 — 파일은 있는데 아무도 부르지 않았다.
    선택 함수만 검사하는 테스트는 이 변이를 못 잡는다.
    """
    called = []

    def spy(spec, feedback=None, attempt=1):
        called.append(attempt)
        return {"semesters": []}

    monkeypatch.setattr("main._generator", lambda: spy)
    client.post(
        "/roadmap",
        json={
            "dept_id": "itc",
            "current_year": 1,
            "current_semester": 1,
            "completed_courses": [],
            "target_job": "네트워크 엔지니어",
        },
    )

    assert called, "_generator()가 고른 생성기가 쓰이지 않았다"
