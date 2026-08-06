"""교육과정표 표 → 과목 목록. 결정론적 헤더 기반 파싱.

35개 학과 PDF를 전수 확인한 결과 필수 5개 열(`교과목명`·`편성학년`·`편성학기`·
`편성학점`·`이수구분`)의 **이름이 전부 동일**했다. 열 이름으로 찾아 읽으면 LLM 없이
파싱된다 — 빠르고, 공짜고, 무엇보다 재실행해도 같은 결과가 나온다.

LLM은 여기서 걷어내고 헤더가 깨진 파일의 폴백으로만 둔다. 판단이 필요 없는 일에
LLM을 쓰면 느리고 비결정적이기만 하다. LLM 예산은 로드맵 에이전트에 쓴다.
"""

import re

from course_id import assign_course_ids
from schema import Course

# 열 이름 → 스키마 필드. 값은 표기 흔들림에 대비한 후보 목록이다.
# `NCS기반`·`현장중심`은 헤더 2행에만 있는 하위 열이다.
COLUMNS = {
    "name": ("교과목명",),
    "year": ("편성학년",),
    "semester": ("편성학기",),
    "credits": ("편성학점",),
    "category": ("이수구분",),
    "talent_type": ("비고",),
    "ncs": ("NCS기반",),
    "field_based": ("현장중심", "현장중심교과"),
}

# 이게 없으면 과목을 만들 수 없다. 나머지는 있으면 쓰고 없으면 넘어간다.
REQUIRED = ("name", "year", "semester", "credits", "category")

# 이수구분 원문 → 스키마 category. `통합전공`은 자유전공학과가 쓴다.
CATEGORY = {"전공과정": "전공", "통합전공": "전공", "교양과정": "교양", "일반선택": "일반선택"}

# `AI oT` → `AIoT`, `I CT최신기술` → `ICT최신기술`.
# 대문자 사이, 또는 대문자와 뒤따르는 소문자 사이에 낀 공백만 지운다.
_SPLIT_ACRONYM = re.compile(r"(?<=[A-Z])\s+(?=[A-Za-z])")


class HeaderNotFound(Exception):
    """필수 열을 찾지 못했다. 호출자는 LLM 폴백으로 넘어간다."""


def _normalize_name(raw: str) -> str:
    """PDF 추출 과정에서 갈라진 공백을 되돌린다. 표시용 이름이다."""
    name = " ".join(raw.split())
    name = _SPLIT_ACRONYM.sub("", name)
    return re.sub(r"\s*([IVX]+)\s*$", r"\1", name)


def _normalize_label(raw: str) -> str | None:
    """직무 라벨의 줄바꿈 흔적을 지운다.

    `시스템관리· 운용엔지니어`처럼 가운뎃점 뒤나 단어 중간에 공백이 끼어 들어온다.
    트랙 B에서 이 값으로 과목을 묶으므로 표기가 흔들리면 같은 직무가 갈라진다.
    """
    label = " ".join(raw.split())
    label = re.sub(r"·\s+", "·", label)
    return re.sub(r"(?<=[가-힣])\s+(?=[가-힣])", "", label) or None


def _find_columns(*header_rows: list[str]) -> dict[str, int]:
    """헤더는 2행이다. `NCS기반` 같은 하위 열은 2행에만 있으므로 함께 훑는다."""
    index = {}
    for field, candidates in COLUMNS.items():
        for row in header_rows:
            for i, cell in enumerate(row):
                if cell.strip() in candidates:
                    index[field] = i
                    break
            if field in index:
                break
    missing = [f for f in REQUIRED if f not in index]
    if missing:
        raise HeaderNotFound(f"필수 열 없음: {missing}")
    return index


def _digits(cell: str) -> int | None:
    m = re.search(r"\d+", cell)
    return int(m.group()) if m else None


def parse_courses(table: str, dept_id: str) -> list[Course]:
    """파이프 구분 표 텍스트에서 과목을 뽑는다.

    행을 건너뛰는 경우는 두 가지다: 헤더 2행(구분자 행 포함), 그리고 학년·학기·학점
    중 하나라도 숫자로 읽히지 않는 행(소계·합계 등).
    """
    lines = [l for l in table.splitlines() if l.strip(" |")]
    if not lines:
        raise HeaderNotFound("표가 비어 있음")

    rows = [[c.strip() for c in l.split("|")] for l in lines]
    col = _find_columns(rows[0], rows[1] if len(rows) > 1 else [])

    def marked(cells: list[str], field: str) -> bool:
        """체크 표시(■·○·V)가 있으면 True. 빈 칸이면 False."""
        i = col.get(field)
        return bool(i is not None and i < len(cells) and cells[i].strip())

    courses = []
    for cells in rows[1:]:
        if len(cells) <= max(col[f] for f in REQUIRED):
            continue

        name = _normalize_name(cells[col["name"]])
        year = _digits(cells[col["year"]])
        semester = _digits(cells[col["semester"]])
        credits = _digits(cells[col["credits"]])
        if not name or year is None or semester is None or credits is None:
            continue

        raw_category = cells[col["category"]]
        talent = cells[col["talent_type"]].strip() if "talent_type" in col else ""

        courses.append(
            Course(
                course_id="",  # assign_course_ids가 채운다
                name=name,
                year=year,
                semester=semester,
                credits=credits,
                category=CATEGORY.get(raw_category, "일반선택"),
                required=False,
                talent_type=_normalize_label(talent) if talent else None,
                ncs=marked(cells, "ncs"),
                # 표에 `현장중심` 열이 없는 학과는 과목명으로 판단한다.
                field_based=marked(cells, "field_based")
                or any(k in name for k in ("현장실습", "캡스톤디자인", "인턴십")),
            )
        )

    if not courses:
        raise HeaderNotFound("헤더는 찾았으나 과목 행이 하나도 없음")

    assign_course_ids(dept_id, courses)
    return courses
