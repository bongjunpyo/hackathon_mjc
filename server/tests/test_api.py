from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import agent
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
    """Tier 2는 파이프라인 자동 통과라 직무 추출이 비어 있을 수 있다.
    비교 대상이 없는데 막으면 그 학과는 아무것도 못 한다."""
    import json

    data = json.loads((FIXTURES / "itc.json").read_text(encoding="utf-8"))
    data["careers"] = []
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



def _roadmap(client, job):
    return client.post(

        "/roadmap",
        json={
            "dept_id": "itc",
            "current_year": 1,
            "current_semester": 1,
            "completed_courses": [],

            "target_job": job,
        },
    )


def test_talent_type_직무도_받는다(client):
    """비고 열 라벨은 careers에 없다. 한쪽만 보면 데모 직무가 400이 된다 (이슈 #40)."""
    assert _roadmap(client, "시스템관리·운용엔지니어").status_code == 200


def test_careers_직무도_그대로_받는다(client):
    assert _roadmap(client, "네트워크 엔지니어").status_code == 200


def test_두_목록에_없는_직무는_400이고_고를_수_있는_직무를_알려준다(client):
    res = _roadmap(client, "우주비행사")

    assert res.status_code == 400
    body = res.json()
    assert body["error"]["code"] == "UNKNOWN_JOB"
    # 두 목록을 합쳐 안내해야 사용자가 실제로 고를 수 있다
    assert "시스템관리·운용엔지니어" in body["error"]["message"]
    assert "네트워크 엔지니어" in body["error"]["message"]


def test_depts는_직무_드롭다운_재료를_낸다(client):
    body = client.get("/depts").json()

    assert {"talent_types", "careers", "certificates"} <= set(body[0])


def test_LLM이_죽어도_규칙_플래너로_로드맵이_나간다(client, monkeypatch):
    """발표 중 키 만료·레이트리밋으로 데모가 통째로 죽지 않아야 한다."""

    def 폭발(*args, **kwargs):
        raise RuntimeError("API 다운")

    monkeypatch.setattr(agent, "generate", 폭발)

    res = _roadmap(client, "네트워크 엔지니어")

    assert res.status_code == 200
    body = res.json()
    assert body["engine"] == "rule"
    assert body["semesters"]


def test_어느_엔진이_짰는지_표시한다(client):
    """폴백이 조용히 일어나면 규칙 코드 결과를 LLM 결과로 오인한다.

    여기는 키가 없는 환경이라 `rule`이 정답이다. 세 상태(rule / llm / rule (llm-failed))를
    실제 분기까지 확인하는 것은 test_engine.py에 있다."""
    assert _roadmap(client, "네트워크 엔지니어").json()["engine"] == "rule"


def test_대응_라벨이_없는_진로는_안내를_함께_낸다(client):
    """학과가 홍보하는 진로에 교육과정 대응이 없을 수 있다. 로드맵은 내되
    "직무 맞춤이 안 됐다"를 숨기지 않는다 — 조용히 일반 로드맵을 주면 거짓이다."""
    body = _roadmap(client, "IoT 개발자").json()

    assert "job_match" in body


def test_대응_라벨이_있으면_무엇과_맞췄는지_알려준다(client):
    body = _roadmap(client, "네트워크 엔지니어").json()

    assert body["job_match"]["matched_labels"]
    assert body["job_match"]["related_courses"] > 0



def test_직무_미정이면_추천_직무로_짠다(client):
    """직무를 못 정한 학생 — 이 서비스가 가장 필요한 사용자 — 를 400으로 내쫓지 않는다."""
    res = client.post(
        "/roadmap",
        json={
            "dept_id": "itc",
            "current_year": 1,
            "current_semester": 1,
            "completed_courses": [],
        },
    )

    assert res.status_code == 200
    body = res.json()
    assert body["job_recommended"] is True
    # 추천 근거는 라벨별 배정 학점 — 1위 직무로 짰음을 밝힌다
    assert body["target_job"] == body["recommended_jobs"][0]["job"]
    assert body["recommended_jobs"][0]["credits"] >= body["recommended_jobs"][-1]["credits"]
    assert body["job_match"]["related_courses"] > 0


def test_직무를_고르면_추천_필드가_없다(client):
    body = _roadmap(client, "네트워크 엔지니어").json()

    assert "job_recommended" not in body
    assert "recommended_jobs" not in body


def test_화면_경로_새로고침이_404가_아니다(client):
    """시연 중 /app/*에서 F5 한 번이면 404가 났다 (이슈 #50).

    StaticFiles(html=True)는 루트만 index.html로 떨어뜨린다 — /app/*는
    별도 SPA 폴백이 받아야 한다. dist가 없는 테스트 환경에선 라우트 자체가
    없으므로, dist가 있을 때만 검사한다.
    """
    from pathlib import Path

    import main as main_module

    dist = Path(main_module.__file__).parent.parent / "web" / "dist"
    if not dist.is_dir():
        return

    res = client.get("/app/roadmap")

    assert res.status_code == 200
    assert "text/html" in res.headers["content-type"]
