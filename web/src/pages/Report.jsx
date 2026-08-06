import { useEffect, useState } from "react";
import { getReport } from "../lib/api";
import { useApp } from "../store";

/* 트랙 B — 학교용 교육과정 정합도 리포트.
   API(GET /report/{dept_id}) 미연결 시 안내만 띄운다. 가짜 수치를 그리지 않는다. */
export default function Report() {
  const { input } = useApp();
  const [state, setState] = useState({ status: "loading", data: null });

  useEffect(() => {
    let alive = true;
    getReport(input.deptId)
      .then((data) => alive && setState({ status: "ok", data }))
      .catch(() => alive && setState({ status: "unavailable", data: null }));
    return () => {
      alive = false;
    };
  }, [input.deptId]);

  if (state.status === "loading") {
    return <p className="text-ink-2">리포트를 불러오는 중…</p>;
  }

  if (state.status === "unavailable") {
    return (
      <section className="flex flex-col gap-3">
        <h2 className="text-2xl font-extrabold tracking-tight">학교용 정합도 리포트</h2>
        <p className="max-w-[60ch] text-ink-2">
          학과 교육과정과 NCS 직무기술서를 대조해 직무별 커버리지·결손 과목·인재양성유형 라벨
          불일치를 보여주는 화면입니다.
        </p>
        <p className="rounded-lg border border-dashed border-edge bg-sky-soft/60 p-3 font-mono text-xs text-steel">
          정합도 API가 아직 연결되지 않았습니다. 수치를 임의로 표시하지 않습니다.
        </p>
      </section>
    );
  }

  return (
    <section className="flex flex-col gap-5">
      <h2 className="text-2xl font-extrabold tracking-tight">학교용 정합도 리포트</h2>
      <ul className="space-y-4">
        {state.data.jobs.map((j) => (
          <li key={j.job} className="rounded-xl border border-edge bg-white p-5">
            <div className="flex items-baseline justify-between gap-3">
              <h3 className="font-extrabold text-navy">{j.job}</h3>
              <span className="font-mono text-sm tabular-nums text-steel">
                커버리지 {j.coverage_pct}%
              </span>
            </div>
            <div className="mt-2 h-2 overflow-hidden rounded-full bg-edge">
              <div className="h-full rounded-full bg-navy" style={{ width: `${j.coverage_pct}%` }} />
            </div>
            {j.gaps?.length > 0 && (
              <p className="mt-3 text-sm text-ink-2">
                <span className="font-semibold">결손:</span> {j.gaps.join(", ")}
              </p>
            )}
            {j.label_mismatches?.length > 0 && (
              <p className="mt-1 text-sm text-ink-2">
                <span className="font-semibold">라벨 불일치:</span>{" "}
                {j.label_mismatches.join(", ")}
              </p>
            )}
          </li>
        ))}
      </ul>
    </section>
  );
}
