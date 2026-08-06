import json
from pathlib import Path

from loop import generate_roadmap
from planner import generate

FIXTURES = Path(__file__).parent / "fixtures"
ITC = json.loads((FIXTURES / "itc.json").read_text(encoding="utf-8"))

JOB = "네트워크 엔지니어"
SPEC = {
    "dept": ITC,
    "target_job": JOB,
    "current_year": 1,
    "current_semester": 1,
    "completed": [],
    "completed_semesters": 0,
}


def ids(roadmap):
    return {c["course_id"] for s in roadmap["semesters"] for c in s["courses"]}


def names_of(dept, predicate):
    return {c["course_id"] for c in dept["courses"] if predicate(c)}


# --- 직무 역산 ---


def test_목표_직무_과목을_1차에_전부_넣는다():
    picked = ids(generate(SPEC))

    assert names_of(ITC, lambda c: c.get("talent_type") == JOB) <= picked


def test_필수과목은_1차부터_전부_넣는다():
    picked = ids(generate(SPEC))

    assert names_of(ITC, lambda c: c["required"]) <= picked


def test_1차는_다른_직무_전용_과목을_넣지_않는다():
    # "직무에서 역산한 경로" — 처음부터 전부 넣으면 그냥 교육과정표다
    picked = ids(generate(SPEC))
    other_job_only = names_of(
        ITC, lambda c: not c["required"] and c.get("talent_type") not in (None, JOB)
    )

    assert not (other_job_only & picked)


def test_재생성하면_모자란_만큼만_더_얹는다():
    first = ids(generate(SPEC, attempt=1))
    second = ids(generate(SPEC, feedback="전공 학점이 모자랍니다", attempt=2))

    assert first < second
    # 통째로 열지 않는다 — 열면 어떤 직무든 같은 로드맵이 된다
    everything = ids(generate(SPEC, attempt=99))
    assert second < everything


def test_목표_직무가_다르면_1차_경로가_다르다():
    """설계서 §1의 차별화. 1차(직무 경로)는 직무마다 달라야 한다."""
    net = ids(generate({**SPEC, "target_job": "네트워크 엔지니어"}, attempt=1))
    ai = ids(generate({**SPEC, "target_job": "AI 개발자"}, attempt=1))

    assert net != ai


def test_직무_관련_과목을_표시하고_앞으로_낸다():
    """교육과정 여유가 적어 최종 과목 집합은 비슷해진다. 그래도 무엇이 직무 때문에
    들어갔는지는 다르므로 화면이 강조할 수 있게 표시한다."""
    net = generate({**SPEC, "target_job": "네트워크 엔지니어"}, attempt=3)
    ai = generate({**SPEC, "target_job": "AI 개발자"}, attempt=3)

    def tagged(roadmap):
        return {c["course_id"] for s in roadmap["semesters"] for c in s["courses"] if c["job_related"]}

    assert tagged(net) != tagged(ai)
    # 학기 안에서 직무 과목이 앞에 온다
    for sem in net["semesters"]:
        flags = [c["job_related"] for c in sem["courses"]]
        assert flags == sorted(flags, reverse=True)


def test_이미_이수한_과목은_다시_넣지_않는다():
    spec = {**SPEC, "completed": [{"course_id": "itc-자료구조"}]}

    assert "itc-자료구조" not in ids(generate(spec))


def test_지나간_학기의_과목은_넣지_않는다():
    spec = {**SPEC, "current_year": 2, "current_semester": 1}

    roadmap = generate(spec)

    assert all(
        (s["year"], s["semester"]) >= (2, 1) for s in roadmap["semesters"]
    )


# --- 교양선택 버킷 ---


def test_없는_과목을_지어내지_않는다():
    """교육과정표에 없는 교양선택·일반선택을 가짜 블록으로 채우지 않는다.
    남은 학점은 validation.remaining_credits로만 알린다."""
    roadmap = generate(SPEC, attempt=3)

    real = {c["course_id"] for c in ITC["courses"]}
    placed = {c["course_id"] for s in roadmap["semesters"] for c in s["courses"]}
    assert placed <= real


# --- 자격증·설명 ---


def test_자격증이_학기에_배치된다():
    roadmap = generate(SPEC)

    placed = [cert for s in roadmap["semesters"] for cert in s["certificates"]]
    assert placed
    assert set(placed) <= set(ITC["certificates"])


def test_학기_설명에_직무_관련_과목_수가_들어간다():
    roadmap = generate(SPEC)

    assert any(JOB in s["notes"] for s in roadmap["semesters"])


# --- 루프와 붙였을 때 ---


def test_루프를_돌면_결국_졸업요건을_충족한다():
    result = generate_roadmap(SPEC, generate)

    assert result["validation"]["passed"] is True


def test_1차만으로는_졸업요건에_모자란다():
    """직무 경로와 졸업요건은 별개다 — 그 간극을 검증기가 메운다."""
    from validator import validate_roadmap

    first = generate(SPEC, attempt=1)
    validation = validate_roadmap(first["semesters"], ITC["years"])

    assert validation["passed"] is False


# --- 검증기 효과 (설계서 §9) ---


def test_재생성_루프가_충족률을_올린다():
    """1차는 직무 경로만 짜서 전공 학점이 모자란다. 검증기가 잡아 채운다.
    이 차이가 기술 점수의 근거이므로 코드로 고정한다."""
    from loop import generate_roadmap

    off = generate_roadmap(SPEC, generate, max_attempts=1)
    on = generate_roadmap(SPEC, generate, max_attempts=3)

    assert off["validation"]["passed"] is False
    assert any(d["rule"] == "major_credits" for d in off["validation"]["details"])
    assert on["validation"]["passed"] is True
