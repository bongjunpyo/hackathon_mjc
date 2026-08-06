"""트랙 B — 학교용 교육과정 진단 리포트.

학과가 **홍보하는 진로**(`careers`, 학과 소개 페이지)와 **교육과정이 실제로 라벨링한
인재양성유형**(`courses[].talent_type`)을 대조한다. 그 간극이 리포트의 내용이다.

NCS 직무기술서는 수집되지 않았으므로 쓰지 않는다. 학교가 자기 문서에 써둔 두 값만
비교한다 — 근거가 전부 학교 안에 있어서 "이 판단의 출처가 뭐냐"에 답할 수 있다.
"""

import re
from itertools import combinations

# 직무 자리에 들어온 직무 아닌 값
NOT_A_JOB = {"공통", "전체", "-", "기타"}

# 오타 판정 최소 길이. 짧은 이름은 진짜로 다른 직무일 수 있다 —
# `공간디자이너`/`제품디자이너`, `청소년상담사`/`청소년지도사`가 그렇다
NEAR_MIN_LEN = 10
NEAR_MAX_DISTANCE = 2


def split_label(raw, others):
    """한 칸에 묶인 여러 직무를 쪼갠다.

    쉼표·슬래시는 항상 구분자다. 가운뎃점은 애매하다 — `시스템 관리·운용 엔지니어`에서는
    이름의 일부고 `부동산중개사·건물관리사`에서는 구분자다. 쪼갠 조각이 같은 학과의
    다른 라벨로도 존재하면 구분자로 본다.
    """
    parts = [p.strip() for p in re.split(r"[,/]", raw) if p.strip()]
    if len(parts) > 1:
        return parts

    dotted = [p.strip() for p in raw.split("·") if p.strip()]
    if len(dotted) > 1 and all(any(p in o for o in others) for p in dotted):
        return dotted
    return [raw.strip()]


def _normalize(text):
    return re.sub(r"[\s·,/]", "", text)


def _distance(a, b):
    """레벤슈타인 거리. 라벨이 짧아 단순 DP로 충분하다."""
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def _raw_labels(dept):
    seen = []
    for course in dept["courses"]:
        label = course.get("talent_type")
        if label and label not in seen:
            seen.append(label)
    return seen


def _matches(career, labels):
    """진로와 인재양성유형을 잇는다. 이름이 다르므로 토큰 겹침으로 본다.

    `시스템 엔지니어` ↔ `시스템 관리·운용 엔지니어` 처럼 학교가 두 문서에서 다르게
    쓴 이름을 이어야 한다. 완전 일치만 보면 대부분이 결손으로 잡힌다.
    """
    target = _normalize(career)
    hits = []
    for label in labels:
        normalized = _normalize(label)
        if target == normalized or target in normalized or normalized in target:
            hits.append(label)
            continue
        tokens = [t for t in re.split(r"[\s·,/]", career) if len(t) >= 2]
        if tokens and all(t in label for t in tokens):
            hits.append(label)
    return hits


def _label_mismatches(dept, raw_labels):
    found = []

    for label in raw_labels:
        if label.strip() in NOT_A_JOB:
            found.append(
                {
                    "kind": "not_a_job",
                    "labels": [label],
                    "note": f"'{label}'은 직무명이 아닙니다. 인재양성유형 자리에 들어가 있습니다",
                }
            )
        parts = split_label(label, [x for x in raw_labels if x != label])
        if len(parts) > 1:
            found.append(
                {
                    "kind": "joined",
                    "labels": [label],
                    "parts": parts,
                    "note": f"직무 {len(parts)}개가 한 칸에 묶여 있습니다. 과목별로 나눠야 집계됩니다",
                }
            )

    for a, b in combinations(raw_labels, 2):
        pa = split_label(a, raw_labels)
        pb = split_label(b, raw_labels)
        if len(pa) > 1 and {_normalize(x) for x in pa} == {_normalize(x) for x in pb}:
            found.append(
                {
                    "kind": "same_set",
                    "labels": [a, b],
                    "note": "같은 직무 묶음인데 순서·표기가 달라 다른 라벨로 집계됩니다",
                }
            )
            continue
        na, nb = _normalize(a), _normalize(b)
        if (
            min(len(na), len(nb)) >= NEAR_MIN_LEN
            and abs(len(na) - len(nb)) <= 1
            and 0 < _distance(na, nb) <= NEAR_MAX_DISTANCE
        ):
            found.append(
                {
                    "kind": "near_duplicate",
                    "labels": [a, b],
                    "note": "오타로 같은 직무가 두 라벨로 갈린 것으로 보입니다",
                }
            )
    return found


def build_report(dept):
    raw_labels = _raw_labels(dept)
    major_credits = sum(
        c["credits"] for c in dept["courses"] if c.get("category") == "전공"
    )

    jobs = []
    for career in dept.get("careers") or []:
        matched = _matches(career, raw_labels)
        covered = [c for c in dept["courses"] if c.get("talent_type") in matched]
        credits = sum(c["credits"] for c in covered)
        jobs.append(
            {
                "job": career,
                "matched_labels": matched,
                "coverage_pct": round(credits / major_credits * 100, 1)
                if major_credits
                else 0,
                "covered_credits": credits,
                "covered_courses": [
                    {"course_id": c["course_id"], "name": c["name"], "credits": c["credits"]}
                    for c in covered
                ],
                "gaps": []
                if matched
                else ["교육과정표의 인재양성유형에 대응하는 라벨이 없습니다"],
            }
        )

    return {
        "dept_id": dept["dept_id"],
        "dept_name": dept["dept_name"],
        # Tier 2는 파이프라인 자동 통과다. 신뢰도를 같이 내지 않으면
        # "품질은 지표로 정직 공개"(설계서 §5)가 성립하지 않는다
        "tier": dept.get("tier"),
        "extraction_confidence": dept.get("extraction_confidence"),
        "major_credits": major_credits,
        "jobs": jobs,
        "label_mismatches": _label_mismatches(dept, raw_labels),
    }
