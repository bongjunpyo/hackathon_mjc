import { Link } from "react-router-dom";
import { useApp } from "../store";

/* 졸업요건 4종 — 값 키는 API 응답(DESIGN.md §5), 라벨은 화면용.
   미달 항목은 details[].rule로 찾아 붙인다. */
const REQUIREMENTS = [
  { key: "total_credits", rule: "total_credits", label: "총 학점", unit: "학점" },
  { key: "major_credits", rule: "major_credits", label: "전공", unit: "학점" },
  { key: "liberal_credits", rule: "liberal_credits", label: "교양", unit: "학점" },
  { key: "semesters", rule: "semesters", label: "재학", unit: "학기" },
];

function ValidationBadge({ validation }) {
  if (!validation) return null;
  const ok = validation.passed;
  const shortfallOf = (rule) => validation.details?.find((d) => d.rule === rule);

  return (
    <div
      className={`flex flex-col gap-3 rounded-xl px-4 py-3 ${
        ok ? "bg-navy text-white" : "border-2 border-gold bg-gold/15 text-navy"
      }`}
    >
      <span className="font-bold">
        {ok ? "✓ 졸업요건 충족 — 검증기 통과" : "⚠ 졸업요건 미달 항목이 있습니다"}
      </span>

      {/* 항목별 충족 상태 — 4종을 모두 보여준다 (issue #5) */}
      <ul className="flex flex-wrap gap-x-5 gap-y-1 font-mono text-xs tabular-nums">
        {REQUIREMENTS.map(({ key, rule, label, unit }) => {
          const value = validation[key];
          if (value == null) return null;
          const miss = shortfallOf(rule);
          return (
            <li key={key} className={miss ? "font-bold" : "opacity-80"}>
              {miss ? "✗" : "✓"} {label} {value}
              {unit}
              {miss && <span> (필요 {miss.required})</span>}
            </li>
          );
        })}
      </ul>

      {/* 미달 항목의 "무엇을 어떻게 고칠지" — 검증기가 재생성 프롬프트로 쓰는 fix 문구를
         화면에도 그대로 보여준다. LLM이 받는 지시와 사람이 보는 안내가 같아야
         "검증기가 잡아서 다시 짰다"가 증명된다. */}
      {validation.details?.length > 0 && (
        <ul className="flex flex-col gap-1.5 border-t border-navy/15 pt-2.5">
          {validation.details.map((d, i) => (
            <li key={d.rule ?? i} className="flex flex-wrap items-baseline gap-x-2 text-sm">
              <span className="font-bold">✗ {d.label ?? d.rule}</span>
              <span className="font-mono text-xs tabular-nums opacity-70">
                {d.actual} / {d.required} — {d.shortfall} 부족
              </span>
              {d.fix && <span className="w-full font-medium">→ {d.fix}</span>}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function SemesterCard({ s }) {
  // 동결 계약(DESIGN.md §5)의 semesters[]에는 credits가 없다 — 과목에서 합산한다
  const credits = s.credits ?? s.courses.reduce((a, c) => a + (c.credits ?? 0), 0);
  return (
    <li className="relative pl-11">
      <span className="absolute left-[7px] top-6 size-3.5 rounded-full border-[3px] border-navy bg-white" />
      <div className="rounded-xl border border-edge bg-white p-5">
        <div className="flex items-baseline justify-between gap-3">
          <h3 className="font-extrabold text-navy">
            {s.year}학년 {s.semester}학기
          </h3>
          <span className="font-mono text-xs tabular-nums text-steel">{credits}학점</span>
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
        {roadmap.source === "curriculum" && (
          <span className="rounded-md bg-gold/25 px-2 py-0.5 font-mono text-xs font-bold text-navy">
            교육과정표 표준 경로 — AI 재배치 전
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
