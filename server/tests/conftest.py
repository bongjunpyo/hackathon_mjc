"""테스트는 LLM을 부르지 않는다.

`POST /roadmap`이 `agent.generate`(실제 Claude API)를 쓰도록 바뀌면서, 손대지 않으면
스위트 한 번에 실제 호출이 열 번 넘게 나간다 — 9초짜리가 2분을 넘겼고 결과가
네트워크·키 상태에 흔들린다.

루프와 검증기 로직은 `generate_fn`이 무엇이든 똑같이 돌아야 하므로 결정론적인 규칙
플래너로 고정한다. LLM 경로 자체는 테스트가 아니라 실측으로 확인한다
(`docs/AI_USAGE.md`). LLM을 쓰는 테스트는 이 픽스처를 직접 덮어쓴다.
"""

import pytest

import agent
import planner


@pytest.fixture(autouse=True)
def no_llm(monkeypatch):
    monkeypatch.setattr(agent, "generate", planner.generate)
