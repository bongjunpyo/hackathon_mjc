"""리뷰에서 재현된 결함들의 회귀 테스트.

각 테스트는 고치기 전 실제로 실패하는 것을 확인한 것이다 (변이 검사).
"""

import json

import pytest
from fastapi.testclient import TestClient

import catalog
import jobmap
import main
import report
from tests.test_api import FIXTURES
from validator import validate_roadmap


@pytest.fixture(autouse=True)
def fixture_data(monkeypatch):
    monkeypatch.setattr(catalog, "DATA_DIR", FIXTURES)


@pytest.fixture
def client():
    return TestClient(main.app)


def _major(dept):
    return next(c for c in dept["courses"] if c["category"] == "전공")


# ── 중복 학점 부풀림 ────────────────────────────────────────────────
def test_같은_과목을_여러_번_보내도_학점은_한_번만_센다(client):
    """같은 id 5번에 전공 54→66학점(3년제 요건선)이 되어 졸업요건이 뚫렸다."""
    dept = catalog.load_dept("itc")
    one = _major(dept)

    def major_credits(ids):
        body = {
            "dept_id": "itc",
            "current_year": 2,
            "current_semester": 1,
            "completed_courses": ids,
            "target_job": "네트워크 엔지니어",
        }
        return client.post("/roadmap", json=body).json()["validation"]["major_credits"]

    assert major_credits([one["course_id"]]) == major_credits([one["course_id"]] * 5)


def test_검증기가_이수와_로드맵의_중복을_합산하지_않는다():
    dept = catalog.load_dept("itc")
    one = _major(dept)
    semesters = [{"year": 1, "semester": 1, "courses": [one]}]

    alone = validate_roadmap(semesters, 3)
    twice = validate_roadmap(semesters, 3, completed=[one])

    assert alone["major_credits"] == twice["major_credits"] == one["credits"]


def test_resolve가_중복_id를_한_번만_돌려준다():
    found, missing = catalog.resolve("itc", ["itc-인성채플"] * 4, root=FIXTURES)
    assert len(found) == 1
    assert missing == []


# ── 빈 학기를 재학 학기로 세지 않는다 ──────────────────────────────
def test_과목이_없는_학기는_재학_학기로_세지_않는다():
    """agent.py는 LLM이 빠뜨린 학기를 빈 칸으로 채운다. len(semesters)로 세면
    LLM은 이 룰을 언제나 공짜로 통과했다."""
    filled = {"year": 1, "semester": 1, "courses": [_major(catalog.load_dept("itc"))]}
    empty = {"year": 1, "semester": 2, "courses": []}

    assert validate_roadmap([filled, empty], 3)["semesters"] == 1


# ── 학과 목록이 파일 하나로 죽지 않는다 ────────────────────────────
def test_깨진_학과_파일_하나가_전체_목록을_죽이지_않는다(tmp_path):
    (tmp_path / "itc.json").write_text(
        (FIXTURES / "itc.json").read_text(encoding="utf-8"), encoding="utf-8"
    )
    (tmp_path / "zz-broken.json").write_text('{"dept_id": "x"}', encoding="utf-8")

    depts = catalog.list_depts(root=tmp_path)

    assert [d["dept_id"] for d in depts] == ["itc"]


def test_깨진_파일이_있어도_depts는_200이다(client, monkeypatch, tmp_path):
    (tmp_path / "itc.json").write_text(
        (FIXTURES / "itc.json").read_text(encoding="utf-8"), encoding="utf-8"
    )
    (tmp_path / "zz-broken.json").write_text("[]", encoding="utf-8")
    monkeypatch.setattr(catalog, "DATA_DIR", tmp_path)

    assert client.get("/depts").status_code == 200


# ── jobmap: 완전 일치 우선 ─────────────────────────────────────────
def test_완전히_일치하는_라벨을_버리지_않는다():
    """동률 처리가 '가장 짧은 라벨'이라 자기 자신을 버렸다 —
    `의료정보관리전문가및보건교육사`가 부분문자열인 `보건교육사`로 매핑됐다."""
    labels = ["보건교육사", "의료정보관리전문가", "의료정보관리전문가및보건교육사"]

    assert jobmap.match_labels("의료정보관리전문가및보건교육사", labels) == [
        "의료정보관리전문가및보건교육사"
    ]


# ── report와 roadmap이 같은 매핑을 쓴다 ────────────────────────────
def test_리포트와_로드맵이_같은_진로를_같게_매핑한다():
    """따로 구현했더니 갈라졌다. `jobmap`에만 동률 처리가 있어서 리포트는 라벨 2개,
    로드맵은 1개를 붙였다. 픽스처는 careers와 talent_type이 같은 문자열이라 이
    차이가 안 드러나므로 실데이터에서 갈라진 조합을 그대로 쓴다."""
    labels = ["시스템관리·운용엔지니어", "시스템응용SW개발엔지니어"]

    assert report._matches("시스템 엔지니어", labels) == jobmap.match_labels(
        "시스템 엔지니어", labels
    )
    assert len(report._matches("시스템 엔지니어", labels)) == 1


def test_커버리지_분자는_전공_과목만_센다():
    dept = catalog.load_dept("itc")
    labels = report._raw_labels(dept)
    # 비전공 과목에 목표 라벨을 붙여도 커버리지가 오르지 않아야 한다
    tainted = json.loads(json.dumps(dept))
    for course in tainted["courses"]:
        if course["category"] != "전공":
            course["talent_type"] = labels[0]

    before = report.build_report(dept)["jobs"]
    after = report.build_report(tainted)["jobs"]

    assert [j["coverage_pct"] for j in before] == [j["coverage_pct"] for j in after]


# ── 직무 미정 모드 (PR #53) ────────────────────────────────────────
def test_직무를_지정해도_응답에_target_job이_있다(client):
    """추천일 때만 넣으면 프론트가 body.target_job을 그대로 못 읽고 분기해야 한다."""
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

    assert body["target_job"] == "네트워크 엔지니어"
    assert "job_recommended" not in body


def test_추천_학점은_전공만_센다():
    """트랙 B 커버리지는 분모가 전공 학점이다. 전 과목을 세면 두 화면이 같은 직무에
    다른 숫자를 말한다 — 유아교육과에서 95학점 중 27학점이 비전공이었다."""
    dept = catalog.load_dept("itc")
    label = next(c["talent_type"] for c in dept["courses"] if c.get("talent_type"))
    tainted = json.loads(json.dumps(dept))
    for course in tainted["courses"]:
        if course["category"] != "전공":
            course["talent_type"] = label

    before = {e["job"]: e["credits"] for e in main._recommend_jobs(dept)}
    after = {e["job"]: e["credits"] for e in main._recommend_jobs(tainted)}

    assert before == after


# ── 두 엔진의 응답 모양이 같다 ─────────────────────────────────────
def test_규칙_폴백도_reasoning과_학기학점을_낸다(client):
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

    assert body["engine"] == "rule"
    assert body["reasoning"] == ""
    for semester in body["semesters"]:
        assert "credits" in semester
        assert semester["credits"] == sum(c["credits"] for c in semester["courses"])


