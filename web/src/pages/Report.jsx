import { useEffect, useState } from "react";
import { getReport } from "../lib/api";
import { DEPTS, DEPT_BY_ID } from "../lib/depts";
import { useApp } from "../store";

/* 트랙 B — 학교용 교육과정 진단 리포트.

   대조하는 두 값은 전부 학교 문서에서 나온다: 학과가 소개 페이지에 적은 진로와,
   교육과정표 인재양성유형 열에 붙은 라벨. NCS 직무기술서는 수집되지 않아 쓰지 않는다
   (server/report.py). "이 판단의 근거가 뭐냐"에 학교 자기 문서로 답할 수 있어야 한다.

   API가 없으면 안내만 띄운다. 수치를 지어내지 않는다. */

const MISMATCH_KIND = {
  joined: { label: "한 칸에 여러 직무", tone: "gold" },
  not_a_job: { label: "직무명이 아님", tone: "gold" },
  near_duplicate: { label: "오타로 갈린 라벨", tone: "navy" },
  same_set: { label: "같은 묶음, 다른 표기", tone: "navy" },
};

export default function Report() {
  const { input } = useApp();
  const [deptId, setDeptId] = useState(input.deptId);
  const [state, setState] = useState({ status: "loading", data: null });
  const [audit, setAudit] = useState(null);

  useEffect(() => {
    let alive = true;
    setState({ status: "loading", data: null });
    getReport(deptId)
      .then((data) => alive && setState({ status: "ok", data }))
      .catch(() => alive && setState({ status: "unavailable", data: null }));
    return () => {
      alive = false;
    };
  }, [deptId]);

  /* 학과 하나짜리 리포트는 "우리 학과 얘기"로 끝난다. 학교가 받아서 쓸 수 있으려면
     몇 개 학과에 몇 건이 있는지가 나와야 한다. 34번 호출하므로 눌러야 돈다. */
  async function auditAll() {
    setAudit({ done: 0, total: DEPTS.length, rows: [] });
    const rows = [];
    for (const [i, d] of DEPTS.entries()) {
      try {
        const r = await getReport(d.id);
        if (r.label_mismatches?.length) rows.push({ dept: d.name, items: r.label_mismatches });
      } catch {
        // 한 학과가 죽어도 나머지 집계는 낸다 — 부분 결과가 없는 것보다 낫다
      }
      setAudit({ done: i + 1, total: DEPTS.length, rows: [...rows] });
    }
  }

  const header = (
    <div className="flex flex-col gap-3">
      <h2 className="text-2xl font-extrabold tracking-tight text-balance">
        학교용 교육과정 진단 리포트
      </h2>
      <p className="max-w-[62ch] text-ink-2">
        학과가 소개 페이지에 적은 <b>진로</b>와 교육과정표 <b>인재양성유형</b> 라벨을
        대조합니다. 두 값 다 학교 문서에서 나오므로 판단의 출처를 되짚을 수 있습니다.
      </p>
      <label className="flex flex-wrap items-center gap-2.5">
        <span className="font-mono text-xs tracking-[0.1em] text-steel">학과</span>
        <select
          value={deptId}
          onChange={(e) => setDeptId(e.target.value)}
          className="rounded-lg border border-edge bg-white px-3 py-2 text-ink focus-visible:outline-2 focus-visible:outline-gold"
        >
          {DEPTS.map((d) => (
            <option key={d.id} value={d.id}>
              {d.name}
            </option>
          ))}
        </select>
      </label>
    </div>
  );

  if (state.status === "loading") {
    return (
      <section className="flex flex-col gap-5">
        {header}
        <p className="text-ink-2">리포트를 불러오는 중…</p>
      </section>
    );
  }

  if (state.status === "unavailable") {
    return (
      <section className="flex flex-col gap-5">
        {header}
        <p className="rounded-lg border border-dashed border-edge bg-sky-soft/60 p-3 font-mono text-xs text-steel">
          정합도 API(GET /report/{deptId})가 연결되지 않았습니다. 수치를 임의로 표시하지
          않습니다.
        </p>
      </section>
    );
  }

  const r = state.data;
  const dept = DEPT_BY_ID[deptId];
  // 대응 없는 진로(0% · 매칭 라벨 0)를 뒤로 뺀다 — 첫인상이 진단서가 되게
  const isUnmatched = (j) => j.coverage_pct === 0 && j.matched_labels.length === 0;
  const covered = r.jobs.filter((j) => !isUnmatched(j));
  const unmatched = r.jobs.filter(isUnmatched);

  return (
    <section className="flex flex-col gap-6">
      {header}

      <dl className="flex flex-wrap gap-x-8 gap-y-2 rounded-xl bg-sky-soft px-4 py-3.5 inset-ring inset-ring-edge">
        {[
          ["학과", r.dept_name],
          ["전공 학점", `${r.major_credits}학점`],
          ["직무", `${r.jobs.length}종`],
          ["데이터 품질", `Tier ${r.tier} · 추출 신뢰도 ${r.extraction_confidence}`],
        ].map(([k, v]) => (
          <div key={k}>
            <dt className="font-mono text-xs tracking-[0.1em] text-steel">{k}</dt>
            <dd className="font-bold text-navy tabular-nums">{v}</dd>
          </div>
        ))}
      </dl>

      <div className="flex flex-col gap-3">
        <h3 className="font-extrabold text-navy">직무별 커버리지</h3>
        <p className="max-w-[62ch] text-sm text-ink-2">
          그 직무로 라벨링된 과목의 학점이 전공 학점에서 차지하는 비율입니다.
        </p>
        <ul className="flex flex-col gap-3">
          {covered.map((j) => (
            <JobRow key={j.job} job={j} />
          ))}
        </ul>

        {/* 0%짜리를 빈 막대로 섞어 두면 "데이터가 안 나왔다"로 읽힌다.
            대응 없음은 이 리포트의 결과지 고장이 아니다 — 따로 묶어 그렇게 쓴다 */}
        {unmatched.length > 0 && (
          <div className="flex flex-col gap-2 rounded-xl border-2 border-gold bg-gold/15 px-4 py-3.5">
            <b className="text-navy">
              ⚠ 교육과정에 대응이 없는 진로{" "}
              <span className="font-mono tabular-nums">{unmatched.length}종</span>
            </b>
            <p className="text-sm text-ink-2">
              학과 소개 페이지가 홍보하는 진로인데, 교육과정표 인재양성유형 열에 같은 직무가
              없습니다. 학생이 이 진로를 목표로 잡으면 어느 과목을 들어야 하는지 학교 문서
              안에서 답이 나오지 않습니다.
            </p>
            <ul className="flex flex-wrap gap-1.5">
              {unmatched.map((j) => (
                <li
                  key={j.job}
                  className="rounded-lg border border-gold/60 bg-white px-2.5 py-1 text-sm text-navy"
                >
                  {j.job}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>

      <div className="flex flex-col gap-3">
        <h3 className="font-extrabold text-navy">
          라벨 점검 <span className="font-mono text-sm tabular-nums">{r.label_mismatches.length}건</span>
        </h3>
        {r.label_mismatches.length === 0 ? (
          <p className="text-sm text-ink-2">
            {dept?.name}의 인재양성유형 라벨에서는 문제를 찾지 못했습니다.
          </p>
        ) : (
          <ul className="flex flex-col gap-2">
            {r.label_mismatches.map((m, i) => (
              <MismatchRow key={`${m.kind}-${i}`} item={m} />
            ))}
          </ul>
        )}
      </div>

      <div className="flex flex-col gap-3 border-t border-edge pt-5">
        <h3 className="font-extrabold text-navy">전 학과 일괄 점검</h3>
        <p className="max-w-[62ch] text-sm text-ink-2">
          34개 학과를 한 번에 훑어 라벨 문제가 몇 개 학과에 몇 건 있는지 셉니다.
        </p>
        {audit ? <AuditResult audit={audit} /> : (
          <button
            onClick={auditAll}
            className="self-start rounded-xl bg-navy px-5 py-2.5 font-bold text-white transition-[background-color,scale] duration-200 hover:bg-navy-deep active:scale-[0.96] focus-visible:outline-2 focus-visible:outline-gold"
          >
            34개 학과 점검하기
          </button>
        )}
      </div>
    </section>
  );
}

function JobRow({ job }) {
  const [open, setOpen] = useState(false);
  const over = job.coverage_pct > 100;

  return (
    <li className="rounded-xl border border-edge bg-white p-4">
      <div className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1">
        <b className="text-navy">{job.job}</b>
        <span className="font-mono text-sm tabular-nums text-steel">
          {job.covered_credits}학점 · {job.coverage_pct}%
        </span>
      </div>
      <div className="mt-2 h-2 overflow-hidden rounded-full bg-edge">
        <div
          className={`h-full rounded-full ${over ? "bg-gold" : "bg-navy"}`}
          style={{ width: `${Math.min(job.coverage_pct, 100)}%` }}
        />
      </div>
      {/* 분자는 라벨 붙은 전 과목, 분모는 전공 학점이라 일반선택에 라벨이 붙으면 100%를 넘는다.
          막대를 잘라 감추지 않고 수치와 이유를 같이 낸다 */}
      {over && (
        <p className="mt-2 text-xs text-steel">
          ⚠ 100%를 넘습니다 — 라벨이 붙은 과목에 전공이 아닌 것(일반선택 등)이 섞여 있습니다.
        </p>
      )}
      {job.gaps.length > 0 && (
        <p className="mt-2 text-sm font-semibold text-navy">결손: {job.gaps.join(", ")}</p>
      )}

      {job.covered_courses.length > 0 && (
        <>
          <button
            onClick={() => setOpen((v) => !v)}
            aria-expanded={open}
            className="mt-2 rounded-md py-1 font-mono text-xs text-steel transition-[color,scale] duration-150 hover:text-navy active:scale-[0.96] focus-visible:outline-2 focus-visible:outline-gold"
          >
            {open ? "▲ 접기" : `▾ 해당 과목 ${job.covered_courses.length}개`}
          </button>
          {open && (
            <ul className="mt-1.5 flex flex-wrap gap-1.5">
              {job.covered_courses.map((c) => (
                <li
                  key={c.course_id}
                  className="rounded-md bg-sky-soft px-2 py-1 text-xs text-navy"
                >
                  {c.name} <span className="font-mono tabular-nums text-steel">{c.credits}</span>
                </li>
              ))}
            </ul>
          )}
        </>
      )}
    </li>
  );
}

function MismatchRow({ item }) {
  const kind = MISMATCH_KIND[item.kind] ?? { label: item.kind, tone: "navy" };
  return (
    <li className="rounded-xl border border-edge bg-white p-4">
      <div className="flex flex-wrap items-baseline gap-2">
        <span
          className={`rounded px-1.5 py-0.5 font-mono text-[0.625rem] font-bold ${
            kind.tone === "gold" ? "bg-gold text-navy-deep" : "bg-navy text-white"
          }`}
        >
          {kind.label}
        </span>
        {item.labels.map((l) => (
          <code key={l} className="rounded bg-sky-soft px-1.5 py-0.5 text-sm text-navy">
            {l}
          </code>
        ))}
      </div>
      <p className="mt-1.5 text-sm text-ink-2">{item.note}</p>
      {item.parts && (
        <p className="mt-1 font-mono text-xs text-steel">→ {item.parts.join(" / ")}</p>
      )}
    </li>
  );
}

function AuditResult({ audit }) {
  const running = audit.done < audit.total;
  const count = audit.rows.reduce((a, r) => a + r.items.length, 0);
  const byKind = {};
  audit.rows.forEach((r) => r.items.forEach((i) => (byKind[i.kind] = (byKind[i.kind] ?? 0) + 1)));

  return (
    <div className="flex flex-col gap-3">
      <p className="font-mono text-sm tabular-nums text-steel">
        {running
          ? `점검 중… ${audit.done}/${audit.total}`
          : `${audit.total}개 학과 · 문제 ${audit.rows.length}개 학과 · ${count}건`}
      </p>
      {!running && (
        <ul className="flex flex-wrap gap-2">
          {Object.entries(byKind).map(([k, n]) => (
            <li
              key={k}
              className="rounded-lg border border-edge px-2.5 py-1 font-mono text-xs tabular-nums text-navy"
            >
              {MISMATCH_KIND[k]?.label ?? k} {n}
            </li>
          ))}
        </ul>
      )}
      <ul className="flex flex-col gap-2">
        {audit.rows.map((r) => (
          <li key={r.dept} className="rounded-xl border border-edge bg-white p-3.5">
            <b className="text-sm text-navy">{r.dept}</b>
            <ul className="mt-1.5 flex flex-col gap-1">
              {r.items.map((i, n) => (
                <li key={n} className="text-sm text-ink-2">
                  <span className="font-mono text-xs text-steel">
                    [{MISMATCH_KIND[i.kind]?.label ?? i.kind}]
                  </span>{" "}
                  {i.labels.join(" · ")} — {i.note}
                </li>
              ))}
            </ul>
          </li>
        ))}
      </ul>
    </div>
  );
}
