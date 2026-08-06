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


def test_LLM이_생성해도_job_related가_붙는다(monkeypatch, tmp_path):
    """planner만 job_related를 달았다. LLM 경로에선 빠져서 화면이 직무 과목을
    강조할 수 없고 job_match.related_courses가 0으로 나왔다."""
    from fastapi.testclient import TestClient

    import catalog
    import main
    from tests.test_api import FIXTURES

    monkeypatch.setattr(catalog, "DATA_DIR", FIXTURES)

    def fake_llm(spec, feedback=None, attempt=1):
        # 에이전트는 job_related를 달지 않는다
        return {
            "semesters": [
                {
                    "year": 1,
                    "semester": 1,
                    "courses": [dict(c) for c in spec["dept"]["courses"]],
                    "certificates": [],
                    "notes": "",
                }
            ]
        }

    monkeypatch.setattr(main, "pick_generator", lambda: fake_llm)

    body = TestClient(main.app).post(
        "/roadmap",
        json={
            "dept_id": "itc",
            "current_year": 1,
            "current_semester": 1,
            "completed_courses": [],
            "target_job": "네트워크 엔지니어",
        },
    ).json()

    assert body["job_match"]["related_courses"] > 0
    assert any(c.get("job_related") for s in body["semesters"] for c in s["courses"])
