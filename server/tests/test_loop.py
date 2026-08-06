import json
from pathlib import Path

from loop import build_feedback, generate_roadmap

FIXTURES = Path(__file__).parent / "fixtures"
ITC = json.loads((FIXTURES / "itc.json").read_text(encoding="utf-8"))


def sems(n, major=0, liberal=0, general=0):
    """학점 총량을 n개 학기에 분산. 1학점 과목으로 채워 계산을 단순하게 유지."""
    buckets = [[] for _ in range(n)]
    i = 0
    for category, total in (("전공", major), ("교양", liberal), ("일반선택", general)):
        for _ in range(total):
            buckets[i % n].append(category)
            i += 1
    return [
        {
            "year": k // 2 + 1,
            "semester": k % 2 + 1,
            "courses": [{"course_id": f"x{k}-{j}", "credits": 1, "category": c} for j, c in enumerate(b)],
            "certificates": [],
            "notes": "",
        }
        for k, b in enumerate(buckets)
    ]


PASSING = sems(6, major=66, liberal=10, general=34)
FAILING = sems(6, major=60, liberal=10, general=34)

SPEC = {"dept": ITC, "target_job": "네트워크 엔지니어", "completed": [], "completed_semesters": 0}


class Generator:
    """호출 순서대로 미리 정해둔 로드맵을 낸다. 받은 feedback을 기록한다."""

    def __init__(self, *roadmaps):
        self.roadmaps = list(roadmaps)
        self.feedbacks = []

    def __call__(self, spec, feedback=None):
        self.feedbacks.append(feedback)
        i = min(len(self.feedbacks) - 1, len(self.roadmaps) - 1)
        return {"semesters": self.roadmaps[i]}

    @property
    def calls(self):
        return len(self.feedbacks)


def test_첫_생성이_통과하면_한_번만_호출한다():
    gen = Generator(PASSING)

    result = generate_roadmap(SPEC, gen)

    assert result["validation"]["passed"] is True
    assert result["attempts"] == 1
    assert gen.calls == 1


def test_미달이면_재생성한다():
    gen = Generator(FAILING, PASSING)

    result = generate_roadmap(SPEC, gen)

    assert result["validation"]["passed"] is True
    assert result["attempts"] == 2
    assert gen.calls == 2


def test_상한을_넘으면_예외가_아니라_부분_로드맵을_낸다():
    # 화면이 "여기까지 충족, 이것이 부족"을 그려야 한다. 예외를 던지면 못 그린다
    gen = Generator(FAILING)

    result = generate_roadmap(SPEC, gen, max_attempts=3)

    assert result["validation"]["passed"] is False
    assert result["attempts"] == 3
    assert result["semesters"] == FAILING
    assert result["validation"]["details"]


def test_상한_이상_호출하지_않는다():
    gen = Generator(FAILING)

    generate_roadmap(SPEC, gen, max_attempts=3)

    assert gen.calls == 3


def test_첫_호출에는_피드백이_없다():
    gen = Generator(PASSING)

    generate_roadmap(SPEC, gen)

    assert gen.feedbacks == [None]


def test_재생성에는_고칠_방법을_실어_보낸다():
    gen = Generator(FAILING, PASSING)

    generate_roadmap(SPEC, gen)

    feedback = gen.feedbacks[1]
    assert "전공 학점" in feedback
    assert "전공 과목으로 6학점을 더 채우세요" in feedback


def test_이수분을_검증기에_넘긴다():
    # 2학년 학생: 로드맵은 남은 4학기만. 합산 안 하면 통과할 수 없다
    spec = {
        **SPEC,
        "completed": [{"credits": 1, "category": "전공"}] * 24
        + [{"credits": 1, "category": "교양"}] * 6,
        "completed_semesters": 2,
    }
    gen = Generator(sems(4, major=84, liberal=8))

    result = generate_roadmap(spec, gen)

    assert result["validation"]["passed"] is True
    assert result["attempts"] == 1


# --- 피드백 문자열 ---


def test_피드백은_미달_항목마다_한_줄이다():
    details = [
        {"rule": "major_credits", "label": "전공 학점", "required": 66, "actual": 60,
         "shortfall": 6, "fix": "전공 과목으로 6학점을 더 채우세요"},
        {"rule": "liberal_credits", "label": "교양 학점", "required": 10, "actual": 8,
         "shortfall": 2, "fix": "교양 과목으로 2학점을 더 채우세요"},
    ]

    feedback = build_feedback(details)

    assert feedback.count("\n- ") == 2
    assert "60/66" in feedback
    assert "8/10" in feedback
