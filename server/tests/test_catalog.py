import json
from pathlib import Path

import pytest

from catalog import CatalogError, list_depts, load_dept, resolve

FIXTURES = Path(__file__).parent / "fixtures"


def write_dept(tmp_path, **overrides):
    """픽스처를 복사해 일부 필드만 망가뜨린 학과 파일을 만든다."""
    data = json.loads((FIXTURES / "itc.json").read_text(encoding="utf-8"))
    data.update(overrides)
    (tmp_path / f"{data['dept_id']}.json").write_text(
        json.dumps(data, ensure_ascii=False), encoding="utf-8"
    )
    return tmp_path


def test_학과를_읽어온다():
    dept = load_dept("itc", root=FIXTURES)

    assert dept["dept_name"] == "정보통신공학과"
    assert dept["years"] == 3
    assert dept["liberal_elective_credits"] == 7
    assert len(dept["courses"]) == 39


def test_없는_학과는_CatalogError():
    with pytest.raises(CatalogError):
        load_dept("없는학과", root=FIXTURES)


# --- 경계 검증: 깨진 데이터는 로드 시점에 죽인다 ---


def test_course_id가_중복이면_거부한다(tmp_path):
    data = json.loads((FIXTURES / "itc.json").read_text(encoding="utf-8"))
    data["courses"][1]["course_id"] = data["courses"][0]["course_id"]
    root = write_dept(tmp_path, courses=data["courses"])

    with pytest.raises(CatalogError) as e:
        load_dept("itc", root=root)

    assert data["courses"][0]["course_id"] in str(e.value)


def test_course_id가_비어있으면_거부한다(tmp_path):
    data = json.loads((FIXTURES / "itc.json").read_text(encoding="utf-8"))
    data["courses"][3]["course_id"] = ""
    root = write_dept(tmp_path, courses=data["courses"])

    with pytest.raises(CatalogError):
        load_dept("itc", root=root)


def test_모르는_category는_거부한다(tmp_path):
    # 검증기가 "전공"/"교양"으로만 집계하므로 오타 하나가 학점 미달로 이어진다
    data = json.loads((FIXTURES / "itc.json").read_text(encoding="utf-8"))
    data["courses"][2]["category"] = "전공선택"
    root = write_dept(tmp_path, courses=data["courses"])

    with pytest.raises(CatalogError) as e:
        load_dept("itc", root=root)

    assert "전공선택" in str(e.value)


def test_years가_2나_3이_아니면_거부한다(tmp_path):
    # 검증기 REQUIREMENTS의 키다. 4가 오면 KeyError로 늦게 터진다
    root = write_dept(tmp_path, years=4)

    with pytest.raises(CatalogError):
        load_dept("itc", root=root)


# --- resolve: 이수 과목 id → 학점·이수구분 ---


def test_이수_과목을_학점과_이수구분으로_바꾼다():
    found, missing = resolve("itc", ["itc-프로그래밍언어실습1", "itc-인성채플"], root=FIXTURES)

    assert missing == []
    assert [c["credits"] for c in found] == [3, 1]
    assert [c["category"] for c in found] == ["전공", "교양"]


def test_없는_course_id는_조용히_버리지_않는다():
    # 프론트 체크박스와 데이터가 어긋난 신호다. 버리면 학점만 조용히 모자란다
    found, missing = resolve("itc", ["itc-프로그래밍언어실습1", "itc-없는과목"], root=FIXTURES)

    assert len(found) == 1
    assert missing == ["itc-없는과목"]


def test_학과_목록은_GET_depts_형태로_낸다():
    depts = list_depts(root=FIXTURES)

    assert {"dept_id", "dept_name", "years", "tier"} <= set(depts[0])


def test_학과_목록에_직무와_자격증이_들어간다():
    """프론트가 목표 직무 드롭다운을 채울 데이터. 없으면 하드코딩할 수밖에 없고,
    그러면 '전 학과 대응'이 성립하지 않는다."""
    itc = next(d for d in list_depts(root=FIXTURES) if d["dept_id"] == "itc")

    assert "네트워크 엔지니어" in itc["careers"]
    assert itc["certificates"]
