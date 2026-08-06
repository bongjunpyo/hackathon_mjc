import { certName, certTip } from "../../lib/external";

/* 학기 상세 패널 (DESIGN §2.6) — 역명판 헤더 문법은 SemesterDetail(3D 모달)과 동일:
   navy 헤더 + gold 하단 보더 + MJ0N 배지. 같은 데이터가 3D·2D 어디서든 같은 얼굴이다. */
export default function SemesterPanel({ semester, index, targetJob, isLast, onNext, onGraduate }) {
  if (!semester) return null;
  const credits =
    semester.credits ?? semester.courses.reduce((a, c) => a + (c.credits ?? 0), 0);

  return (
    <aside className="flex flex-col overflow-hidden rounded-2xl bg-white shadow-[0_3px_8px_rgba(0,26,61,.12),0_18px_44px_rgba(0,26,61,.16)]">
      <header className="border-b-[5px] border-gold bg-navy px-5 pb-3.5 pt-4 text-white">
        <span className="inline-flex h-[24px] items-center rounded-full bg-gold px-2.5 font-mono text-xs font-extrabold text-navy-deep">
          MJ0{index + 1}
        </span>
        <div className="mt-1 flex items-baseline gap-3">
          <h3 className="text-xl font-extrabold">
            {semester.year}학년 {semester.semester}학기
          </h3>
          <span className="ml-auto font-mono text-sm tabular-nums text-sky">{credits}학점</span>
        </div>
      </header>

      <ul className="flex flex-col gap-1.5 px-5 py-4">
        {semester.courses.map((c) => (
          <li key={c.course_id} className="flex flex-wrap items-baseline gap-x-2 text-sm">
            <span className="font-semibold">{c.name}</span>
            <span className="font-mono text-xs tabular-nums text-steel">{c.credits}</span>
            {c.talent_type === targetJob && (
              <span className="rounded bg-gold/20 px-1.5 py-0.5 text-xs font-bold text-navy">
                ★ 목표직무
              </span>
            )}
            {c.field_based && (
              <span className="rounded bg-sky-soft px-1.5 py-0.5 text-xs text-navy">현장중심</span>
            )}
          </li>
        ))}
      </ul>

      {semester.certificates?.length > 0 && (
        <div className="mx-5 mb-4 rounded-xl bg-sky-soft px-3.5 py-3 inset-ring inset-ring-edge">
          {semester.certificates.map((c) => (
            <p key={certName(c)} className="text-sm text-navy">
              🎫 <b>{certName(c)}</b>
              {certTip(c) && <span className="block text-xs text-ink-2">{certTip(c)}</span>}
            </p>
          ))}
          {semester.notes && <p className="mt-1 text-xs text-ink-2">{semester.notes}</p>}
        </div>
      )}
      {!semester.certificates?.length && semester.notes && (
        <p className="mx-5 mb-4 text-xs text-ink-2">{semester.notes}</p>
      )}

      <div className="mt-auto border-t border-edge px-5 py-3 text-right">
        {isLast ? (
          <button
            onClick={onGraduate}
            className="rounded-xl bg-navy px-5 py-2.5 font-bold text-white transition-[background-color,scale] duration-200 hover:bg-navy-deep active:scale-[0.96] focus-visible:outline-2 focus-visible:outline-gold"
          >
            졸업 →
          </button>
        ) : (
          <button
            onClick={onNext}
            className="rounded-lg px-4 py-2 font-bold text-navy transition-[background-color,scale] duration-150 hover:bg-sky-soft active:scale-[0.96] focus-visible:outline-2 focus-visible:outline-gold"
          >
            다음 학기 →
          </button>
        )}
      </div>
    </aside>
  );
}
