"""학과 소개 페이지 → 자격증·진로·인재양성유형 수집.

교과과정표(PDF)에는 과목만 있다. 로드맵에 "CCNA를 2학년 여름에" 같은 내용이
나오려면 자격증 목록이, 목표 직무를 고르게 하려면 진로 정보가 필요하다.

`faculty/facultyIntro.do?facultyType={코드}`는 전 학과가 같은 구조라 코드만
알면 같은 파서로 훑을 수 있다. 코드는 공개 목록이 없어 탐색으로 찾는다.

부수 수확: `인재양성유형` 표에 직무명과 **직무 설명**이 함께 있다. 교과과정표
비고 열의 라벨(`시스템응용SW개발엔지니어`)이 무슨 일인지를 학교가 직접 적어둔
것이므로, 트랙 B에서 NCS 직무기술서와 맞출 때 그대로 쓴다.
"""

import argparse
import html
import json
import re
import sys
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

BASE = "https://www.mjc.ac.kr/faculty/facultyIntro.do"
UA = {"User-Agent": "Mozilla/5.0 (hackathon-mjc dept-info collector)"}

# 코드 공간. 본과정은 A~E 계열, 조기취업형 계약학과는 F 계열을 쓴다.
CODE_PREFIXES = ("A", "B", "C", "D", "E")
CODE_RANGE = range(1, 13)


def fetch(code: str) -> str | None:
    url = f"{BASE}?facultyType={code}&facultyContent=01"
    try:
        with urlopen(Request(url, headers=UA), timeout=20) as r:
            return r.read().decode("utf-8", errors="ignore")
    except (HTTPError, URLError, TimeoutError):
        return None


def plain_text(raw: str) -> str:
    body = re.sub(r"<(script|style)\b.*?</\1>", " ", raw, flags=re.S | re.I)
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", body)).split())


def dept_name(raw: str) -> str | None:
    """학과명은 h1 중 하나다. 사이트 로고도 h1이라 그것만 걸러낸다."""
    for m in re.finditer(r"<h1[^>]*>(.*?)</h1>", raw, re.S):
        name = " ".join(html.unescape(re.sub(r"<[^>]+>", "", m.group(1))).split())
        if name and "명지전문대학" not in name:
            return name
    return None


def _between(text: str, starts: tuple[str, ...], ends: tuple[str, ...]) -> str:
    """`starts` 중 먼저 나오는 것 뒤부터 `ends` 앞까지를 잘라낸다.

    절 제목 표기가 학과마다 다르다 — 자격증은 `취득 자격증`(28곳)·`취득가능
    자격증`(1곳)·`자격증 취득`(5곳)이 섞여 있고, 진로도 `교육활동 및 진로`(26곳)와
    `취업 및 진로`(3곳)로 갈린다. 하나만 보면 그 학과가 통째로 빈다.
    """
    # 위치가 아니라 **목록 순서**로 고른다. 뒤쪽 표기일수록 느슨해서, 위치로
    # 고르면 본문 문장("…자격증 취득과정 및 전공영어 교육으로…")이 절 제목을
    # 이긴다 — 정보통신공학과가 실제로 그렇게 오염됐다.
    start = next((s for s in starts if s in text), None)
    if start is None:
        return ""
    rest = text[text.find(start) + len(start) :]
    cuts = [rest.find(e) for e in ends if rest.find(e) > 0]
    return rest[: min(cuts)].strip() if cuts else rest[:600].strip()


# 자격증 목록에 섞여 들어오는 안내 문장. "…를 통하여 전자" 같은 조각이 자격증으로 잡힌다.
_NOT_A_CERT = re.compile(r"통하여|다음과|아래|취득할|응시|바랍니다|참고|및 기타")

# `(국가자격증)`·`(민간자격증)` 같은 분류 머리말. 자격증명이 아니다.
_CERT_HEADING = re.compile(r"^\(?(국가|민간|공인)?\s*자격증\)?$")

CERT_STARTS = ("취득 자격증", "취득가능 자격증", "취득 가능 자격증", "자격증 취득")
CERT_ENDS = ("교육활동", "취업 및 진로", "졸업 후 진로", "교수진", "※")
CAREER_STARTS = ("교육활동 및 진로", "취업 및 진로", "졸업 후 진로", "진로 및 취업")
CAREER_ENDS = ("※", "교수진소개", "교과안내", "QUICK")


def parse_certificates(text: str) -> list[str]:
    """자격증 절의 쉼표 목록을 쪼갠다. `(국가자격증)` 같은 머리말은 버린다."""
    seg = _between(text, CERT_STARTS, CERT_ENDS)
    seg = re.sub(r"\((?:국가|민간|공인)\s*자격증\)", ",", seg)
    items = [re.sub(r"\s*등$", "", c).strip(" ·,.") for c in re.split(r"[,·]", seg)]
    return [
        c
        for c in items
        if 1 < len(c) < 40 and not _NOT_A_CERT.search(c) and not _CERT_HEADING.match(c)
    ]


def parse_careers(text: str) -> str:
    return _between(text, CAREER_STARTS, CAREER_ENDS)


# 진로 산문에서 직업명을 끊어내는 꼬리말. `네트워크 관리자`, `웹 프로그래머` 등.
_JOB_TAIL = (
    "엔지니어", "개발자", "프로그래머", "디자이너", "관리자", "전문가", "기술자",
    "기획자", "컨설턴트", "분석가", "상담사", "교사", "지도사", "조종자", "운용자",
    "매니저", "크리에이터", "아티스트", "연구원", "공무원", "사무원", "회계사",
    "중개사", "기사", "산업기사", "치료사", "간호사", "영양사", "제작자",
)
_JOB_RE = re.compile(
    r"[가-힣A-Za-z0-9·/\s]{2,25}?(?:" + "|".join(_JOB_TAIL) + r")"
)


def parse_career_jobs(careers_text: str) -> list[str]:
    """진로 산문에서 직업명만 추린다.

    학과 소개의 진로는 문장이다 — "…S/W 개발분야 (빅데이터, 인공지능, 모바일 앱
    프로그래머, 웹프로그래머), 로봇 제어, 네트워크 관리 및 유지/보수 분야…".
    직업명 꼬리말로 끊어내면 사용자가 고를 수 있는 목록이 된다.

    산문이라 완벽하게는 못 뽑는다. 트랙 B의 축은 `talent_types`(학교가 과목에
    직접 매긴 라벨)이고, 이 목록은 입력 화면의 선택지 용도다.
    """
    jobs = []
    for m in _JOB_RE.finditer(careers_text):
        job = " ".join(m.group().split()).lstrip("및,)(· ").strip()
        # 앞쪽에 딸려온 조사·접속어를 떼어낸다
        job = re.sub(r"^(?:등|또는|그리고|다양한|각종|관련)\s*", "", job)
        if 2 < len(job) < 25 and job not in jobs:
            jobs.append(job)
    return jobs[:12]


def parse_talent_types(raw: str) -> list[dict]:
    """인재양성유형 표에서 (직무명, 직무내용)을 뽑는다.

    평문으로 펴면 유형명과 직무내용의 경계가 사라진다(둘 다 그냥 한국어 문장이다).
    표 구조를 살려 셀 단위로 읽어야 한다. 직무내용은 `：`(전각 콜론)으로 시작한다.
    """
    start = raw.find("인재양성유형표")
    if start < 0:
        return []
    end = raw.find("취득 자격증", start)
    table = raw[start : end if end > 0 else start + 8000]

    cells = [
        " ".join(html.unescape(re.sub(r"<[^>]+>", " ", c)).split())
        for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", table, re.S | re.I)
    ]

    types = []
    for i, cell in enumerate(cells):
        if "：" not in cell and ":" not in cell:
            continue
        # 직무내용 셀이다. 앞쪽에서 가장 가까운 유형명 셀을 찾는다.
        # 유형명은 짧고 콜론이 없다 — 설명 셀을 이름으로 잘못 집는 것을 막는다.
        for prev in reversed(cells[:i]):
            if not prev or len(prev) > 40 or ":" in prev or "：" in prev:
                continue
            if prev not in ("인재양성유형", "직무내용"):
                # 셀은 `{NCS 직무명}：{설명}` 꼴이다. 직무명은 학교가 붙인
                # NCS 매핑이므로 트랙 B에서 쓸 수 있게 따로 남긴다.
                ncs_job, _, desc = cell.partition("：")
                if not desc:
                    ncs_job, _, desc = cell.partition(":")
                types.append(
                    {
                        "name": prev,
                        "ncs_job": ncs_job.strip() if desc else "",
                        "description": (desc or cell).strip()[:400],
                    }
                )
                break
    return types


def collect(code: str) -> dict | None:
    raw = fetch(code)
    if not raw:
        return None
    name = dept_name(raw)
    if not name:
        return None

    text = plain_text(raw)
    return {
        "faculty_type_code": code,
        "dept_name": name,
        "certificates": parse_certificates(text),
        "careers_text": (careers := parse_careers(text)),
        "careers": parse_career_jobs(careers),
        "talent_types": parse_talent_types(raw),
        "source_url": f"{BASE}?facultyType={code}&facultyContent=01",
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="학과 자격증·진로 수집")
    ap.add_argument("--out", default="../data/dept_info.json")
    ap.add_argument("--codes", nargs="*", help="특정 코드만 (미지정 시 전 코드 탐색)")
    args = ap.parse_args()

    codes = args.codes or [f"{p}{n:02d}" for p in CODE_PREFIXES for n in CODE_RANGE]
    found = []
    for code in codes:
        info = collect(code)
        if info:
            found.append(info)
            print(
                f"  {code}  {info['dept_name']:<22} "
                f"자격증 {len(info['certificates']):>2}개 · "
                f"인재양성유형 {len(info['talent_types'])}종",
                file=sys.stderr,
            )
        time.sleep(0.2)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(found, ensure_ascii=False, indent=2), encoding="utf-8")

    with_cert = sum(1 for f in found if f["certificates"])
    with_type = sum(1 for f in found if f["talent_types"])
    print(
        f"\n{out} 저장 — 학과 {len(found)}개 "
        f"(자격증 보유 {with_cert} · 인재양성유형 보유 {with_type})",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
