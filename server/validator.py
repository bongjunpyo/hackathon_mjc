"""졸업요건 검증기 — 순수 규칙 코드. LLM을 쓰지 않는다."""

# 출처: docs/DESIGN.md §5 졸업요건 룰
REQUIREMENTS = {
    2: {"total_credits": 75, "liberal_credits": 6, "major_credits": 45, "semesters": 4},
    3: {"total_credits": 110, "liberal_credits": 10, "major_credits": 66, "semesters": 6},
}

LABELS = {
    "total_credits": "총 학점",
    "liberal_credits": "교양 학점",
    "major_credits": "전공 학점",
    "semesters": "재학 학기",
}

FIXES = {
    "total_credits": "아무 과목으로든 {shortfall}학점을 더 채우세요",
    "liberal_credits": "교양 과목으로 {shortfall}학점을 더 채우세요",
    "major_credits": "전공 과목으로 {shortfall}학점을 더 채우세요",
    "semesters": "과목을 {shortfall}개 학기에 더 나눠 배치하세요",
}


def _credits(semesters, category=None):
    return sum(
        c["credits"]
        for s in semesters
        for c in s["courses"]
        if category is None or c["category"] == category
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


def validate_roadmap(semesters, years):
    req = REQUIREMENTS[years]

    total = _credits(semesters)
    liberal = _credits(semesters, "교양")
    major = _credits(semesters, "전공")

    details = []
    _check(details, "total_credits", req["total_credits"], total)
    _check(details, "liberal_credits", req["liberal_credits"], liberal)
    _check(details, "major_credits", req["major_credits"], major)
    _check(details, "semesters", req["semesters"], len(semesters))

    return {
        "passed": not details,
        "total_credits": total,
        "liberal_credits": liberal,
        "major_credits": major,
        "semesters": len(semesters),
        "details": details,
    }
