"""어느 엔진이 로드맵을 짰는지 — 데모 안전장치.

규칙 엔진이 메인이다 (8/7 02시 팀 결정). LLM은 `MJC_ENGINE=llm`일 때만 시도하는
비교 데모용 보조이며, 실패해도 로드맵은 나와야 한다. 무엇이 돌았는지 `engine`으로
밝힌다 — 폴백이 조용히 일어나면 결과의 출처를 오인한다.
"""

import pytest
from fastapi.testclient import TestClient

import agent
import catalog
import envfile
import main
from tests.test_api import FIXTURES

REQ = {
    "dept_id": "itc",
    "current_year": 1,
    "current_semester": 1,
    "completed_courses": [],
    "target_job": "네트워크 엔지니어",
}


@pytest.fixture(autouse=True)
def fixture_data(monkeypatch):
    monkeypatch.setattr(catalog, "DATA_DIR", FIXTURES)


@pytest.fixture
def client():
    return TestClient(main.app)


def test_키가_없으면_규칙_플래너로_돈다(client):
    body = client.post("/roadmap", json=REQ).json()

    assert body["engine"] == "rule"
    assert body["validation"]["passed"] is True


def test_키가_있어도_기본은_규칙이다(client, monkeypatch, tmp_path):
    """MJC_ENGINE 없이 키만 있으면 LLM을 부르지 않는다 — 기본 경로에 토큰·지연 없음."""
    monkeypatch.setattr(envfile, "DEFAULT", tmp_path / ".env")
    (tmp_path / ".env").write_text("ANTHROPIC_API_KEY = sk-test-abc\n", encoding="utf-8")

    assert client.post("/roadmap", json=REQ).json()["engine"] == "rule"


def test_MJC_ENGINE_llm일_때만_LLM을_쓴다(client, monkeypatch, tmp_path):
    """LLM은 opt-in이다. env파일의 키 + MJC_ENGINE=llm 둘 다 있어야 시도한다."""
    monkeypatch.setenv("MJC_ENGINE", "llm")
    monkeypatch.setattr(envfile, "DEFAULT", tmp_path / ".env")
    (tmp_path / ".env").write_text("ANTHROPIC_API_KEY = sk-test-abc\n", encoding="utf-8")
    monkeypatch.setattr(agent, "generate", lambda spec, feedback=None, attempt=1: {
        "semesters": [{"year": 1, "semester": 1, "courses": [], "certificates": [], "notes": ""}]
    })

    assert client.post("/roadmap", json=REQ).json()["engine"] == "llm"


def test_LLM이_실패하면_규칙으로_떨어지고_200을_낸다(client, monkeypatch, tmp_path):
    """API 키가 만료되거나 네트워크가 끊겨도 시연은 계속돼야 한다."""
    monkeypatch.setenv("MJC_ENGINE", "llm")
    monkeypatch.setattr(envfile, "DEFAULT", tmp_path / ".env")
    (tmp_path / ".env").write_text("ANTHROPIC_API_KEY = sk-test-abc\n", encoding="utf-8")

    def boom(spec, feedback=None, attempt=1):
        raise RuntimeError("레이트리밋")

    monkeypatch.setattr(agent, "generate", boom)

    body = client.post("/roadmap", json=REQ).json()

    assert body["engine"] == "rule (llm-failed)"
    assert body["validation"]["passed"] is True


def test_LLM이_생성해도_job_related가_붙는다(client, monkeypatch, tmp_path):
    """규칙 플래너만 job_related를 달았다. LLM 경로에선 빠져서 화면이 직무 과목을
    강조할 수 없고 job_match.related_courses가 0으로 나왔다."""
    monkeypatch.setenv("MJC_ENGINE", "llm")
    monkeypatch.setattr(envfile, "DEFAULT", tmp_path / ".env")
    (tmp_path / ".env").write_text("ANTHROPIC_API_KEY = sk-test-abc\n", encoding="utf-8")

    def fake_llm(spec, feedback=None, attempt=1):
        return {
            "semesters": [
                {
                    "year": 1, "semester": 1,
                    "courses": [dict(c) for c in spec["dept"]["courses"]],
                    "certificates": [], "notes": "",
                }
            ]
        }

    monkeypatch.setattr(agent, "generate", fake_llm)

    body = client.post("/roadmap", json=REQ).json()

    assert body["engine"] == "llm"
    assert body["job_match"]["related_courses"] > 0
    assert any(c.get("job_related") for s in body["semesters"] for c in s["courses"])
