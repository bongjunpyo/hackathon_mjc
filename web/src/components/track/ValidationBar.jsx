/* 검증 배지 바 (DESIGN §2.1) — 판정 3종 + 남은 학점 + engine 태그.
   Roadmap.jsx(v1) 배지와 같은 룰 표기. engine 폴백을 숨기지 않는다. */
const RULES = [
  { key: "major_credits", rule: "major_credits", label: "전공", unit: "학점" },
  { key: "liberal_credits", rule: "liberal_required", label: "교양필수", unit: "학점" },
  { key: "semesters", rule: "semesters", label: "재학", unit: "학기" },
];

const ENGINE = {
  llm: { text: "AI 생성", cls: "bg-gold text-navy-deep" },
  rule: { text: "규칙 생성(폴백)", cls: "bg-white/20 text-white" },
};

export default function ValidationBar({ validation, engine }) {
  if (!validation) return null;
  const ok = validation.passed;
  const miss = (rule) => validation.details?.find((d) => d.rule === rule);
  const eng = ENGINE[engine] ?? (engine ? { text: engine, cls: "bg-white/20 text-white" } : null);

  return (
    <div
      className={`flex flex-wrap items-center gap-x-5 gap-y-1.5 rounded-xl px-4 py-3 ${
        ok ? "bg-navy text-white" : "border-2 border-gold bg-gold/15 text-navy"
      }`}
    >
      <span className="font-bold">{ok ? "✓ 졸업요건 충족" : "⚠ 졸업요건 미달"}</span>
      <ul className="flex flex-wrap gap-x-4 gap-y-1 font-mono text-xs tabular-nums">
        {RULES.map(({ key, rule, label, unit }) => {
          const value = validation[key];
          if (value == null) return null;
          const m = miss(rule);
          return (
            <li key={key} className={m ? "font-bold" : "opacity-85"}>
              {m ? "✗" : "✓"} {label} {value}{unit}
              {m && ` (필요 ${m.required})`}
            </li>
          );
        })}
        {validation.remaining_credits > 0 && (
          <li className="opacity-85">
            남은 {validation.remaining_credits}학점 — 교양선택·일반선택
          </li>
        )}
      </ul>
      {eng && (
        <span className={`ml-auto rounded px-2 py-0.5 font-mono text-[0.625rem] font-bold ${eng.cls}`}>
          {eng.text}
        </span>
      )}
    </div>
  );
}
