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


def _between(text: str, start: str, ends: tuple[str, ...]) -> str:
    """`start` 뒤부터 `ends` 중 가장 먼저 나오는 것 앞까지를 잘라낸다."""
    i = text.find(start)
    if i < 0:
        return ""
    rest = text[i + len(start) :]
    cuts = [rest.find(e) for e in ends if rest.find(e) > 0]
    return rest[: min(cuts)].strip() if cuts else rest[:600].strip()


# 자격증 목록에 섞여 들어오는 안내 문장. "…를 통하여 전자" 같은 조각이 자격증으로 잡힌다.
_NOT_A_CERT = re.compile(r"통하여|다음과|아래|취득할|응시|가능|바랍니다|참고|등의|및 기타")


def parse_certificates(text: str) -> list[str]:
    """'취득 자격증' 절의 쉼표 목록을 쪼갠다."""
    seg = _between(text, "취득 자격증", ("교육활동", "교수진", "※"))
    items = [re.sub(r"\s*등$", "", c).strip(" ·,") for c in seg.split(",")]
    return [c for c in items if 1 < len(c) < 40 and not _NOT_A_CERT.search(c)]


def parse_careers(text: str) -> str:
    return _between(text, "교육활동 및 진로", ("※", "교수진소개", "교과안내", "QUICK"))


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
        "careers_text": parse_careers(text),
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
