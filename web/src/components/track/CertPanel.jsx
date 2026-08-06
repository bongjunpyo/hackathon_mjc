import ExternalPanel from "../ExternalPanel";
import { certExternal, certName, certTip } from "../../lib/external";

/* 자격증 전용 패널 — 분기(동그라미) 도착 시 열린다.
   학기 패널(navy·전공 추천)과 역할이 다르므로 gold 문법으로 가른다.
   과목 얘기는 여기 없다 — 과목은 역을 눌러 학기 패널에서 본다. */
export default function CertPanel({ semester, index, onCourses }) {
  if (!semester?.certificates?.length) return null;
  const names = semester.certificates.map(certName).filter(Boolean);
  const qnet = {
    ...certExternal(names[0]),
    facts: [["찾을 종목", names.join(" · ")], ...certExternal(names[0]).facts.slice(1)],
  };

  return (
    <aside className="flex flex-col overflow-hidden rounded-2xl bg-white shadow-[0_3px_8px_rgba(0,26,61,.12),0_18px_44px_rgba(0,26,61,.16)]">
      <header className="border-b-[5px] border-navy bg-gold px-5 pb-3.5 pt-4 text-navy-deep">
        <span className="inline-flex h-[24px] items-center rounded-full bg-navy px-2.5 font-mono text-xs font-extrabold text-gold">
          MJ0{index + 1} 분기
        </span>
        <h3 className="mt-1 text-xl font-extrabold">
          🎫 자격증 <span className="font-mono text-base tabular-nums">{names.length}종</span>
        </h3>
        <p className="font-mono text-xs opacity-70">
          {semester.year}학년 {semester.semester}학기에 준비
        </p>
      </header>

      <ul className="flex flex-col gap-1.5 px-4 py-4 text-sm">
        {semester.certificates.map((c) => (
          <li key={certName(c)} className="rounded-lg border border-gold/60 bg-gold/10 px-3 py-2">
            <b className="text-navy">{certName(c)}</b>
            {certTip(c) && <span className="block text-xs text-ink-2">{certTip(c)}</span>}
          </li>
        ))}
      </ul>

      {semester.notes && (
        <p className="mx-4 mb-3 rounded-xl bg-sky-soft px-3.5 py-3 text-sm text-ink-2 inset-ring inset-ring-edge">
          💡 {semester.notes}
        </p>
      )}

      <div className="mx-4 mb-4">
        <ExternalPanel info={qnet} />
      </div>

      <div className="mt-auto border-t border-edge px-5 py-3 text-right">
        <button
          onClick={onCourses}
          className="rounded-lg px-4 py-2 font-bold text-navy transition-[background-color,scale] duration-150 hover:bg-sky-soft active:scale-[0.96] focus-visible:outline-2 focus-visible:outline-gold"
        >
          이 학기 과목 보기 →
        </button>
      </div>
    </aside>
  );
}
