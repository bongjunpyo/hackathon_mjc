import envfile
import main


def test_env파일의_키만_있어도_LLM을_고른다(tmp_path, monkeypatch):
    """pick_generator가 os.getenv를 보는데 .env는 agent.generate 안에서 로드됐다.
    그래서 .env에 키가 있어도 planner가 선택됐다 — 실제로 그랬다."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setattr(envfile, "DEFAULT", tmp_path / ".env")
    (tmp_path / ".env").write_text("ANTHROPIC_API_KEY = sk-test-abc\n", encoding="utf-8")

    assert main.pick_generator().__module__ == "agent"


def test_env파일에도_키가_없으면_planner(tmp_path, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setattr(envfile, "DEFAULT", tmp_path / ".env")
    (tmp_path / ".env").write_text("# 비어있음\n", encoding="utf-8")

    assert main.pick_generator().__module__ == "planner"


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
