"""테스트는 LLM을 부르지 않는다.

`POST /roadmap`이 `agent.generate`(실제 Claude API)를 쓰도록 바뀌면서, 손대지 않으면
스위트 한 번에 실제 호출이 열 번 넘게 나간다 — 15초짜리가 5분을 넘겼고 결과가
네트워크·키 상태에 흔들린다. 요금도 나간다.

두 겹으로 막는다.
  1. `agent.generate`를 규칙 플래너로 바꿔치기 — 루프·검증기 로직은 `generate_fn`이
     무엇이든 똑같이 돌아야 하므로 결정론적인 쪽으로 고정한다
  2. `ANTHROPIC_API_KEY`를 지우고 `.env` 경로를 없는 곳으로 — 엔진 선택 자체가
     LLM으로 가지 않게 한다. 1번만 두면 `pick_generator()`가 LLM을 고르고,
     그때 실제 클라이언트를 만드는 경로가 살아 있다

LLM 경로 자체는 테스트가 아니라 실측으로 확인한다 (`docs/AI_USAGE.md`).
LLM을 쓰는 테스트는 이 픽스처를 직접 덮어쓴다 (`test_generator_env.py`).
"""

import pytest

import agent
import envfile
import planner


@pytest.fixture(autouse=True)
def no_llm(monkeypatch, tmp_path_factory):
    monkeypatch.setattr(agent, "generate", planner.generate)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setattr(envfile, "DEFAULT", tmp_path_factory.mktemp("noenv") / ".env")
