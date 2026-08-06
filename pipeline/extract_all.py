"""전 학과 일괄 추출 + 품질 지표 산출.

학과별 PDF를 같은 파이프라인에 통과시키고, 학과마다 어느 경로로 처리됐는지
(코드 파싱 / LLM 폴백) 지표로 남긴다. 이 지표가 곧 산출물이다 — "전 학과를
파이프라인 하나로 처리했다"는 주장의 근거.

수업연한(2/3년제)과 자격증·진로는 표와 학과 소개 페이지에서 각각 가져와 합친다.
"""

import argparse
import json
import re
import sys
from pathlib import Path

from extract import GRADUATION_RULES, extract_tables, normalize_liberal, structure
from schema import DeptCurriculum

# 학과명 → dept_id. 로마자 약칭은 학과 서브도메인을 따른다.
DEPT_IDS = {
    "정보통신공학과": "itc",
    "컴퓨터공학과": "mjcs",
    "컴퓨터보안공학과": "cse",
    "전자공학과": "cee",
    "기계공학과": "mee",
    "산업경영공학과": "idm",
    "전기공학과": "electrical",
    "토목공학과": "civil",
    "지적공간정보학과": "jijuk",
    "드론정보공학과": "droneinfo",
    "AI게임소프트웨어학과": "swcontent",
    "경영학과": "ceo",
    "세무회계과": "tax",
    "부동산경영과": "rem",
    "사회복지과": "swd",
    "공공행정서비스과": "publiccs",
    "항공서비스과": "skysvc",
    "중국어비즈니스과": "china",
    "일본어과": "mjcjp",
    "문예창작과": "mjccrw",
    "유아교육학과": "ece",
    "청소년교육상담과": "yde",
    "산업디자인학과": "iid",
    "커뮤니케이션디자인과": "mjcd",
    "사회체육과": "sls",
    "보건의료정보과": "medinfo",
    "실용음악과": "sileum",
    "연극영상학과": "acting",
}

# 자유전공학과는 전공 미정 학과라 교과과정표에 과목이 2개뿐이다. 로드맵을 짤
# 대상이 아니므로 제외한다 (팀 결정 2026-08-06).
SKIP_DEPTS = {"자유전공학과"}


def slug(name: str) -> str:
    """매핑에 없는 학과는 파일명을 로마자화하지 않고 그대로 쓴다."""
    return DEPT_IDS.get(name) or re.sub(r"[^\w가-힣]", "", name)


def years_from_table(table: str) -> int:
    """표의 `수업연한` 열에서 2/3년제를 읽는다. 못 읽으면 2년제로 본다."""
    m = re.search(r"([23])년제", table)
    return int(m.group(1)) if m else 2


def main() -> None:
    ap = argparse.ArgumentParser(description="전 학과 일괄 추출")
    ap.add_argument("--curricula", default="../data/raw/curricula")
    ap.add_argument("--dept-info", default="../data/dept_info.json")
    ap.add_argument("--out", default="../data/depts")
    ap.add_argument("--tier1", nargs="*", default=["정보통신공학과"])
    args = ap.parse_args()

    info_by_name = {}
    info_path = Path(args.dept_info)
    if info_path.exists():
        for item in json.loads(info_path.read_text(encoding="utf-8")):
            info_by_name[re.sub(r"[^\w가-힣]", "", item["dept_name"])] = item

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    report = []

    for pdf in sorted(Path(args.curricula).glob("*.pdf")):
        name = pdf.stem
        if name in SKIP_DEPTS:
            report.append({"dept_name": name, "status": "skipped", "reason": "전공 미정 학과"})
            print(f"  – {name}: 제외 (전공 미정 학과)", file=sys.stderr)
            continue

        dept_id = slug(name)
        table = extract_tables(pdf)
        years = years_from_table(table)

        try:
            dept, route = structure(
                table, dept_id, name, years, 1 if name in args.tier1 else 2
            )
        except Exception as e:  # 폴백까지 실패한 학과는 지표에 남기고 넘어간다
            report.append({"dept_name": name, "status": "failed", "reason": str(e)[:120]})
            print(f"  ✗ {name}: {str(e)[:80]}", file=sys.stderr)
            continue

        dept = normalize_liberal(dept)
        dept.source_url = f"https://www.mjc.ac.kr/bbs/data/list.do?menu_idx=2207"
        dept.extraction_confidence = (
            1.0 if route == "code" else round(1.0 - int(route.split(":")[1]) * 0.15, 2)
        )

        info = info_by_name.get(re.sub(r"[^\w가-힣]", "", name))
        if info:
            dept.certificates = info["certificates"]
            dept.careers = [t["name"] for t in info["talent_types"]]
            dept.faculty_type_code = info["faculty_type_code"]

        # 진로 선택지는 교과과정표 비고 열의 직무 라벨이 1순위다 — 과목과 직접
        # 연결돼 있어 트랙 B 매칭에 그대로 쓸 수 있다.
        labels = sorted({c.talent_type for c in dept.courses if c.talent_type})
        if labels:
            dept.careers = labels

        (out_dir / f"{dept_id}.json").write_text(
            dept.model_dump_json(indent=2), encoding="utf-8"
        )

        major = sum(c.credits for c in dept.courses if c.category == "전공")
        report.append(
            {
                "dept_name": name,
                "dept_id": dept_id,
                "status": "ok",
                "route": route,
                "years": years,
                "courses": len(dept.courses),
                "major_credits": major,
                "major_required": GRADUATION_RULES[years]["major"],
                # 교육과정표만으로는 전공 요건을 채울 수 없는 학과. 로드맵 에이전트가
                # 이 학과에서 검증을 통과시킬 수 없다는 뜻이라 미리 드러내 둔다.
                "major_short": max(0, GRADUATION_RULES[years]["major"] - major),
                "job_labels": len(labels),
                "certificates": len(dept.certificates),
            }
        )
        print(
            f"  ✓ {name:<24} {years}년제 {len(dept.courses):>2}과목 "
            f"전공{major:>3}학점 직무{len(labels)}종 자격증{len(dept.certificates):>2}개 [{route}]",
            file=sys.stderr,
        )

    (out_dir / "_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    ok = [r for r in report if r["status"] == "ok"]
    by_code = sum(1 for r in ok if r["route"] == "code")
    print(
        f"\n학과 {len(ok)}/{len(report)} 처리 — 코드 파싱 {by_code} · LLM 폴백 {len(ok) - by_code}",
        file=sys.stderr,
    )
    print(f"과목 합계 {sum(r['courses'] for r in ok)}개", file=sys.stderr)


if __name__ == "__main__":
    main()
