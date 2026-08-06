"""교육과정표 PDF → courses.json 구조화 추출.

파이프라인은 학과별 파서를 만들지 않는다. 어느 학과의 표든 같은 경로를 통과한다:

    PDF → pdfplumber 표 추출 → LLM 구조화 → 스키마 검증 → (실패 시 재시도)

명지전문대 교과과정표 PDF는 학과마다 열 구성이 조금씩 다르고 교과목명에
`네트워크I I`, `AI oT` 같은 공백 깨짐이 있다. 열 이름을 코드로 고정하지 않고
LLM에 표 원문을 넘기는 이유다.
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path

import anthropic
import pdfplumber

from course_id import assign_course_ids
from schema import DeptCurriculum

MODEL = "claude-sonnet-5"
MAX_RETRIES = 3

# 교양필수는 전 학과 공통이며 교과과정표(전공 전용)에 실리지 않는다.
# 졸업요건 페이지(menu_idx=1942) 기준으로 주입한다.
LIBERAL_REQUIRED = [
    {"name": "인성채플", "credits": 1},
    {"name": "성경과삶", "credits": 2},
]

GRADUATION_RULES = {2: {"total": 75, "liberal": 6, "major": 45}, 3: {"total": 110, "liberal": 10, "major": 66}}

PROMPT = """다음은 명지전문대학 {dept_name} 교과과정표 PDF에서 추출한 표 원문이다.

{table}

이 표를 courses.json 스키마로 구조화하라.

규칙:
- `교과목명` 열이 과목 이름이다. 원본에는 공백 깨짐이 있다 (`네트워크I I` → `네트워크II`,
  `i OS프로그래밍` → `iOS프로그래밍`, `AI oT` → `AIoT`, `I CT최신기술` → `ICT최신기술`).
  로마숫자 I/II는 원본 표기를 살리되 공백만 제거한다.
- `course_id`는 빈 문자열로 둔다. 코드가 과목명에서 조립한다 (이슈 #9).
- `편성학년`/`편성학기`의 "1학년"·"1학기"에서 숫자만 뽑아 year/semester로.
- `이수구분`이 "전공과정"이면 category는 "전공", "교양과정"이면 "교양".
- `talent_type`은 맨 오른쪽 비고 열의 직무 라벨 (예: "시스템응용SW개발엔지니어").
  `·`나 공백이 깨져 있으면 정규화한다. 값이 없으면 null.
- `ncs`는 교과목 구분에 NCS기반 표시가 있으면 true.
- `field_based`는 현장실습·캡스톤디자인 등 현장 중심 과목이면 true.
- `required`는 이 표에 실린 전공 과목의 경우 false로 둔다 (필수 여부가 표에 없다).

표에 없는 과목을 지어내지 마라. 표에 있는 행만 그대로 옮긴다."""


def extract_tables(pdf_path: Path) -> str:
    """PDF의 모든 표를 파이프 구분 텍스트로 펼친다."""
    rows = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            for table in page.extract_tables():
                for row in table:
                    cells = [(c or "").replace("\n", " ").strip() for c in row]
                    if any(cells):
                        rows.append(" | ".join(cells))
    return "\n".join(rows)


def normalize_liberal(dept: DeptCurriculum) -> DeptCurriculum:
    """교양필수를 실명으로 주입하고, 교양선택은 필요 학점만 남긴다.

    교과과정표에는 전공 과목만 실려 있다. 교양선택은 과목마다 학점이 달라
    열거가 불가능하므로 학점 버킷으로 처리한다 (팀 결정 2026-08-06).
    """
    rules = GRADUATION_RULES[dept.years]
    existing = {c.name for c in dept.courses}

    for item in LIBERAL_REQUIRED:
        if item["name"] in existing:
            continue
        slug = "chapel" if item["name"] == "인성채플" else "bible-life"
        dept.courses.append(
            DeptCurriculum.model_fields["courses"].annotation.__args__[0](
                course_id=f"{dept.dept_id}-1-1-{slug}",
                name=item["name"],
                year=1,
                semester=1,
                credits=item["credits"],
                category="교양",
                required=True,
            )
        )

    required_credits = sum(i["credits"] for i in LIBERAL_REQUIRED)
    dept.liberal_elective_credits = max(0, rules["liberal"] - required_credits)
    return dept


def structure(table: str, dept_id: str, dept_name: str, years: int, tier: int) -> tuple[DeptCurriculum, int]:
    """LLM 구조화 → 스키마 검증. 실패하면 오류를 붙여 재시도한다."""
    client = anthropic.Anthropic()
    prompt = PROMPT.format(table=table, dept_id=dept_id, dept_name=dept_name)
    messages = [{"role": "user", "content": prompt}]

    for attempt in range(1, MAX_RETRIES + 1):
        response = client.messages.parse(
            model=MODEL,
            max_tokens=16000,
            messages=messages,
            output_format=DeptCurriculum,
        )
        dept = response.parsed_output
        if dept is None:
            messages.append({"role": "user", "content": "스키마에 맞는 JSON을 반환하지 못했다. 다시 시도하라."})
            continue

        assign_course_ids(dept_id, dept.courses)
        problems = validate(dept, dept_id, years)
        if not problems:
            dept.dept_id, dept.dept_name, dept.years, dept.tier = dept_id, dept_name, years, tier
            return dept, attempt

        print(f"  [재시도 {attempt}] 검증 실패: {'; '.join(problems)}", file=sys.stderr)
        messages.append({"role": "assistant", "content": dept.model_dump_json()})
        messages.append({"role": "user", "content": "다음 문제를 고쳐 다시 출력하라:\n- " + "\n- ".join(problems)})

    raise RuntimeError(f"{dept_name}: {MAX_RETRIES}회 시도 후에도 검증 통과 실패")


def validate(dept: DeptCurriculum, dept_id: str, years: int) -> list[str]:
    """LLM 출력이 실제로 쓸 수 있는지 확인한다. 통과하면 빈 리스트."""
    problems = []
    if not dept.courses:
        problems.append("과목이 하나도 추출되지 않았다")

    # course_id는 코드가 조립하므로 여기서는 조립 결과만 확인한다.
    ids = [c.course_id for c in dept.courses]
    if len(ids) != len(set(ids)):
        dupes = {i for i in ids if ids.count(i) > 1}
        problems.append(f"course_id 중복: {sorted(dupes)}")

    for c in dept.courses:
        if not 1 <= c.year <= years:
            problems.append(f"{c.name}: 학년 {c.year}이 1~{years} 범위 밖")
        if c.semester not in (1, 2):
            problems.append(f"{c.name}: 학기 {c.semester}이 1 또는 2가 아님")
        if re.search(r"[A-Za-z]\s+[A-Za-z]|\s{2,}", c.name):
            problems.append(f"{c.name}: 공백 깨짐이 남아 있음")

    major = sum(c.credits for c in dept.courses if c.category == "전공")
    need = GRADUATION_RULES[years]["major"]
    if major < need:
        problems.append(f"전공 학점 합계 {major}이 졸업요건 {need} 미만 — 표를 빠뜨렸을 가능성")

    return problems[:8]


def main() -> None:
    ap = argparse.ArgumentParser(description="교육과정표 PDF → courses.json")
    ap.add_argument("pdf")
    ap.add_argument("--dept-id", required=True)
    ap.add_argument("--dept-name", required=True)
    ap.add_argument("--years", type=int, required=True, choices=[2, 3])
    ap.add_argument("--tier", type=int, default=2)
    ap.add_argument("--source-url", default="")
    ap.add_argument("--out", default="../data/depts")
    args = ap.parse_args()

    table = extract_tables(Path(args.pdf))
    if not table.strip():
        sys.exit(f"표를 추출하지 못했다: {args.pdf}")
    print(f"표 {len(table.splitlines())}행 추출", file=sys.stderr)

    dept, attempts = structure(table, args.dept_id, args.dept_name, args.years, args.tier)
    dept = normalize_liberal(dept)
    dept.source_url = args.source_url
    dept.extraction_confidence = round(1.0 - (attempts - 1) * 0.15, 2)

    out = Path(args.out) / f"{args.dept_id}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(dept.model_dump_json(indent=2), encoding="utf-8")

    major = sum(c.credits for c in dept.courses if c.category == "전공")
    liberal = sum(c.credits for c in dept.courses if c.category == "교양")
    print(
        f"{out} 저장 — {len(dept.courses)}과목 "
        f"(전공 {major}학점 / 교양필수 {liberal}학점 + 교양선택 {dept.liberal_elective_credits}학점), "
        f"시도 {attempts}회",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
