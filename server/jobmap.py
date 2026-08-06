"""진로 ↔ 인재양성유형 매핑.

학교가 같은 직무를 두 문서에서 다르게 적는다.

    학과 소개 페이지  careers      "시스템 엔지니어"
    교육과정표        talent_type  "시스템 관리·운용 엔지니어"

역산의 축은 `courses[].talent_type`이라, 사용자가 진로를 고르면 그걸 라벨로 옮겨야
과목이 붙는다. 완전 일치만 보면 모든 진로가 0과목이 된다 — 실제로 그랬다 (이슈 #40).

대응이 없는 진로는 빈 목록을 낸다. 억지로 잇지 않는다 — "학과가 홍보하는 진로에
교육과정 대응이 없다"는 것 자체가 트랙 B의 발견이다.
"""

import re

SPLIT = r"[\s·,/]"
MIN_TOKEN = 2


def normalize(text):
    return re.sub(SPLIT, "", text)


def match_labels(job, labels):
    """목표 직무에 대응하는 인재양성유형 라벨들."""
    target = normalize(job)
    tokens = [t for t in re.split(SPLIT, job) if len(t) >= MIN_TOKEN]

    hits = []
    for label in labels:
        flat = normalize(label)
        # 완전 일치는 곧바로 확정한다. 아래 동률 처리가 "가장 짧은 라벨"을 고르기
        # 때문에, 이걸 먼저 걸러내지 않으면 자기 자신을 버린다 — `의료정보관리전문가
        # 및보건교육사`를 고르면 부분문자열인 `보건교육사`로 매핑돼 11과목이 4과목이 됐다
        if target == flat:
            return [label]
        if target in flat or flat in target:
            hits.append(label)
        elif tokens and all(t in label for t in tokens):
            hits.append(label)

    # 토큰 겹침만 보면 너무 많이 걸린다 — `시스템 엔지니어`가 `시스템관리·운용엔지니어`와
    # `시스템응용SW개발엔지니어` 양쪽에 붙는다(둘 다 "시스템"·"엔지니어" 포함). 그러면
    # 거의 모든 과목이 직무 관련이 되어 역산이 무의미해진다.
    # 목표 직무 밖의 글자가 가장 적은 라벨만 남긴다 = 가장 가까운 것.
    if len(hits) > 1:
        closest = min(len(normalize(h)) for h in hits)
        hits = [h for h in hits if len(normalize(h)) == closest]
    return hits


def choices(dept):
    """사용자가 고를 수 있는 목표 직무.

    인재양성유형을 먼저 놓는다 — 역산의 축이라 과목이 확실히 붙는다.
    진로는 매핑을 거쳐야 하고 대응이 없을 수도 있다.
    """
    seen, out = set(), []
    for value in (dept.get("talent_types") or []) + (dept.get("careers") or []):
        if value not in seen:
            seen.add(value)
            out.append(value)
    return out
