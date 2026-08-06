"""트랙 B — 학교용 교육과정 진단 리포트.

학과가 **홍보하는 진로**(`careers`, 학과 소개 페이지)와 **교육과정이 실제로 라벨링한
인재양성유형**(`courses[].talent_type`)을 대조한다. 그 간극이 리포트의 내용이다.

NCS 직무기술서는 수집되지 않았으므로 쓰지 않는다. 학교가 자기 문서에 써둔 두 값만
비교한다 — 근거가 전부 학교 안에 있어서 "이 판단의 출처가 뭐냐"에 답할 수 있다.
"""

import json
import logging
import re
from itertools import combinations
from pathlib import Path

from jobmap import match_labels

log = logging.getLogger(__name__)

# 파이프라인 산출물. 자격증 3분류는 P1이 이미 계산해뒀다 —
# 여기서 다시 계산하면 화면과 파이프라인 지표가 갈린다
REPORTS_DIR = Path(__file__).parent.parent / "data" / "reports"

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
    """진로와 인재양성유형을 잇는다 — `/roadmap`과 **같은 구현**을 쓴다.

    따로 구현했더니 갈라졌다. `jobmap`에만 동률 처리가 있어서 리포트는 `시스템
    엔지니어`에 라벨 2개를 붙이고 로드맵은 1개를 붙였다 — 두 화면이 같은 진로를
    다르게 말하고 커버리지가 과대 집계됐다. 매핑 규칙은 한 곳에만 둔다.
    """
    return match_labels(career, labels)


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
        # others에 자기 자신을 넣으면 안 된다 — `any(p in o for o in others)`가 o=a로
        # 항상 참이 되어 가운뎃점을 무조건 구분자로 본다. `시스템관리·운용엔지니어`가
        # ['시스템관리','운용엔지니어']로 쪼개져 same_set 오탐의 재료가 된다
        pa = split_label(a, [x for x in raw_labels if x != a])
        pb = split_label(b, [x for x in raw_labels if x != b])
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
        # 분모가 전공 학점이므로 분자도 전공만 센다. 전 과목을 세면 비전공에 붙은
        # talent_type(실데이터에 15건 — ece의 일반선택 등)이 섞여 100%를 넘을 수 있다 (이슈 #34)
        covered = [
            c
            for c in dept["courses"]
            if c.get("talent_type") in matched and c.get("category") == "전공"
        ]
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
        **_pipeline_metrics(dept["dept_id"]),
    }


def _pipeline_metrics(dept_id, root=None):
    """파이프라인이 낸 자격증 3분류·NCS 비율을 응답에 합친다.

    계산하지 않고 읽는다. `supported`/`unsupported`/`unevaluated` 구분은
    P1이 교육과정표 대조로 만든 값이고, 특히 **판정불가를 결손으로 세지 않는 것**이
    그 데이터에 이미 반영돼 있다.

    파일이 없거나 깨져도 리포트 본체는 나가야 한다 — 자격증 절만 비운다.
    """
    path = (Path(root) if root else REPORTS_DIR) / f"{dept_id}.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        log.warning("파이프라인 리포트를 읽지 못했습니다 (%s): %s", path.name, e)
        return {"certificates": None, "ncs_ratio": None}

    certs = data.get("certificates") or {}
    return {
        "certificates": {
            "total": certs.get("total", 0),
            "supported": certs.get("supported", 0),
            # 교육과정에 대응 과목이 없는 자격증 — 이게 진짜 결손이다
            "unsupported": certs.get("unsupported") or [],
            # 자격증명 추출이 불완전해 판정하지 못한 것. 결손이 아니다
            "unevaluated": certs.get("unevaluated") or [],
        },
        "ncs_ratio": data.get("ncs_ratio"),
    }
