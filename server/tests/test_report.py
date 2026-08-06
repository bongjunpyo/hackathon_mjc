from report import build_report, split_label


def course(cid, credits=3, category="전공", talent_type=None):
    return {
        "course_id": cid,
        "name": cid,
        "year": 1,
        "semester": 1,
        "credits": credits,
        "category": category,
        "required": False,
        "talent_type": talent_type,
    }


def dept(courses, careers=None, talent_types=None, **extra):
    d = {
        "dept_id": "t",
        "dept_name": "테스트학과",
        "years": 3,
        "tier": 1,
        "courses": courses,
        "careers": careers or [],
        "extraction_confidence": 0.9,
    }
    if talent_types is not None:
        d["talent_types"] = talent_types
    return {**d, **extra}


# --- 라벨 쪼개기: 한 칸에 여러 직무가 들어 있다 ---


def test_콤마와_슬래시로_묶인_라벨을_쪼갠다():
    assert split_label("컴퓨터응용시스템전문가, 통신및정보보호시스템전문가", []) == [
        "컴퓨터응용시스템전문가",
        "통신및정보보호시스템전문가",
    ]
    assert split_label("브랜드디자이너/그래픽디자이너", []) == ["브랜드디자이너", "그래픽디자이너"]


def test_가운뎃점은_다른_라벨로도_존재할_때만_쪼갠다():
    """`시스템 관리·운용 엔지니어`의 ·는 이름의 일부고,
    `부동산중개사·건물관리사`의 ·는 구분자다. 같은 학과의 다른 라벨을 보고 판단한다."""
    others = ["부동산중개사", "건물관리사", "부동산공급기능인"]

    assert split_label("부동산중개사·건물관리사", others) == ["부동산중개사", "건물관리사"]
    assert split_label("시스템 관리·운용 엔지니어", others) == ["시스템 관리·운용 엔지니어"]


# --- 커버리지 ---


def test_직무별_전공학점_비중을_낸다():
    courses = [
        course("a", talent_type="네트워크"),
        course("b", talent_type="네트워크"),
        course("c", talent_type="AI"),
        course("d", category="교양"),
    ]
    report = build_report(dept(courses, careers=["네트워크", "AI"]))

    net = next(j for j in report["jobs"] if j["job"] == "네트워크")
    assert net["coverage_pct"] == 66.7  # 전공 9학점 중 6
    assert [c["course_id"] for c in net["covered_courses"]] == ["a", "b"]


def test_대응_라벨이_없는_진로는_결손으로_잡는다():
    """학과가 진로로 내세우는데 교육과정 라벨에 대응이 없다 — 리포트의 핵심 발견."""
    courses = [course("a", talent_type="시스템 관리·운용 엔지니어")]
    report = build_report(
        dept(
            courses,
            careers=["시스템 엔지니어", "빅데이터 전문가"],
            talent_types=["시스템 관리·운용 엔지니어"],
        )
    )

    big = next(j for j in report["jobs"] if j["job"] == "빅데이터 전문가")
    assert big["coverage_pct"] == 0
    assert big["covered_courses"] == []
    assert big["gaps"]


def test_토큰이_겹치면_진로와_라벨을_잇는다():
    courses = [course("a", talent_type="시스템 관리·운용 엔지니어")]
    report = build_report(
        dept(courses, careers=["시스템 엔지니어"], talent_types=["시스템 관리·운용 엔지니어"])
    )

    job = report["jobs"][0]
    assert job["matched_labels"] == ["시스템 관리·운용 엔지니어"]
    assert job["gaps"] == []


# --- 라벨 품질 (label_mismatches) ---


def test_직무가_아닌_라벨을_잡는다():
    courses = [course("a", talent_type="공통"), course("b", talent_type="네트워크")]

    report = build_report(dept(courses, careers=["네트워크"]))

    kinds = {m["kind"] for m in report["label_mismatches"]}
    assert "not_a_job" in kinds


def test_오타로_갈린_라벨_쌍을_잡는다():
    """'통신및정보보호…' vs '통신및정보호…' — 실데이터(컴퓨터보안공학과)에 있는 사례."""
    courses = [
        course("a", talent_type="통신및정보보호시스템전문가"),
        course("b", talent_type="통신및정보호시스템전문가"),
    ]

    report = build_report(dept(courses))

    near = [m for m in report["label_mismatches"] if m["kind"] == "near_duplicate"]
    assert near
    assert set(near[0]["labels"]) == {"통신및정보보호시스템전문가", "통신및정보호시스템전문가"}


def test_짧고_비슷한_이름은_오타로_보지_않는다():
    """'공간디자이너'와 '제품디자이너'는 진짜 다른 직무다. 글자 수만 보면 오검출한다."""
    courses = [
        course("a", talent_type="공간디자이너"),
        course("b", talent_type="제품디자이너"),
        course("c", talent_type="청소년상담사"),
        course("d", talent_type="청소년지도사"),
    ]

    report = build_report(dept(courses))

    assert not [m for m in report["label_mismatches"] if m["kind"] == "near_duplicate"]


def test_순서만_다른_묶음_라벨을_잡는다():
    """'브랜드/그래픽'과 '그래픽/ 브랜드' — 실데이터(커뮤니케이션디자인과) 사례."""
    courses = [
        course("a", talent_type="브랜드디자이너/그래픽디자이너"),
        course("b", talent_type="그래픽디자이너/ 브랜드디자이너"),
    ]

    report = build_report(dept(courses))

    assert [m for m in report["label_mismatches"] if m["kind"] == "same_set"]


def test_여러_직무가_한_칸에_묶인_것을_잡는다():
    courses = [course("a", talent_type="영유아교사, 유아체육지도")]

    report = build_report(dept(courses))

    joined = [m for m in report["label_mismatches"] if m["kind"] == "joined"]
    assert joined
    assert joined[0]["parts"] == ["영유아교사", "유아체육지도"]


# --- 정직한 품질 공개 ---


def test_리포트에_추출_신뢰도와_계층을_싣는다():
    """Tier 2는 파이프라인 자동 통과다. 신뢰도가 안 보이면 '정직한 공개'가 성립하지 않는다."""
    report = build_report(dept([course("a")], tier=2, extraction_confidence=0.6))

    assert report["tier"] == 2
    assert report["extraction_confidence"] == 0.6


def test_라벨이_하나도_없으면_빈_리포트를_낸다():
    report = build_report(dept([course("a")], careers=[]))

    assert report["jobs"] == []
    assert report["label_mismatches"] == []


def test_파이프라인_자격증_3분류를_응답에_합친다(tmp_path):
    """계산하지 않고 읽는다 — 화면과 파이프라인 지표가 갈리면 안 된다."""
    import json

    import report

    (tmp_path / "t.json").write_text(
        json.dumps(
            {
                "certificates": {
                    "total": 6,
                    "supported": 0,
                    "unsupported": ["컴퓨터활용능력"],
                    "unevaluated": ["공인행정관리사"],
                },
                "ncs_ratio": 83.3,
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    got = report._pipeline_metrics("t", root=tmp_path)

    assert got["certificates"]["unsupported"] == ["컴퓨터활용능력"]
    # 판정불가는 결손이 아니다 — 따로 온다
    assert got["certificates"]["unevaluated"] == ["공인행정관리사"]
    assert got["ncs_ratio"] == 83.3


def test_파이프라인_파일이_없어도_리포트_본체는_나간다(tmp_path):
    """자격증 절이 리포트 전체를 죽이면 안 된다."""
    import report

    got = report._pipeline_metrics("없는학과", root=tmp_path)

    assert got == {"certificates": None, "ncs_ratio": None}
