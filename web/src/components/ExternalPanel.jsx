/* 외부 시스템 안내 패널 — 누르기 전에 무엇이 있는지 먼저 보여주고, 이동은 선택으로 둔다.
   링크를 그냥 걸면 로그인 벽(또는 조용한 리다이렉트)에 부딪혀 시연 흐름이 끊긴다. */
export default function ExternalPanel({ info }) {
  if (!info) return null;

  return (
    <div className="rounded-xl bg-sky-soft px-4 py-3.5 inset-ring inset-ring-edge">
      <div className="flex items-baseline gap-2">
        {/* flex 자식이라 폭이 모자라면 배지부터 줄어든다 — 340px 패널에서 '자격/증'으로
           접혔다 (이슈 #82). 라벨은 쪼개질 값이 아니므로 줄바꿈·수축을 둘 다 막는다 */}
        <span className="shrink-0 whitespace-nowrap rounded bg-navy px-1.5 py-0.5 font-mono text-[0.625rem] font-bold text-white">
          {info.kind}
        </span>
        <b className="text-navy">{info.title}</b>
      </div>

      <dl className="mt-2.5 grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-sm">
        {info.facts.map(([k, v]) => (
          <div key={k} className="contents">
            <dt className="font-mono text-xs text-steel">{k}</dt>
            <dd className="text-ink-2">{v}</dd>
          </div>
        ))}
      </dl>

      {info.caution && (
        <p className="mt-2.5 border-t border-edge pt-2 text-xs text-steel">⚠ {info.caution}</p>
      )}

      <a
        href={info.href}
        target="_blank"
        rel="noreferrer"
        className="mt-3 inline-flex items-center gap-1.5 rounded-lg bg-navy px-4 py-2 text-sm font-bold text-white transition-[background-color,scale] duration-200 hover:bg-navy-deep active:scale-[0.96] focus-visible:outline-2 focus-visible:outline-gold"
      >
        {info.linkLabel} ↗
      </a>
    </div>
  );
}
