import os

import envfile


def write(tmp_path, text):
    p = tmp_path / ".env"
    p.write_text(text, encoding="utf-8")
    return p


def test_등호_양쪽_공백을_허용한다(tmp_path, monkeypatch):
    """실제로 이렇게 적힌 .env가 왔다. 공백을 안 벗기면 키를 못 읽는다."""
    monkeypatch.delenv("MJC_T1", raising=False)

    envfile.load(write(tmp_path, "MJC_T1 = sk-abc123 "))

    assert os.environ["MJC_T1"] == "sk-abc123"


def test_주석과_빈_줄을_무시한다(tmp_path, monkeypatch):
    monkeypatch.delenv("MJC_T2", raising=False)

    envfile.load(write(tmp_path, "# 주석\n\nMJC_T2=v\n"))

    assert os.environ["MJC_T2"] == "v"


def test_값에_등호가_있어도_첫_등호만_가른다(tmp_path, monkeypatch):
    monkeypatch.delenv("MJC_T3", raising=False)

    envfile.load(write(tmp_path, "MJC_T3=postgresql://u:p@h/db?a=b"))

    assert os.environ["MJC_T3"] == "postgresql://u:p@h/db?a=b"


def test_이미_있는_환경변수를_덮어쓰지_않는다(tmp_path, monkeypatch):
    """셸에서 준 값이 파일보다 우선이어야 한다 — 테스트가 DATABASE_URL을 갈아끼운다."""
    monkeypatch.setenv("MJC_T4", "셸값")

    envfile.load(write(tmp_path, "MJC_T4=파일값"))

    assert os.environ["MJC_T4"] == "셸값"


def test_줄바꿈_없는_한_줄_파일도_읽는다(tmp_path, monkeypatch):
    monkeypatch.delenv("MJC_T5", raising=False)

    envfile.load(write(tmp_path, "MJC_T5=v"))

    assert os.environ["MJC_T5"] == "v"


def test_파일이_없으면_False(tmp_path):
    assert envfile.load(tmp_path / "없음") is False
