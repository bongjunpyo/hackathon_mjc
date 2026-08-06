"""테스트는 절대 외부 API를 호출하지 않는다.

`.env`에 ANTHROPIC_API_KEY를 넣은 순간 `pick_generator()`가 LLM을 골라서, POST /roadmap을
치는 테스트마다 실제 Anthropic 호출이 나갔다. 한 번에 18~46초 × 요금이고, 그대로 두면
CI든 로컬이든 테스트를 돌릴 때마다 돈이 빠진다. 실제로 스위트가 5분 넘게 멈췄다.

키를 지우고 `.env` 경로를 없는 곳으로 돌려, 기본값이 항상 결정론적 planner가 되게 한다.
LLM 경로를 재려면 test_generator_env.py처럼 테스트가 명시적으로 다시 지정한다.
"""

import pytest

import envfile


@pytest.fixture(autouse=True)
def no_external_api(monkeypatch, tmp_path_factory):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setattr(
        envfile, "DEFAULT", tmp_path_factory.mktemp("noenv") / ".env"
    )
