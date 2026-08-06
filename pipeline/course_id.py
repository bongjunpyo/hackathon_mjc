"""course_id 조립 — 과목명 정규화 슬러그.

id는 **코드가 만든다. LLM이 짓지 않는다.** LLM이 id를 지으면 재추출마다 값이
달라지고, 그 순간 프론트 체크박스·DB 이수내역·검증기가 서로 어긋난다.
(이슈 #9)

만족하는 성질:
  결정론적   같은 과목명 → 항상 같은 id
  위치 무관  행 순서가 바뀌어도 불변
  가독성     로그에 `itc-네트워크1`로 찍힌다

원본 교과과정표에 학수번호 컬럼이 없어(35개 학과 전수 확인) 조립이 유일한 선택지다.
"""

import re
import unicodedata

_ROMAN_VALUE = {"I": 1, "V": 5, "X": 10}

# 끝에 붙은 로마숫자만 잡는다. 앞에 한글/숫자가 오거나 문자열 전체가 로마숫자인 경우.
# `IT활용`처럼 과목명 중간이나 앞머리의 영문은 건드리지 않는다.
# 로마숫자 사이 공백(`네트워크I I`)은 PDF 추출기에 따라 생기므로 함께 흡수한다.
_TRAILING_ROMAN = re.compile(r"(?<=[^A-Za-z])([IVX](?:\s*[IVX])*)\s*$|^([IVX](?:\s*[IVX])*)$")


def _roman_to_int(s: str) -> int:
    """IV → 4. 글자 수로 세면 IV(4)와 II(2)가 같은 값이 되어 충돌한다.

    실용음악과 `합주실기 II`와 `합주실기 IV`가 실제로 그렇게 충돌했다.
    """
    total = prev = 0
    for ch in reversed(re.sub(r"\s", "", s).upper()):
        value = _ROMAN_VALUE[ch]
        total = total - value if value < prev else total + value
        prev = max(prev, value)
    return total


def make_course_id(dept_id: str, name: str) -> str:
    """`itc` + `프로그래밍언어실습Ⅰ` → `itc-프로그래밍언어실습1`

    `Ⅰ`(U+2160)·`I`(라틴)·`1`이 섞여 있어도 같은 id로 수렴한다. NFKC 정규화가
    전각 로마숫자를 라틴 문자로 펴주고, 그 뒤 로마숫자 규칙이 아라비아로 통일한다.

    괄호 안 내용은 지우지 않고 살린다. `보육교사(인성)론`·`프로그램개발과평가(캡스톤디자인)`
    처럼 괄호가 과목을 구분하는 정보라, 지우면 다른 과목과 섞인다.
    """
    s = unicodedata.normalize("NFKC", name)
    s = _TRAILING_ROMAN.sub(lambda m: str(_roman_to_int(m.group(1) or m.group(2))), s.strip())
    s = re.sub(r"[\s·,\-_/()\[\]]", "", s)
    return f"{dept_id}-{s.lower()}"


def assign_course_ids(dept_id: str, courses: list) -> list:
    """과목 목록에 course_id를 채운다. 동명이과목은 뒤쪽에 -2, -3을 붙인다.

    충돌 순번은 (학년, 학기, 원본 행 순서)로 고정한다 — 정렬 기준이 흔들리면
    재실행 때 순번이 뒤바뀌어 결정론이 깨진다.
    """
    ordered = sorted(enumerate(courses), key=lambda p: (p[1].year, p[1].semester, p[0]))
    seen: dict[str, int] = {}
    for _, course in ordered:
        base = make_course_id(dept_id, course.name)
        seen[base] = seen.get(base, 0) + 1
        course.course_id = base if seen[base] == 1 else f"{base}-{seen[base]}"
    return courses
