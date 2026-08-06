from jobmap import choices, match_labels

LABELS = ["시스템관리·운용엔지니어", "시스템응용SW개발엔지니어"]


def test_학과_문서마다_이름이_달라도_잇는다():
    """학과 소개 페이지의 진로와 교육과정표의 인재양성유형은 이름이 다르다.
    완전 일치만 보면 모든 진로가 결손으로 잡힌다."""
    assert match_labels("시스템 엔지니어", LABELS) == ["시스템관리·운용엔지니어"]


def test_인재양성유형을_그대로_주면_그것과_잇는다():
    assert match_labels("시스템관리·운용엔지니어", LABELS) == ["시스템관리·운용엔지니어"]


def test_대응_라벨이_없는_진로는_빈_목록():
    """'모바일 앱 프로그래머'는 교육과정 라벨에 대응이 없다 — 트랙 B의 결손 소재다."""
    assert match_labels("모바일 앱 프로그래머", LABELS) == []


def test_공백과_구두점_차이를_흡수한다():
    assert match_labels("시스템 관리·운용 엔지니어", LABELS) == ["시스템관리·운용엔지니어"]


def test_고를_수_있는_직무는_인재양성유형이_먼저다():
    """역산의 축이 talent_type이라 그쪽이 맞으면 과목이 확실히 붙는다."""
    dept = {"talent_types": LABELS, "careers": ["시스템 엔지니어", "웹프로그래머"]}

    assert choices(dept) == LABELS + ["시스템 엔지니어", "웹프로그래머"]


def test_중복은_한_번만():
    dept = {"talent_types": ["A"], "careers": ["A", "B"]}

    assert choices(dept) == ["A", "B"]
