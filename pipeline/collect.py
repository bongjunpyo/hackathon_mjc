"""명지전문대 교과과정표 게시판 → PDF 일괄 수집.

게시판(menu_idx=2207)은 전 학과 교과과정표를 한곳에 모아둔다. 학과별
서브도메인을 각각 긁는 대신 여기 하나만 훑으면 전 학과가 나온다.

    목록 페이지 순회 → 게시물별 첨부 idx 조회 → 파일 다운로드
"""

import argparse
import html
import json
import re
import sys
import time
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

BASE = "https://www.mjc.ac.kr"
BBS = "BM0000001768"
MENU = "2207"
UA = {"User-Agent": "Mozilla/5.0 (hackathon-mjc curriculum collector)"}

# 조기취업형 계약학과·전공심화는 본과정과 졸업요건 체계가 달라 v1 범위 밖이다.
SKIP = ("조기취업", "전공심화")


def get(url: str) -> str:
    with urlopen(Request(url, headers=UA), timeout=30) as r:
        return r.read().decode("utf-8", errors="ignore")


def list_posts(pages: int) -> list[dict]:
    """게시판 목록에서 (data_idx, 제목)을 모은다."""
    posts = []
    for page in range(1, pages + 1):
        url = f"{BASE}/bbs/data/list.do?" + urlencode(
            {"menu_idx": MENU, "bbs_mst_idx": BBS, "pageIndex": page}
        )
        for idx, chunk in re.findall(r"(BD\d{10})(.{0,400}?)</a>", get(url), re.S):
            title = " ".join(html.unescape(re.sub(r"<[^>]+>", " ", chunk)).split())
            title = title.replace("','');\">", "").strip()
            if title:
                posts.append({"data_idx": idx, "title": title, "page": page})
        time.sleep(0.3)
    return posts


def find_attachment(data_idx: str) -> tuple[str, str] | None:
    """게시물 상세에서 (attach_idx, 파일명)을 찾는다. 첨부가 없으면 None."""
    url = f"{BASE}/bbs/data/view.do?" + urlencode(
        {"menu_idx": MENU, "bbs_mst_idx": BBS, "data_idx": data_idx}
    )
    m = re.search(
        r"fn_egov_downFile\('[^']*','[^']*','(BF\d{10})'\)\s*\">([^<]+)", get(url)
    )
    return (m.group(1), html.unescape(m.group(2)).strip()) if m else None


def download(data_idx: str, attach_idx: str, dest: Path) -> int:
    url = f"{BASE}/bbs/dataFile/fileDown.do?" + urlencode(
        {"bbs_mst_idx": BBS, "data_idx": data_idx, "attach_idx": attach_idx}
    )
    with urlopen(Request(url, headers=UA), timeout=60) as r:
        body = r.read()
    dest.write_bytes(body)
    return len(body)


def dept_slug(title: str) -> str:
    """'2026학년도 교과과정표_정보통신공학과' → '정보통신공학과'"""
    name = title.split("_")[-1] if "_" in title else title
    return re.sub(r"[^\w가·]", "", name.replace(" ", ""))


def main() -> None:
    ap = argparse.ArgumentParser(description="교과과정표 PDF 일괄 수집")
    ap.add_argument("--pages", type=int, default=11)
    ap.add_argument("--year", default="2026", help="수집할 학년도")
    ap.add_argument("--out", default="../data/raw/curricula")
    args = ap.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    posts = list_posts(args.pages)
    targets = [
        p
        for p in posts
        if p["title"].startswith(args.year) and not any(s in p["title"] for s in SKIP)
    ]
    print(f"게시물 {len(posts)}건 중 {args.year} 본과정 {len(targets)}건", file=sys.stderr)

    manifest = []
    for i, post in enumerate(targets, 1):
        slug = dept_slug(post["title"])
        found = find_attachment(post["data_idx"])
        if not found:
            print(f"  [{i}/{len(targets)}] {slug}: 첨부 없음", file=sys.stderr)
            manifest.append({**post, "dept": slug, "status": "no_attachment"})
            continue

        attach_idx, filename = found
        ext = Path(filename).suffix.lower() or ".bin"
        dest = out / f"{slug}{ext}"
        size = download(post["data_idx"], attach_idx, dest)
        print(f"  [{i}/{len(targets)}] {slug}{ext} — {size:,} bytes", file=sys.stderr)
        manifest.append(
            {**post, "dept": slug, "file": dest.name, "bytes": size, "status": "ok"}
        )
        time.sleep(0.3)

    (out / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    ok = sum(1 for m in manifest if m["status"] == "ok")
    print(f"\n완료: {ok}/{len(targets)}건 다운로드", file=sys.stderr)


if __name__ == "__main__":
    main()
