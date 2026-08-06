"""로드맵 생성 에이전트 — LLM이 과목을 고르고, 검증기가 결과를 잡는다.

`planner.generate`와 같은 계약이라 `loop.py`에 그대로 주입된다. 검증·재생성
루프는 손대지 않는다.

**LLM에게는 `course_id`만 고르게 한다.** 학점·이수구분까지 만들게 하면 없는
과목이나 틀린 학점을 지어내고, 그 환각이 검증기를 통과할 수 있다. 후보 목록에서
id만 뽑게 하고 나머지 필드는 카탈로그에서 코드가 채운다 — 지어낼 여지가 없다.

`feedback`은 검증기가 낸 미달 사유다. 그대로 프롬프트에 실어 다시 짜게 한다.
"""

import json
import os
from pathlib import Path

from pydantic import BaseModel, Field

MODEL = "claude-sonnet-5"
MAX_TOKENS = 8000

# 학기당 상한. 넘기면 한 학기에 몰아넣어 "계획"이 아니게 된다.
MAX_CREDITS_PER_SEMESTER = 21


def _load_env() -> None:
    """python-dotenv 없이도 .env를 읽는다. 서버 실행 경로가 달라도 동작하게."""
    env = Path(__file__).with_name(".env")
    if not env.exists():
        return
    for line in env.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())


class SemesterPlan(BaseModel):
    year: int
    semester: int
    course_ids: list[str] = Field(description="카탈로그에 있는 course_id만. 새로 만들지 말 것")
    note: str = Field(default="", description="이 학기의 한 줄 조언 (자격증 준비 시점 등)")


class RoadmapPlan(BaseModel):
    semesters: list[SemesterPlan]
    reasoning: str = Field(default="", description="직무에서 역산한 근거 두세 문장")


PROMPT = """당신은 명지전문대학 학생의 학기별 수강 로드맵을 짜는 학사 설계자다.

## 학생
- 학과: {dept_name} ({years}년제)
- 현재: {current_year}학년 {current_semester}학기
- 목표 직무: **{target_job}**
- 이미 이수: {completed_count}과목

## 남은 학기
{semesters}

## 수강 가능 과목 (이 목록의 course_id만 사용한다)
{catalog}

## 졸업요건
- 총 {total}학점 · 교양 {liberal}학점 · 전공 {major}학점
- 교양선택 {liberal_bucket}학점은 별도 배치되므로 당신은 신경 쓰지 않는다

## 규칙
1. **course_id는 위 목록에서만 고른다.** 목록에 없는 id를 만들면 그 과목은 버려진다.
2. 목표 직무(`{target_job}`)로 표시된 과목을 우선 배치한다. 이게 이 로드맵의 존재 이유다.
3. `required: true`인 과목은 반드시 넣는다.
4. 한 학기 {max_credits}학점을 넘기지 않는다.
5. 선수 관계가 이름에서 드러나면(예: `C언어I` → `C언어II`) 순서를 지킨다.
6. 남은 학기를 고르게 채운다. 한 학기를 비우고 다른 학기에 몰지 않는다.
7. `note`에는 그 학기에 준비하면 좋을 자격증이나 현장실습 시점을 한 줄로 적는다.

## 이 학과가 안내한 자격증
{certificates}
{feedback}"""

FEEDBACK_BLOCK = """
## ⚠ 이전 로드맵이 졸업요건에 미달했다
{feedback}

미달분을 채워서 다시 짜라. 이미 넣은 과목은 유지하고 부족한 만큼만 더한다."""


def _catalog_lines(pool: list[dict], job: str) -> str:
    """LLM이 읽을 후보 목록. 목표 직무 과목을 먼저 보여준다."""

    def key(c):
        return (c.get("talent_type") != job, not c["required"], c["year"], c["semester"])

    lines = []
    for c in sorted(pool, key=key):
        tags = []
        if c["required"]:
            tags.append("필수")
        if c.get("talent_type") == job:
            tags.append("★목표직무")
        elif c.get("talent_type"):
            tags.append(c["talent_type"])
        if c.get("field_based"):
            tags.append("현장중심")
        tag = f" [{' '.join(tags)}]" if tags else ""
        lines.append(
            f"- {c['course_id']} | {c['name']} | {c['year']}-{c['semester']} | "
            f"{c['credits']}학점 | {c['category']}{tag}"
        )
    return "\n".join(lines)


def _remaining_semesters(years: int, start: tuple[int, int]) -> list[tuple[int, int]]:
    return [
        (y, s) for y in range(1, years + 1) for s in (1, 2) if (y, s) >= start
    ]


def generate(spec, feedback=None, attempt=1):
    """LLM으로 로드맵을 짠다. `planner.generate`와 같은 계약."""
    _load_env()
    import anthropic

    dept = spec["dept"]
    job = spec["target_job"]
    start = (spec["current_year"], spec["current_semester"])
    done = {c.get("course_id") for c in spec.get("completed", [])}

    pool = [
        c
        for c in dept["courses"]
        if c["course_id"] not in done and (c["year"], c["semester"]) >= start
    ]
    by_id = {c["course_id"]: c for c in pool}
    remaining = _remaining_semesters(dept["years"], start)

    from validator import REQUIREMENTS

    req = REQUIREMENTS.get(dept["years"], REQUIREMENTS[3])
    prompt = PROMPT.format(
        dept_name=dept["dept_name"],
        years=dept["years"],
        current_year=start[0],
        current_semester=start[1],
        target_job=job,
        completed_count=len(done),
        semesters=", ".join(f"{y}학년 {s}학기" for y, s in remaining),
        catalog=_catalog_lines(pool, job),
        total=req["total_credits"],
        liberal=req["liberal_credits"],
        major=req["major_credits"],
        liberal_bucket=dept.get("liberal_elective_credits", 0),
        max_credits=MAX_CREDITS_PER_SEMESTER,
        certificates=", ".join(dept.get("certificates", [])) or "(없음)",
        feedback=FEEDBACK_BLOCK.format(feedback=feedback) if feedback else "",
    )

    client = anthropic.Anthropic()
    response = client.messages.parse(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        thinking={"type": "adaptive"},
        messages=[{"role": "user", "content": prompt}],
        output_format=RoadmapPlan,
    )
    plan = response.parsed_output
    if plan is None:
        raise RuntimeError("LLM이 스키마에 맞는 응답을 내지 못했다")

    return _materialize(plan, by_id, remaining, dept, job)


def _materialize(plan, by_id, remaining, dept, job):
    """LLM이 고른 id를 카탈로그 데이터로 바꾼다.

    카탈로그에 없는 id는 조용히 버린다 — 환각을 검증기까지 흘리지 않는다.
    한 과목이 두 학기에 걸쳐 나오면 앞 학기만 남긴다.
    """
    seen = set()
    semesters = []
    for item in plan.semesters:
        if (item.year, item.semester) not in remaining:
            continue
        courses = []
        for cid in item.course_ids:
            course = by_id.get(cid)
            if course and cid not in seen:
                seen.add(cid)
                courses.append(course)
        semesters.append(
            {
                "year": item.year,
                "semester": item.semester,
                "courses": courses,
                "credits": sum(c["credits"] for c in courses),
                "certificates": [],
                "notes": item.note,
            }
        )

    # LLM이 빠뜨린 학기를 채운다. 학기 수가 모자라면 재학 학기 요건에서 걸린다.
    have = {(s["year"], s["semester"]) for s in semesters}
    for y, s in remaining:
        if (y, s) not in have:
            semesters.append(
                {
                    "year": y,
                    "semester": s,
                    "courses": [],
                    "credits": 0,
                    "certificates": [],
                    "notes": "",
                }
            )

    semesters.sort(key=lambda s: (s["year"], s["semester"]))

    from planner import _place_certificates, _place_liberal_bucket

    _place_liberal_bucket(dept, semesters)
    _place_certificates(dept, semesters)
    return {"semesters": semesters, "reasoning": plan.reasoning}
