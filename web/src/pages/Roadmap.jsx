import { Link } from "react-router-dom";
import { useApp } from "../store";

function ValidationBadge({ validation }) {
  if (!validation) return null;
  const ok = validation.passed;
  return (
    <div
      className={`flex flex-wrap items-center gap-3 rounded-xl px-4 py-3 font-bold ${
        ok ? "bg-navy text-white" : "border-2 border-gold bg-gold/15 text-navy"
      }`}
    >
      <span>{ok ? "✓ 졸업요건 충족 — 검증기 통과" : "미달 항목이 있습니다"}</span>
      <span className="font-mono text-xs font-medium tabular-nums opacity-80">
        총 {validation.total_credits}학점 · 전공 {validation.major_credits} · 교양{" "}
        {validation.liberal_credits}
      </span>
      {!ok && validation.details?.length > 0 && (
        <ul className="w-full space-y-1 pt-1 font-mono text-xs font-medium">
          {validation.details.map((d, i) => (
            <li key={i}>
              {d.rule}: 필요 {d.required} / 현재 {d.actual} — {d.shortfall} 부족
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function SemesterCard({ s }) {
  return (
    <li className="relative pl-11">
      <span className="absolute left-[7px] top-6 size-3.5 rounded-full border-[3px] border-navy bg-white" />
      <div className="rounded-xl border border-edge bg-white p-5">
        <div className="flex items-baseline justify-between gap-3">
          <h3 className="font-extrabold text-navy">
            {s.year}학년 {s.semester}학기
          </h3>
          <span className="font-mono text-xs tabular-nums text-steel">{s.credits}학점</span>
        </div>
        {s.goal && <p className="mt-1 text-sm text-ink-2">{s.goal}</p>}
        <ul className="mt-3 space-y-2">
          {s.courses.map((c) => (
            <li key={c.course_id} className="text-sm">
              <span className="font-semibold">{c.name}</span>
              {c.why && <span className="block text-ink-2">{c.why}</span>}
            </li>
          ))}
        </ul>
        {s.certificates?.length > 0 && (
          <div className="mt-3 flex flex-wrap gap-2">
            {s.certificates.map((c) => (
              <span
                key={c.name}
                title={c.tip}
                className="rounded-md border border-gold/60 bg-gold/15 px-2.5 py-1 text-xs font-bold text-navy"
              >
                🎫 {c.name}
              </span>
            ))}
          </div>
        )}
      </div>
    </li>
  );
}

export default function Roadmap() {
  const { roadmap, input } = useApp();

  if (!roadmap) {
    return (
      <p className="text-ink-2">
        아직 생성된 로드맵이 없습니다.{" "}
        <Link to="/app/input" className="font-bold text-navy underline">
          로드맵 만들기
        </Link>
        에서 시작하세요.
      </p>
    );
  }

  return (
    <section className="flex flex-col gap-5">
      <div className="flex flex-wrap items-baseline gap-3">
        <h2 className="text-2xl font-extrabold tracking-tight">
          {input.targetJob}까지의 노선
        </h2>
        {roadmap.source === "mock" && (
          <span className="rounded-md bg-gold/25 px-2 py-0.5 font-mono text-xs font-bold text-navy">
            목데이터 — 서버 미연결
          </span>
        )}
      </div>

      <ValidationBadge validation={roadmap.validation} />

      <ol className="relative space-y-4 before:absolute before:bottom-3 before:left-3 before:top-3 before:w-[3px] before:rounded before:bg-navy/50">
        {roadmap.semesters.map((s) => (
          <SemesterCard key={`${s.year}-${s.semester}`} s={s} />
        ))}
      </ol>
    </section>
  );
}
