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


def test_3년제_총학점_미달을_잡는다():
    result = validate_roadmap(roadmap(6, major=66, liberal=10, general=24), years=3)

    assert result["total_credits"] == 100
    detail = find(result["details"], "total_credits")
    assert detail["required"] == 110
    assert detail["shortfall"] == 10
    assert rules(result) == ["total_credits"]


def test_3년제_교양학점_미달을_잡는다():
    result = validate_roadmap(roadmap(6, major=66, liberal=8, general=36), years=3)

    assert result["liberal_credits"] == 8
    detail = find(result["details"], "liberal_credits")
    assert detail["required"] == 10
    assert detail["shortfall"] == 2
    assert rules(result) == ["liberal_credits"]


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


# --- 동결 계약 (docs/DESIGN.md §5) ---


def test_동결_스펙의_validation_필드를_그대로_낸다():
    result = validate_roadmap(roadmap(6, major=66, liberal=10, general=34), years=3)

    assert set(result) == {
        "passed",
        "total_credits",
        "major_credits",
        "liberal_credits",
        "semesters",
        "details",
    }


def test_재학_학기_수를_요약에도_낸다():
    # details뿐 아니라 최상위에도 있어야 배지 UI가 4종을 모두 그린다
    result = validate_roadmap(roadmap(4, major=66, liberal=10, general=34), years=3)

    assert result["semesters"] == 4


# --- details는 LLM 재생성 프롬프트로 쓰인다 ---


def test_미달_항목마다_고칠_방법이_들어있다():
    result = validate_roadmap(roadmap(6, major=60, liberal=8, general=30), years=3)

    assert rules(result) == ["total_credits", "liberal_credits", "major_credits"]
    for detail in result["details"]:
        assert detail["fix"]
        assert str(detail["shortfall"]) in detail["fix"]
        assert detail["label"]
