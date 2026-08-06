"""agent.py가 planner의 이름을 잘못 가져오지 않는지 — 소스 검사."""


def test_에이전트가_planner에서_없는_함수를_가져오지_않는다():
    """agent.py가 planner._place_liberal_bucket을 import했는데 그 함수를 지웠다.
    ImportError로 죽어 매번 planner로 폴백했다 — 30초를 태우고 나서야.
    프롬프트 조립까지 가야 드러나므로 소스에서 미리 막는다."""
    import re
    from pathlib import Path

    import planner

    source = (Path(__file__).parent.parent / "agent.py").read_text(encoding="utf-8")
    imported = set()
    for m in re.finditer(r"from planner import ([^\n]+)", source):
        imported |= {n.strip() for n in m.group(1).split(",")}

    missing = {n for n in imported if not hasattr(planner, n)}
    assert not missing, f"planner에 없는 이름: {sorted(missing)}"
