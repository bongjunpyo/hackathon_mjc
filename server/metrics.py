"""검증기 효과 측정 — 설계서 §9.

재생성 루프를 끄고(1차 생성만) 켰을 때(최대 3회) 졸업요건 충족률을 비교한다.

**재는 대상은 결정론적 planner다. LLM이 아니다.** "LLM 단독 27%"로 부르면 거짓이 된다 —
심사에서 "27%는 어느 모델입니까"에 답이 없다. "1차 생성 27%"가 정확한 표현이다.
LLM 수치를 원하면 ANTHROPIC_API_KEY를 넣고 generate를 agent.generate로 바꿔 다시 잰다.

    uv run python metrics.py            # 표 출력
    uv run python metrics.py --md       # README용 마크다운
"""

import sys
from collections import Counter

import catalog
from loop import generate_roadmap
from planner import generate

# 재학생 시나리오. (현재 학년, 현재 학기) — 그 앞 학기는 이수한 것으로 본다
START_POINTS = [(1, 1), (2, 1)]


def scenarios():
    for meta in catalog.list_depts():
        dept = catalog.load_dept(meta["dept_id"])
        for job in dept.get("careers") or []:
            for year, semester in START_POINTS:
                if (year - 1) * 2 >= dept["years"] * 2:
                    continue
                yield dept, job, year, semester


def build_spec(dept, job, year, semester):
    start = (year, semester)
    completed = [c for c in dept["courses"] if (c["year"], c["semester"]) < start]
    return {
        "dept": dept,
        "target_job": job,
        "current_year": year,
        "current_semester": semester,
        "completed": completed,
        "completed_semesters": (year - 1) * 2 + (semester - 1),
    }


def measure():
    off_pass = on_pass = total = 0
    attempts = Counter()
    off_reasons = Counter()
    on_reasons = Counter()
    failed_depts = set()

    for dept, job, year, semester in scenarios():
        spec = build_spec(dept, job, year, semester)
        total += 1

        off = generate_roadmap(spec, generate, max_attempts=1)
        on = generate_roadmap(spec, generate, max_attempts=3)

        if off["validation"]["passed"]:
            off_pass += 1
        else:
            off_reasons.update(d["rule"] for d in off["validation"]["details"])

        if on["validation"]["passed"]:
            on_pass += 1
        else:
            on_reasons.update(d["rule"] for d in on["validation"]["details"])
            failed_depts.add(dept["dept_name"])
        attempts[on["attempts"]] += 1

    return {
        "total": total,
        "off_pass": off_pass,
        "on_pass": on_pass,
        "attempts": attempts,
        "off_reasons": off_reasons,
        "on_reasons": on_reasons,
        "failed_depts": sorted(failed_depts),
    }


def _pct(n, d):
    return round(n / d * 100, 1) if d else 0.0


def render(m, markdown=False):
    b = "**" if markdown else ""
    lines = []
    lines.append(f"시나리오 {m['total']}개 (전 학과 × 목표 직무 × 재학 시점 2종) — 결정론적 planner 기준")
    lines.append("")
    lines.append("| 검증기 재생성 루프 | 졸업요건 충족 | 충족률 |")
    lines.append("|---|---:|---:|")
    lines.append(f"| OFF (1차 생성만) | {m['off_pass']} / {m['total']} | {_pct(m['off_pass'], m['total'])}% |")
    lines.append(
        f"| {b}ON (최대 3회){b} | {b}{m['on_pass']} / {m['total']}{b} | {b}{_pct(m['on_pass'], m['total'])}%{b} |"
    )
    lines.append("")
    lines.append("재생성 횟수 분포: " + ", ".join(f"{k}회 {v}건" for k, v in sorted(m["attempts"].items())))
    lines.append("")
    if m["off_reasons"]:
        lines.append("OFF일 때 미달 사유: " + ", ".join(f"{k} {v}건" for k, v in m["off_reasons"].most_common()))
    if m["on_reasons"]:
        lines.append("ON일 때 남은 미달: " + ", ".join(f"{k} {v}건" for k, v in m["on_reasons"].most_common()))
        lines.append("해당 학과: " + ", ".join(m["failed_depts"]))
    else:
        lines.append("ON일 때 미달 0건")
    return "\n".join(lines)


if __name__ == "__main__":
    print(render(measure(), markdown="--md" in sys.argv))
