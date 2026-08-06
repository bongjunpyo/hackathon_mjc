"""data/depts/*.json을 읽는 유일한 창구.

여기가 시스템 경계다. 깨진 데이터는 로드 시점에 죽인다 — 새벽에 "왜 이 과목이
미이수로 나오지"를 추적하는 것보다 지금 예외를 보는 게 싸다.
"""

import json
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data" / "depts"

CATEGORIES = {"전공", "교양", "일반선택"}
YEARS = {2, 3}


class CatalogError(Exception):
    pass


def _validate(dept):
    dept_id = dept.get("dept_id", "?")

    if dept.get("years") not in YEARS:
        raise CatalogError(
            f"{dept_id}: years가 {dept.get('years')}다. 검증기 REQUIREMENTS 키는 {sorted(YEARS)}뿐"
        )

    seen = set()
    duplicates = set()
    for course in dept["courses"]:
        course_id = course.get("course_id")
        if not course_id:
            raise CatalogError(f"{dept_id}: course_id가 빈 과목이 있다 — {course.get('name')}")
        if course_id in seen:
            duplicates.add(course_id)
        seen.add(course_id)

        if course["category"] not in CATEGORIES:
            raise CatalogError(
                f"{dept_id}: 모르는 category '{course['category']}' — {course['name']}"
            )

    if duplicates:
        raise CatalogError(f"{dept_id}: course_id 중복 {sorted(duplicates)}")


def load_dept(dept_id, root=None):
    path = (Path(root) if root else DATA_DIR) / f"{dept_id}.json"
    if not path.exists():
        raise CatalogError(f"학과 데이터가 없다: {path}")

    dept = json.loads(path.read_text(encoding="utf-8"))
    _validate(dept)
    return dept


def list_depts(root=None):
    directory = Path(root) if root else DATA_DIR
    depts = []
    for path in sorted(directory.glob("*.json")):
        # 파이프라인이 추출 리포트(_report.json, 배열)를 같은 디렉터리에 떨군다.
        # 학과로 읽으면 GET /depts가 통째로 죽는다 (이슈 #22)
        if path.name.startswith("_"):
            continue
        dept = json.loads(path.read_text(encoding="utf-8"))
        depts.append(
            {
                "dept_id": dept["dept_id"],
                "dept_name": dept["dept_name"],
                "years": dept["years"],
                "tier": dept["tier"],
                # 입력 화면의 목표 직무 드롭다운 재료. 없으면 프론트가 하드코딩해야 하고,
                # 그러면 "전 학과 대응"이 성립하지 않는다.
                # talent_types가 드롭다운의 **기본값**이다 — courses[].talent_type과
                # 같은 값이라 직무 역산이 실제로 걸린다. careers는 학과 소개 페이지의
                # 진로라 과목과 연결돼 있지 않다 (이슈 #40)
                "talent_types": dept.get("talent_types", []),
                "careers": dept.get("careers", []),
                "certificates": dept.get("certificates", []),
            }
        )
    return depts


def resolve(dept_id, course_ids, root=None):
    """course_id 목록 → (찾은 과목, 못 찾은 id).

    못 찾은 id를 버리지 않고 돌려준다. 프론트 체크박스와 데이터가 어긋난 신호이므로
    조용히 무시하면 학점만 모자라고 원인은 안 보인다.
    """
    by_id = {c["course_id"]: c for c in load_dept(dept_id, root)["courses"]}
    found, missing = [], []
    for course_id in course_ids:
        course = by_id.get(course_id)
        (found if course else missing).append(course or course_id)
    return found, missing
