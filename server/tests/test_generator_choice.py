"""어느 생성기가 쓰이는지 — 데모 안전장치.

LLM은 18~46초가 걸리고 API 키가 필요하다. 키가 없거나 호출이 실패해도 로드맵은
나와야 한다. 실패하면 무엇이 돌았는지 응답에 남겨 조용히 넘어가지 않게 한다.
"""

import pytest
from fastapi.testclient import TestClient

import catalog
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


def test_키가_없으면_결정론적_planner를_쓴다(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    assert main.pick_generator().__module__ == "planner"


def test_키가_있으면_LLM_에이전트를_쓴다(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-not-real")

    assert main.pick_generator().__module__ == "agent"


def test_LLM이_실패하면_planner로_떨어지고_200을_낸다(client, monkeypatch):
    """API 키가 만료되거나 네트워크가 끊겨도 시연은 계속돼야 한다."""

    def boom(spec, feedback=None, attempt=1):
        raise RuntimeError("API 호출 실패")

    monkeypatch.setattr(main, "pick_generator", lambda: boom)

    res = client.post("/roadmap", json=REQ)

    assert res.status_code == 200
    assert res.json()["validation"]["passed"] is True


def test_무엇이_돌았는지_응답에_남긴다(client, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    body = client.post("/roadmap", json=REQ).json()

    assert body["generator"] == "planner"


def test_폴백했으면_그렇게_표시한다(client, monkeypatch):
    def boom(spec, feedback=None, attempt=1):
        raise RuntimeError("API 호출 실패")

    monkeypatch.setattr(main, "pick_generator", lambda: boom)

    body = client.post("/roadmap", json=REQ).json()

    assert body["generator"] == "planner (LLM 실패)"
