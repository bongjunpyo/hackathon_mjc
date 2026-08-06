"""LLM 없이 도는 임시 생성기.

교육과정표의 편성학년·학기를 그대로 따라 남은 학기를 채운다. 목표 직무를 반영하지
않으므로 **이건 로드맵이 아니라 배치표다** — agent.py가 나오면 교체한다.

이 단계에서 필요한 건 catalog → loop → API 한 줄기가 실제로 도는 것이고,
LLM 없이 P3가 붙여볼 서버가 있는 것이다.
"""


def naive_generate(spec, feedback=None):
    dept = spec["dept"]
    start = (spec["current_year"], spec["current_semester"])
    done = {c["course_id"] for c in spec.get("completed", [])}

    buckets = {}
    for course in dept["courses"]:
        if course["course_id"] in done:
            continue
        if (course["year"], course["semester"]) < start:
            continue
        buckets.setdefault((course["year"], course["semester"]), []).append(course)

    semesters = []
    for (year, semester), courses in sorted(buckets.items()):
        semesters.append(
            {
                "year": year,
                "semester": semester,
                "courses": courses,
                "certificates": [],
                "notes": "",
            }
        )

    _place_liberal_bucket(dept, semesters)
    return {"semesters": semesters}


def _place_liberal_bucket(dept, semesters):
    """교양선택을 `category: "교양"` 블록으로 깐다.

    교육과정표에 교양 과목이 열거되지 않아 학점 버킷(`liberal_elective_credits`)으로만
    온다. 이 블록을 빠뜨리면 검증기의 교양 룰이 **항상** 미달로 나온다.
    """
    remaining = dept.get("liberal_elective_credits", 0)
    if not remaining or not semesters:
        return

    per = max(1, remaining // len(semesters))
    for sem in semesters:
        if remaining <= 0:
            break
        credits = min(per, remaining)
        sem["courses"].append(
            {
                "course_id": f"{dept['dept_id']}-교양선택-{sem['year']}-{sem['semester']}",
                "name": f"교양선택 {credits}학점",
                "credits": credits,
                "category": "교양",
            }
        )
        remaining -= credits

    if remaining:
        semesters[-1]["courses"][-1]["credits"] += remaining
