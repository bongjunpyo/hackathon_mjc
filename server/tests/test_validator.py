from validator import validate_roadmap


def roadmap(n_semesters, major=0, liberal=0, general=0):
    """학점 총량을 지정해 n개 학기에 고르게 분산한다. 1학점 과목으로 채워 계산을 단순하게 유지."""
    buckets = [[] for _ in range(n_semesters)]
    i = 0
    for category, total in (("전공", major), ("교양", liberal), ("일반선택", general)):
        for _ in range(total):
            buckets[i % n_semesters].append(category)
            i += 1
    return [
        {
            "year": k // 2 + 1,
            "semester": k % 2 + 1,
            "courses": [
                {"course_id": f"t-{k}-{j}", "credits": 1, "category": cat}
                for j, cat in enumerate(bucket)
            ],
        }
        for k, bucket in enumerate(buckets)
    ]


def done(major=0, liberal=0, general=0):
    """이미 이수한 과목 목록. 학기 구조 없이 평평한 과목 배열이다."""
    return (
        [{"credits": 1, "category": "전공"}] * major
        + [{"credits": 1, "category": "교양"}] * liberal
        + [{"credits": 1, "category": "일반선택"}] * general
    )


def find(details, rule):
    return next(d for d in details if d["rule"] == rule)


def rules(result):
    return [d["rule"] for d in result["details"]]


# --- 3년제 룰: 총110 / 교양10 / 전공66 / 6학기 ---


def test_3년제_전공학점_미달을_잡는다():
    result = validate_roadmap(roadmap(6, major=60, liberal=10, general=40), years=3)

    assert result["passed"] is False
    assert result["major_credits"] == 60
    detail = find(result["details"], "major_credits")
    assert detail["required"] == 66
    assert detail["actual"] == 60
    assert detail["shortfall"] == 6
    assert rules(result) == ["major_credits"]


def test_총학점은_미달로_잡지_않고_남은_학점으로_알려준다():
    """교육과정표에 교양선택·일반선택이 없다. 우리가 배치할 수 없는 몫을
    미달로 잡으면 어떤 로드맵도 통과하지 못한다 — 실데이터 34개 학과 중 32개가 그랬다."""
    result = validate_roadmap(roadmap(6, major=66, liberal=3, general=24), years=3)

    assert result["total_credits"] == 93
    assert result["remaining_credits"] == 17
    assert not any(d["rule"] == "total_credits" for d in result["details"])
    assert result["passed"] is True


def test_교양필수가_빠지면_잡는다():
    """인성채플·성경과삶은 학과 교육과정표에 실제로 있는 과목이라 판정할 수 있다."""
    result = validate_roadmap(roadmap(6, major=66, liberal=1, general=36), years=3)

    detail = find(result["details"], "liberal_required")
    assert detail["required"] == 3
    assert detail["shortfall"] == 2
    assert rules(result) == ["liberal_required"]


def test_3년제_재학학기_부족을_잡는다():
    # 학점은 전부 충족이지만 4학기에 몰아넣었다
    result = validate_roadmap(roadmap(4, major=66, liberal=10, general=34), years=3)

    detail = find(result["details"], "semesters")
    assert detail["required"] == 6
    assert detail["actual"] == 4
    assert detail["shortfall"] == 2
    assert rules(result) == ["semesters"]


def test_3년제_전부_충족하면_통과한다():
    result = validate_roadmap(roadmap(6, major=66, liberal=10, general=34), years=3)

    assert result["passed"] is True
    assert result["details"] == []
    assert result["total_credits"] == 110


# --- 2년제 룰: 총75 / 교양6 / 전공45 / 4학기 ---


def test_2년제_전공학점_기준은_45다():
    # 전공 60 — 3년제였다면 미달이지만 2년제 기준 45는 넘는다
    result = validate_roadmap(roadmap(4, major=60, liberal=6, general=9), years=2)

    assert result["passed"] is True
    assert result["details"] == []


def test_2년제_기준_미달은_2년제_수치로_보고한다():
    result = validate_roadmap(roadmap(4, major=40, liberal=6, general=29), years=2)

    detail = find(result["details"], "major_credits")
    assert detail["required"] == 45
    assert detail["shortfall"] == 5
    assert rules(result) == ["major_credits"]


# --- 재학 중인 학생: 로드맵은 남은 학기만 온다 ---


def test_이미_이수한_학점과_학기를_합산한다():
    # 2학년 1학기 학생. 1학년 2개 학기에 전공24·교양6을 이수했고,
    # 남은 4개 학기 로드맵은 전공84·교양8. 합치면 122학점 6학기로 충족이다.
    result = validate_roadmap(
        roadmap(4, major=84, liberal=8),
        years=3,
        completed=done(major=24, liberal=6),
        completed_semesters=2,
    )

    assert result["passed"] is True
    assert result["total_credits"] == 122
    assert result["semesters"] == 6


def test_이수분을_합쳐도_모자라면_남은_양만_요구한다():
    # 이수 전공 24 + 계획 전공 30 = 54. 3년제 66에 12 부족
    result = validate_roadmap(
        roadmap(4, major=30, liberal=10, general=76),
        years=3,
        completed=done(major=24),
        completed_semesters=2,
    )

    detail = find(result["details"], "major_credits")
    assert detail["actual"] == 54
    assert detail["shortfall"] == 12


# --- LLM이 만든 로드맵은 스키마 보장이 없다 ---
#
# 검증기는 LLM 출력을 잡는 장치인데, 정작 LLM이 필드를 빠뜨렸다고 검증기가 죽으면
# 재생성 루프가 스스로 고칠 기회조차 없이 데모가 멈춘다.


def bad_roadmap(*courses):
    return [{"year": 1, "semester": 1, "courses": list(courses)}]


def test_필드가_빠진_과목에_죽지_않는다():
    result = validate_roadmap(bad_roadmap({"course_id": "x", "name": "과목"}), years=3)

    assert result["passed"] is False
    assert find(result["details"], "malformed_course")


def test_credits가_문자열이면_형식_오류로_잡는다():
    result = validate_roadmap(bad_roadmap({"credits": "3", "category": "전공"}), years=3)

    detail = find(result["details"], "malformed_course")
    assert "credits" in detail["fix"]


def test_모르는_category는_형식_오류로_잡는다():
    result = validate_roadmap(bad_roadmap({"credits": 3, "category": "전공선택"}), years=3)

    assert find(result["details"], "malformed_course")


def test_형식_오류는_재생성_프롬프트에_개수가_들어간다():
    result = validate_roadmap(
        bad_roadmap({"credits": 3}, {"category": "전공"}, {"credits": 3, "category": "전공"}),
        years=3,
    )

    detail = find(result["details"], "malformed_course")
    assert detail["actual"] == 2  # 정상 1개, 깨진 것 2개
    assert "2" in detail["fix"]


def test_깨진_과목이_섞여도_정상_과목은_집계한다():
    # 전부 버리면 재생성이 뭘 고쳐야 할지 모른다
    courses = [{"credits": 3, "category": "전공"}, {"name": "깨진 과목"}]

    result = validate_roadmap(bad_roadmap(*courses), years=3)

    assert result["major_credits"] == 3


def test_모르는_학제는_죽지_않고_3년제로_본다():
    # 경계(catalog)가 먼저 막지만, 검증기 자체도 KeyError로 죽지 않아야 한다
    result = validate_roadmap(roadmap(6, major=66, liberal=10, general=34), years=4)

    assert result["passed"] is True


# --- 동결 계약 (docs/DESIGN.md §5) ---


def test_동결_스펙의_validation_필드를_그대로_낸다():
    result = validate_roadmap(roadmap(6, major=66, liberal=3, general=34), years=3)

    assert set(result) == {
        "passed",
        "total_credits",
        "major_credits",
        "liberal_credits",
        "semesters",
        "remaining_credits",
        "details",
    }


def test_재학_학기_수를_요약에도_낸다():
    # details뿐 아니라 최상위에도 있어야 배지 UI가 4종을 모두 그린다
    result = validate_roadmap(roadmap(4, major=66, liberal=10, general=34), years=3)

    assert result["semesters"] == 4


# --- details는 LLM 재생성 프롬프트로 쓰인다 ---


def test_미달_항목마다_고칠_방법이_들어있다():
    result = validate_roadmap(roadmap(6, major=60, liberal=1, general=30), years=3)

    assert rules(result) == ["liberal_required", "major_credits"]
    for detail in result["details"]:
        assert detail["fix"]
        assert str(detail["shortfall"]) in detail["fix"]
        assert detail["label"]
