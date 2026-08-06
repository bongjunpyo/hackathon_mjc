import { useEffect, useRef } from "react";
import ExternalPanel from "./ExternalPanel";
import { certExternal, certName, certTip, externalFor } from "../lib/external";

/* 행선판 클릭 → 학기 상세. 시안의 .detail CSS 대신 Tailwind로 다시 짰다. */
export default function SemesterDetail({ semester, index, onClose }) {
  const closeRef = useRef(null);
  const open = Boolean(semester);

  useEffect(() => {
    if (!open) return;
    const prevFocus = document.activeElement;
    closeRef.current?.focus();
    document.body.style.overflow = "hidden";
    const onKey = (e) => e.key === "Escape" && onClose();
    addEventListener("keydown", onKey);
    return () => {
      removeEventListener("keydown", onKey);
      document.body.style.overflow = "";
      prevFocus?.focus?.();
    };
  }, [open, onClose]);

  if (!open) return null;
  const cert = semester.certificates?.[0];
  const cName = certName(cert);
  const cTip = certTip(cert);

  return (
    <div
      className="fixed inset-0 z-80 grid place-items-center p-5"
      role="dialog"
      aria-modal="true"
      aria-labelledby="semester-detail-title"
    >
      <button
        aria-label="닫기"
        onClick={onClose}
        className="absolute inset-0 cursor-default bg-[rgba(6,18,38,0.44)] backdrop-blur-md"
      />
      <div className="relative max-h-[86vh] w-[min(580px,94vw)] overflow-y-auto rounded-3xl bg-white shadow-[0_8px_24px_rgba(0,26,61,.18),0_40px_120px_rgba(0,26,61,.4)]">
        <header className="sticky top-0 rounded-t-3xl border-b-[5px] border-gold bg-navy px-6 pb-4 pt-5 text-white">
          <button
            ref={closeRef}
            onClick={onClose}
            aria-label="닫기"
            className="absolute right-3.5 top-3.5 grid size-10 place-items-center rounded-full bg-white/15 text-white transition-[background-color,scale] duration-200 hover:bg-white/25 active:scale-[0.96] focus-visible:outline-2 focus-visible:outline-gold"
          >
            ✕
          </button>
          <span className="inline-flex h-[26px] items-center rounded-full bg-gold px-2.5 font-mono text-xs font-extrabold text-navy-deep">
            MJ0{index + 1}
          </span>
          <div className="mt-1 flex items-center gap-3">
            <h3 id="semester-detail-title" className="text-2xl font-extrabold">
              {semester.name}
            </h3>
            <span className="ml-auto font-mono text-sm tabular-nums text-sky">
              {semester.credits}학점 · {semester.en}
            </span>
          </div>
          {semester.goal && (
            <p className="mt-2.5 text-sm text-sky">이 학기의 목표 — {semester.goal}</p>
          )}
        </header>

        <div className="flex flex-col gap-3.5 px-6 pb-6 pt-5">
          <h4 className="font-mono text-xs uppercase tracking-[0.12em] text-steel">
            이수 과목 · 왜 이 학기인가
          </h4>
          {semester.courses.map((c) => {
            const ext = externalFor(c);
            return (
              <div key={c.course_id ?? c.name} className="flex flex-col gap-2">
                <div className="rounded-xl bg-sky-soft px-4 py-3 inset-ring inset-ring-edge">
                  <b className="mb-0.5 block text-navy">{c.name}</b>
                  {c.why && <p className="text-sm text-ink-2">{c.why}</p>}
                </div>
                {/* 현장실습·산학인턴십은 "어디서"가 학교 시스템에 있다 */}
                <ExternalPanel info={ext} />
              </div>
            );
          })}

          {cName && (
            <>
              <h4 className="mt-1 font-mono text-xs uppercase tracking-[0.12em] text-steel">
                자격증 타이밍
              </h4>
              <div className="rounded-xl bg-gold/15 px-4 py-3 inset-ring-[1.5px] inset-ring-gold/55">
                <b className="mb-0.5 block text-navy">🎫 {cName}</b>
                {cTip && <p className="text-sm text-ink-2">{cTip}</p>}
              </div>
              <ExternalPanel info={certExternal(cName)} />
            </>
          )}

          <p className="border-t border-dashed border-edge pt-3 text-xs text-steel">
            추천 근거: 교육과정표(이수구분·인재양성유형) × NCS 직무기술서 매핑.
            외부 시스템 링크는 학교·기관 공식 페이지로 연결됩니다.
          </p>
        </div>
      </div>
    </div>
  );
}
