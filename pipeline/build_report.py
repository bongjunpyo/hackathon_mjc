"""트랙 B — 교육과정 진단 리포트 산출.

`GET /report/{dept_id}` 응답의 재료를 미리 계산해 둔다. LLM 없이 학교 자체
데이터 간 정합성만으로 성립하는 진단이다.

무엇을 진단하는가:

  커버리지   직무마다 몇 과목·몇 학점이 배정됐나. 한쪽에 쏠렸으면 그 학과에서
             다른 직무를 목표로 삼은 학생은 들을 과목이 없다는 뜻이다.
  준비 시점   직무 과목이 3학년에만 몰려 있으면 자격증·현장실습을 앞당길 수 없다.
  자격증 결손 학과가 내건 자격증에 대응하는 과목이 있는가. `CCNA`를 내걸고
             네트워크 과목이 없으면 그 자격증은 학생 개인 몫이라는 뜻이다.

자격증↔과목 매칭은 키워드 규칙이다. 의미 매칭이 아니라 근거가 눈에 보이는 게
중요해서 그렇게 뒀다 — 리포트에 매칭된 과목명이 그대로 나온다.
"""

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

# 자격증 → 과목명에서 찾을 키워드. 학과가 내건 자격증이 교육과정에 반영됐는지
# 보려는 것이라 자격증명 자체보다 그 자격증이 다루는 주제어를 쓴다.
CERT_KEYWORDS = {
    "정보처리": ("프로그래밍", "자료구조", "데이터베이스", "운영체제", "알고리즘", "소프트웨어"),
    "정보통신": ("통신", "네트워크", "무선", "전송"),
    "네트워크관리사": ("네트워크", "통신"),
    "CCNA": ("네트워크", "라우팅", "스위칭"),
    "CCNP": ("네트워크", "라우팅"),
    "CCIE": ("네트워크",),
    "리눅스마스터": ("리눅스", "운영체제", "서버", "유닉스"),
    "정보보안": ("보안", "암호", "해킹"),
    "정보보호": ("보안", "암호"),
    "웹프로그래머": ("웹", "html", "자바스크립트"),
    "웹마스터": ("웹", "html"),
    "웹서버관리사": ("웹", "서버"),
    "전자상거래": ("전자상거래", "이커머스", "웹"),
    "OCJP": ("자바", "java", "객체지향"),
    "OJCP": ("자바", "java", "객체지향"),
    "OCP": ("데이터베이스", "오라클", "sql"),
    "모바일앱": ("모바일", "안드로이드", "ios", "앱"),
    "Unity": ("게임", "유니티", "unity"),
    "MCSE": ("윈도우", "서버", "운영체제"),
    "ESDP": ("임베디드", "시스템"),
    "PC정비사": ("컴퓨터구조", "하드웨어", "정비"),
    "컴퓨터활용": ("컴퓨터", "엑셀", "오피스"),
    "사회복지사": ("사회복지", "복지"),
    "보육교사": ("보육", "유아"),
    "전기": ("전기", "회로", "전력"),
    "기계": ("기계", "설계", "가공"),
    "토목": ("토목", "구조", "시공"),
    "측량": ("측량", "지적", "공간정보"),
    "드론": ("드론", "비행", "항공"),
}


def keywords_for(cert: str) -> tuple[str, ...]:
    """자격증명에서 키워드 세트를 찾는다. 표기 흔들림(공백·괄호)을 흡수한다."""
    flat = re.sub(r"[\s()·]", "", cert).lower()
    for key, words in CERT_KEYWORDS.items():
        if re.sub(r"\s", "", key).lower() in flat:
            return words
    return ()


def diagnose(dept: dict) -> dict:
    courses = dept["courses"]
    major = [c for c in courses if c["category"] == "전공"]
    total_major_credits = sum(c["credits"] for c in major) or 1

    by_job = defaultdict(list)
    for c in major:
        if c["talent_type"]:
            by_job[c["talent_type"]].append(c)

    jobs = []
    for job, cs in sorted(by_job.items(), key=lambda kv: -sum(c["credits"] for c in kv[1])):
        credits = sum(c["credits"] for c in cs)
        semesters = sorted({(c["year"], c["semester"]) for c in cs})
        gaps = []
        if not any(y == 1 for y, _ in semesters):
            gaps.append("1학년에 이 직무 과목이 없어 조기 진로 결정이 어렵다")
        if credits < total_major_credits * 0.2:
            gaps.append(f"전공 학점의 {credits / total_major_credits:.0%}만 배정돼 선택지가 좁다")

        jobs.append(
            {
                "job": job,
                "coverage_pct": round(credits / total_major_credits * 100, 1),
                "credits": credits,
                "covered_courses": [c["name"] for c in cs],
                "semesters": [f"{y}-{s}" for y, s in semesters],
                "gaps": gaps,
            }
        )

    # 자격증마다 대응 과목이 있는지 본다. 없으면 학생 개인 몫이라는 뜻.
    #
    # 셋으로 나눈다. 키워드 사전이 IT·공학 위주라 디자인·어학 자격증은 애초에
    # 판정할 수 없는데, 이를 "대응 과목 없음"으로 세면 없는 결손을 지어내게 된다.
    # 판정 불가는 판정 불가로 남긴다.
    supported, unsupported, unevaluated = [], [], []
    for cert in dept.get("certificates", []):
        words = keywords_for(cert)
        if not words:
            unevaluated.append({"certificate": cert, "reason": "키워드 사전 미수록"})
            continue
        hits = [
            c["name"] for c in courses if any(w.lower() in c["name"].lower() for w in words)
        ]
        entry = {"certificate": cert, "courses": hits[:5], "matched": bool(hits)}
        (supported if hits else unsupported).append(entry)

    ncs_count = sum(1 for c in major if c["ncs"])
    return {
        "dept_id": dept["dept_id"],
        "dept_name": dept["dept_name"],
        "years": dept["years"],
        "tier": dept["tier"],
        "extraction_confidence": dept["extraction_confidence"],
        "jobs": jobs,
        "certificates": {
            "total": len(dept.get("certificates", [])),
            "evaluated": len(supported) + len(unsupported),
            "supported": len(supported),
            "unsupported": [u["certificate"] for u in unsupported],
            "unevaluated": [u["certificate"] for u in unevaluated],
            "detail": supported + unsupported,
        },
        "ncs_ratio": round(ncs_count / len(major) * 100, 1) if major else 0.0,
        "field_based_courses": [c["name"] for c in courses if c["field_based"]],
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="트랙 B 진단 리포트 산출")
    ap.add_argument("--depts", default="../data/depts")
    ap.add_argument("--out", default="../data/reports")
    args = ap.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    summary = []

    for path in sorted(Path(args.depts).glob("*.json")):
        if path.name.startswith("_"):
            continue
        dept = json.loads(path.read_text(encoding="utf-8"))
        report = diagnose(dept)
        (out / path.name).write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        summary.append(
            {
                "dept_id": report["dept_id"],
                "dept_name": report["dept_name"],
                "jobs": len(report["jobs"]),
                "top_coverage": report["jobs"][0]["coverage_pct"] if report["jobs"] else 0,
                "certs_unsupported": len(report["certificates"]["unsupported"]),
                "certs_evaluated": report["certificates"]["evaluated"],
                "certs_total": report["certificates"]["total"],
                "ncs_ratio": report["ncs_ratio"],
            }
        )
        cert = report["certificates"]
        print(
            f"  {report['dept_name']:<24} 직무{len(report['jobs'])}종 "
            f"자격증 {cert['supported']}/{cert['evaluated']} 대응 "
            f"(판정불가 {len(cert['unevaluated'])}) NCS {report['ncs_ratio']}%",
            file=sys.stderr,
        )

    (out / "_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"\n{len(summary)}개 학과 리포트 산출", file=sys.stderr)


if __name__ == "__main__":
    main()
