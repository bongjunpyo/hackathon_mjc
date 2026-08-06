# server — P2 이동제

FastAPI: 졸업요건 검증기(순수 규칙) + 로드맵 에이전트 + 정합도 계산.
API 계약: ../docs/DESIGN.md §5 (동결), ../CLAUDE.md

## 테스트

```bash
uv run pytest
```

윈도우에서 한글 테스트 이름이 깨져 보이면 `PYTHONUTF8=1 uv run pytest`. 실패한 테스트가 뭔지 못 읽으면 디버깅이 안 된다.

## 검증기

`validator.py` — `validate_roadmap(semesters, years)` → 동결 스펙의 `validation` 객체.
LLM을 쓰지 않는 결정론적 규칙 코드다. 졸업요건 4종(총학점·교양·전공·재학학기)을 2/3년제로 분기해 검사하고,
미달 항목마다 `{rule, label, required, actual, shortfall, fix}`를 낸다. `fix`는 재생성 프롬프트에 그대로 들어간다.

**룰을 바꾸면 `REQUIREMENTS` 상수만 고친다.** 판정 로직은 건드릴 필요가 없다.
