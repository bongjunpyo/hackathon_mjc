"""졸업요건 검증기 — 순수 규칙 코드. LLM을 쓰지 않는다."""

# 출처: docs/DESIGN.md §5 졸업요건 룰
REQUIREMENTS = {
    2: {"total_credits": 75, "liberal_credits": 6, "major_credits": 45, "semesters": 4},
    3: {"total_credits": 110, "liberal_credits": 10, "major_credits": 66, "semesters": 6},
}

CATEGORIES = {"전공", "교양", "일반선택"}

LABELS = {
    "total_credits": "총 학점",
    "liberal_credits": "교양 학점",
    "major_credits": "전공 학점",
    "semesters": "재학 학기",
    "malformed_course": "과목 형식 오류",
}

FIXES = {
    "total_credits": "아무 과목으로든 {shortfall}학점을 더 채우세요",
    "liberal_credits": "교양 과목으로 {shortfall}학점을 더 채우세요",
    "major_credits": "전공 과목으로 {shortfall}학점을 더 채우세요",
    "semesters": "과목을 {shortfall}개 학기에 더 나눠 배치하세요",
    "malformed_course": (
        "과목 {shortfall}개에 credits(정수)와 category(전공|교양|일반선택)가 "
        "없거나 형식이 틀렸습니다. 고쳐서 다시 짜세요"
    ),
}


def _sound(course):
    """LLM이 조립한 과목이라 스키마 보장이 없다. 학점 집계에 쓸 수 있는지 본다."""
    credits = course.get("credits")
    return (
        isinstance(credits, int)
        and not isinstance(credits, bool)
        and course.get("category") in CATEGORIES
    )


def _credits(courses, category=None):
    return sum(
        c["credits"] for c in courses if category is None or c["category"] == category
    )


def _check(details, rule, required, actual):
    if actual >= required:
        return
    shortfall = required - actual
    details.append(
        {
            "rule": rule,
            "label": LABELS[rule],
            "required": required,
            "actual": actual,
            "shortfall": shortfall,
            "fix": FIXES[rule].format(shortfall=shortfall),
        }
    )


def validate_roadmap(semesters, years, completed=None, completed_semesters=0):
    """로드맵은 **남은 학기**만 담고 있다. 이수분을 합쳐야 재학생이 통과할 수 있다.

    합산하지 않으면 2학년 학생은 어떤 로드맵으로도 졸업요건을 못 채우고, `fix`가
    "이미 지나간 학기에 과목을 나눠 배치하라"는 이행 불가능한 지시를 재생성 프롬프트로
    보내 max_retries를 전부 소진한다.
    """
    # 경계(catalog)가 years를 먼저 막지만, 검증기 자체도 KeyError로 죽지 않게 한다.
    # 더 빡빡한 3년제 기준으로 떨어뜨린다 — 통과시켜 놓고 나중에 못 졸업하는 것보다 낫다
    req = REQUIREMENTS.get(years, REQUIREMENTS[3])

    raw = [c for s in semesters for c in s.get("courses", [])] + list(completed or [])
    courses = [c for c in raw if _sound(c)]
    malformed = len(raw) - len(courses)

    total = _credits(courses)
    liberal = _credits(courses, "교양")
    major = _credits(courses, "전공")
    semester_count = len(semesters) + completed_semesters

    details = []
    if malformed:
        # 깨진 과목은 집계에서 빼되 버리지 않는다 — 재생성이 뭘 고칠지 알아야 한다.
        # 다른 룰과 달리 "부족한 학점"이 아니라 "고쳐야 할 과목 수"다
        details.append(
            {
                "rule": "malformed_course",
                "label": LABELS["malformed_course"],
                "required": 0,
                "actual": malformed,
                "shortfall": malformed,
                "fix": FIXES["malformed_course"].format(shortfall=malformed),
            }
        )
    _check(details, "total_credits", req["total_credits"], total)
    _check(details, "liberal_credits", req["liberal_credits"], liberal)
    _check(details, "major_credits", req["major_credits"], major)
    _check(details, "semesters", req["semesters"], semester_count)

    return {
        "passed": not details,
        "total_credits": total,
        "liberal_credits": liberal,
        "major_credits": major,
        "semesters": semester_count,
        "details": details,
    }
