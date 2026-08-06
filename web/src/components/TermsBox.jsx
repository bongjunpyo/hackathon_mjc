import { useState } from "react";
import { TERMS } from "../lib/terms";

/* 약관 동의 — 항목별 체크 + 전문 펼치기.

   "전체 동의" 하나만 두지 않는다. 무엇에 동의하는지 항목이 보여야 하고,
   전문을 화면 안에서 읽을 수 있어야 한다 (새 탭으로 보내면 폼이 날아간다). */
export default function TermsBox({ value, onChange }) {
  const items = Object.values(TERMS);
  const [open, setOpen] = useState(null);
  const allOn = items.every((t) => value[t.key]);

  const toggleAll = () =>
    onChange(Object.fromEntries(items.map((t) => [t.key, !allOn])));

  return (
    <fieldset className="flex flex-col gap-1.5 rounded-xl border border-edge bg-white p-3.5">
      <legend className="px-1 font-mono text-xs tracking-[0.1em] text-steel">약관 동의</legend>

      <label className="flex cursor-pointer items-center gap-2.5 rounded-lg px-1.5 py-1.5 font-bold text-navy hover:bg-sky-soft">
        <input type="checkbox" className="size-4 accent-navy" checked={allOn} onChange={toggleAll} />
        전체 동의
      </label>
      <hr className="border-edge" />

      {items.map((t) => (
        <div key={t.key}>
          <div className="flex items-center gap-1">
            <label className="flex flex-1 cursor-pointer items-center gap-2.5 rounded-lg px-1.5 py-1.5 text-sm hover:bg-sky-soft">
              <input
                type="checkbox"
                className="size-4 accent-navy"
                checked={Boolean(value[t.key])}
                onChange={(e) => onChange({ ...value, [t.key]: e.target.checked })}
              />
              <span>
                <span className="font-bold text-navy">{t.required ? "[필수]" : "[선택]"}</span>{" "}
                {t.label}에 동의합니다
              </span>
            </label>
            <button
              type="button"
              onClick={() => setOpen(open === t.key ? null : t.key)}
              aria-expanded={open === t.key}
              className="rounded-md px-2 py-1 font-mono text-xs text-steel underline decoration-edge underline-offset-4 transition-colors hover:text-navy"
            >
              {open === t.key ? "접기" : "전문 보기"}
            </button>
          </div>

          {open === t.key && (
            <div className="mx-1.5 mb-2 max-h-52 overflow-y-auto rounded-lg bg-hall px-3.5 py-3 text-xs leading-relaxed text-ink-2">
              {t.sections.map((s) => (
                <p key={s.title} className="mb-2.5 last:mb-0">
                  <b className="block text-navy">{s.title}</b>
                  {s.body}
                </p>
              ))}
            </div>
          )}
        </div>
      ))}
    </fieldset>
  );
}
