"""목표 직무에서 역산하는 로드맵 생성기. LLM을 쓰지 않는다.

설계서 §1의 차별화가 "졸업 가능 여부 **확인**"이 아니라 "직무에서 역산한 경로 **설계**"다.
그 역산을 학교가 이미 매긴 과목↔직무 라벨(`talent_type`)로 한다 — 추천 근거가
데이터 안에 있어서, "왜 이 과목이냐"는 질문에 답할 수 있다.

**직무 경로와 졸업요건은 별개로 다룬다.**
1차는 직무에 필요한 것만 짠다(필수 + 직무 매칭). 졸업요건이 모자라면 검증기가 잡아내고,
그 피드백을 받아 관련 분야 → 나머지 순으로 채운다. 두 관심사가 섞이지 않고,
재생성 루프가 실제로 일을 한다.
"""

from validator import REQUIREMENTS

# 재생성할 때마다 한 티어씩 더 연다
TIERS = 3


def generate(spec, feedback=None, attempt=1):
    dept = spec["dept"]
    job = spec["target_job"]
    start = (spec["current_year"], spec["current_semester"])
    done = {c.get("course_id") for c in spec.get("completed", [])}

    pool = [
        c
        for c in dept["courses"]
        if c["course_id"] not in done and (c["year"], c["semester"]) >= start
    ]
    electives = [c for c in pool if not c["required"]]

    # 우선순위: 목표 직무 → 라벨은 있으나 다른 직무 → 라벨 없음.
    # attempt가 오를수록 뒤 티어가 열린다
    tiers = [
        [c for c in electives if c.get("talent_type") == job],
        [c for c in electives if c.get("talent_type") not in (None, job)],
        [c for c in electives if not c.get("talent_type")],
    ]
    # 필수 + 직무 매칭은 1차부터 전부. 그 뒤 티어는 **모자란 만큼만** 연다 —
    # 통째로 열면 어떤 직무를 골라도 결국 같은 로드맵이 되어 역산이 무의미해진다
    chosen = [c for c in pool if c["required"]] + tiers[0]
    if attempt > 1:
        _fill_to_requirement(chosen, tiers[1 : min(attempt, TIERS)], dept, spec)

    semesters = _by_semester(chosen, job)
    _place_liberal_bucket(dept, semesters)
    _place_certificates(dept, semesters)
    return {"semesters": semesters}


def _fill_to_requirement(chosen, tiers, dept, spec):
    """졸업요건에 모자란 만큼만 다음 티어에서 가져온다.

    전공이 모자라면 전공부터 집는다. 총학점만 모자라면 아무거나로 메운다.
    """
    req = REQUIREMENTS.get(dept["years"], REQUIREMENTS[3])
    base = list(spec.get("completed") or [])
    bucket = dept.get("liberal_elective_credits", 0)

    def short():
        pool = chosen + base
        total = sum(c["credits"] for c in pool) + bucket
        major = sum(c["credits"] for c in pool if c["category"] == "전공")
        return req["total_credits"] - total, req["major_credits"] - major

    for tier in tiers:
        # 전공이 모자란 상태면 전공 과목을 먼저 집는다
        for course in sorted(tier, key=lambda c: c["category"] != "전공"):
            total_gap, major_gap = short()
            if total_gap <= 0 and major_gap <= 0:
                return
            if major_gap <= 0 and course["category"] == "전공" and total_gap <= 0:
                continue
            chosen.append(course)


def _by_semester(courses, job):
    """직무 관련 과목을 표시하고 학기 안에서 앞으로 낸다.

    전문대 교육과정은 여유 학점이 적어 어떤 직무를 골라도 과목 **집합**은 크게
    다르지 않다. 그래도 "무엇이 목표 직무 때문에 들어갔는지"는 다르므로,
    표시해서 화면이 강조할 수 있게 한다.
    """
    buckets = {}
    for course in courses:
        tagged = {**course, "job_related": course.get("talent_type") == job}
        buckets.setdefault((course["year"], course["semester"]), []).append(tagged)

    semesters = []
    for (year, semester), items in sorted(buckets.items()):
        items.sort(key=lambda c: not c["job_related"])
        related = sum(1 for c in items if c["job_related"])
        semesters.append(
            {
                "year": year,
                "semester": semester,
                "courses": items,
                "certificates": [],
                "notes": f"{job} 관련 {related}과목" if related else "",
            }
        )
    return semesters


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
                "job_related": False,
            }
        )
        remaining -= credits

    if remaining:
        semesters[-1]["courses"][-1]["credits"] += remaining


def _place_certificates(dept, semesters):
    """자격증은 뒤쪽 학기부터 배치한다 — 관련 과목을 들은 뒤 따는 게 순서다."""
    certificates = dept.get("certificates", [])
    if not certificates or len(semesters) < 2:
        return

    targets = semesters[1:]  # 첫 학기에는 딸 수 없다
    for i, cert in enumerate(certificates):
        targets[i % len(targets)]["certificates"].append(cert)
