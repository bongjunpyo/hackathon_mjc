import { Link, Navigate, useNavigate, useParams } from "react-router-dom";
import { DEPT_BY_ID, realJobs } from "../lib/depts";
import { CURRICULA } from "../lib/curricula";

/* 학과 상세 (DESIGN §4) — 학기별 커리큘럼 표 + CTA.
   CTA가 없으면 고립된 페이지다 — 탐색을 로드맵의 깔때기로 만든다. */
export default function DeptDetail() {
  const { deptId } = useParams();
  const navigate = useNavigate();
  const dept = DEPT_BY_ID[deptId];
  const cur = CURRICULA[deptId];

  if (!dept) return <Navigate to="/app/explore" replace />;

  return (
    <section className="flex flex-col gap-6 py-6">
      <div className="flex flex-wrap items-baseline gap-3">
        <h2 className="text-2xl font-extrabold tracking-tight">{dept.name}</h2>
        <span className="rounded bg-sky-soft px-2 py-0.5 font-mono text-xs font-bold text-navy">
          {dept.years}년제
        </span>
        <Link
          to="/app/explore"
          className="ml-auto rounded-lg px-3 py-1.5 text-sm font-bold text-navy transition-[background-color,scale] duration-150 hover:bg-sky-soft active:scale-[0.96]"
        >
          ← 학과 탐색
        </Link>
      </div>

      <dl className="flex flex-col gap-3 rounded-xl bg-sky-soft px-4 py-3.5 inset-ring inset-ring-edge">
        {[
          ["인재양성유형", realJobs(dept.careers), "교육과정표가 과목마다 붙인 직무 — 로드맵은 이 값으로 역산합니다"],
          ["취득 자격증", cur?.cert ?? [], null],
          ["진로", realJobs(dept.promoted ?? []).filter((j) => !dept.careers.includes(j)), "학과 소개 페이지 기준"],
        ].map(([k, items, note]) =>
          items.length === 0 ? null : (
            <div key={k}>
              <dt className="font-mono text-xs tracking-[0.1em] text-steel">
                {k}{note && <span className="ml-2 normal-case tracking-normal">— {note}</span>}
              </dt>
              <dd className="mt-1 flex flex-wrap gap-1.5">
                {items.map((it) => (
                  <span key={it} className="rounded-md bg-white px-2 py-0.5 text-sm text-navy">
                    {it}
                  </span>
                ))}
              </dd>
            </div>
          ),
        )}
      </dl>

      {cur && (
        <div className="flex flex-col gap-3">
          <h3 className="font-extrabold text-navy">학기별 커리큘럼 (교육과정표 기준)</h3>
          <div className="grid gap-3 md:grid-cols-2">
            {cur.sem.map((s) => (
              <div key={`${s.y}-${s.s}`} className="rounded-xl border border-edge bg-white p-4">
                <div className="flex items-baseline justify-between">
                  <b className="text-sm text-navy">{s.y}학년 {s.s}학기</b>
                  <span className="font-mono text-xs tabular-nums text-steel">
                    {s.c.reduce((a, c) => a + c.cr, 0)}학점
                  </span>
                </div>
                <ul className="mt-2 flex flex-col gap-1">
                  {s.c.map((c) => (
                    <li key={c.id} className="flex flex-wrap items-baseline gap-x-2 text-sm">
                      <span>{c.n}</span>
                      <span className="font-mono text-xs tabular-nums text-steel">{c.cr}</span>
                      <span className="text-xs text-steel">{c.cat}</span>
                      {c.job && (
                        <span className="rounded bg-gold/20 px-1 py-0.5 text-xs text-navy">{c.job}</span>
                      )}
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="sticky bottom-4 self-center">
        <button
          onClick={() => navigate("/app/roadmap", { state: { deptId } })}
          className="rounded-2xl bg-navy px-7 py-3.5 font-bold text-white shadow-[0_10px_30px_rgba(0,45,101,.35)] transition-[background-color,scale] duration-200 hover:bg-navy-deep active:scale-[0.96] focus-visible:outline-2 focus-visible:outline-gold"
        >
          이 학과로 내 로드맵 그리기 →
        </button>
      </div>
    </section>
  );
}
