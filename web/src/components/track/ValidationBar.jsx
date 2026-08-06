/* 검증 배지 바 (DESIGN §2.1).
   판정 3종은 각각 칩으로 끊는다 — 한 줄로 이으면 어느 요건이 걸렸는지 안 읽힌다.
   판정 / 정보(배치·남은 학점) / 엔진 세 구획이고, engine 폴백을 숨기지 않는다. */
const RULES = [
  { key: "major_credits", rule: "major_credits", label: "전공" },
  { key: "liberal_credits", rule: "liberal_required", label: "교양필수" },
  { key: "semesters", rule: "semesters", label: "재학학기" },
];

const REQ = {
  major_credits: (v) => v.details?.find((d) => d.rule === "major_credits")?.required,
  liberal_credits: (v) => v.details?.find((d) => d.rule === "liberal_required")?.required,
  semesters: (v) => v.details?.find((d) => d.rule === "semesters")?.required,
};

const ENGINE = {
  llm: "AI 생성",
  rule: "규칙 생성(폴백)",
};

export default function ValidationBar({ validation, engine, attempts }) {
  if (!validation) return null;
  const ok = validation.passed;
  const miss = (rule) => validation.details?.find((d) => d.rule === rule);

  const engineText = ENGINE[engine] ?? engine;
  const attemptText = attempts ? `${attempts}회 통과` : null;

  return (
    <div
      className={`flex flex-wrap items-center gap-2 rounded-xl px-3 py-2.5 ${
        ok ? "bg-navy text-white" : "border-2 border-gold bg-gold/15 text-navy"
      }`}
    >
      {/* 판정 구획 — 요건마다 칩 하나 */}
      {RULES.map(({ key, rule, label }) => {
        const value = validation[key];
        if (value == null) return null;
        const m = miss(rule);
        const required = m?.required ?? REQ[key](validation);
        return (
          <span
            key={key}
            className={`rounded-lg px-2.5 py-1 font-mono text-xs font-bold tabular-nums ${
              ok ? "bg-white/12" : m ? "bg-gold text-navy-deep" : "bg-white/70"
            }`}
          >
            {label} {value}
            {required != null && `/${required}`} {m ? "✗" : "✓"}
          </span>
        );
      })}

      {/* 정보 구획 — 판정이 아니라 알림. 배경 없이 둬서 칩과 구분된다 */}
      <span className="px-1 font-mono text-xs tabular-nums opacity-80">
        배치 {validation.total_credits}학점
        {validation.remaining_credits > 0 &&
          ` · 졸업까지 ${validation.remaining_credits}학점 남음`}
      </span>

      {engineText && (
        <span
          className={`ml-auto rounded-lg px-2.5 py-1 font-mono text-xs font-bold ${
            ok ? "bg-white/12" : "bg-white/70"
          }`}
        >
          {engineText}
          {attemptText && ` · ${attemptText}`}
        </span>
      )}
    </div>
  );
}
