import { useState } from "react";
import { Link } from "react-router-dom";
import { DEPTS } from "../lib/depts";
import { CURRICULA } from "../lib/curricula";

/* 학과 탐색 (DESIGN §4) — 전부 번들 데이터, 서버 0.
   컨트롤은 이름 검색 + 학제 필터 둘만 — 계열 분류 데이터가 없으므로 지어내지 않는다. */
export default function Explore() {
  const [q, setQ] = useState("");
  const [years, setYears] = useState(0); // 0=전체

  const list = DEPTS.filter(
    (d) => (!years || d.years === years) && (!q || d.name.includes(q.trim())),
  );

  const chip = (active) =>
    `rounded-lg px-3 py-1.5 text-sm font-bold transition-[background-color,scale] duration-150 active:scale-[0.96] focus-visible:outline-2 focus-visible:outline-gold ${
      active ? "bg-navy text-white" : "text-ink-2 hover:bg-sky-soft"
    }`;

  return (
    <section className="flex flex-col gap-5 py-6">
      <div>
        <h2 className="text-2xl font-extrabold tracking-tight">학과 탐색</h2>
        <p className="mt-1 text-ink-2">
          명지전문대학 {DEPTS.length}개 학과 — 어느 학과에서 어떤 직무로 갈 수 있는지 보고,
          바로 로드맵을 그려보세요.
        </p>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <input
          type="search"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="학과 이름 검색"
          aria-label="학과 이름 검색"
          className="min-w-56 flex-1 rounded-lg border border-edge bg-white px-3 py-2 text-sm text-ink focus-visible:outline-2 focus-visible:outline-gold sm:max-w-72"
        />
        {[[0, "전체"], [2, "2년제"], [3, "3년제"]].map(([v, label]) => (
          <button key={v} className={chip(years === v)} onClick={() => setYears(v)}>
            {label}
          </button>
        ))}
        <span className="ml-auto font-mono text-xs tabular-nums text-steel">{list.length}개</span>
      </div>

      <ul className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {list.map((d) => {
          const certs = CURRICULA[d.id]?.cert?.length ?? 0;
          return (
            <li key={d.id}>
              <Link
                to={`/app/explore/${d.id}`}
                className="flex h-full flex-col gap-2 rounded-xl border border-edge bg-white p-4 transition-[border-color,box-shadow,scale] duration-150 hover:border-navy hover:shadow-[0_6px_20px_rgba(0,45,101,.10)] active:scale-[0.98] focus-visible:outline-2 focus-visible:outline-gold"
              >
                <div className="flex items-baseline justify-between gap-2">
                  <b className="text-navy">{d.name}</b>
                  <span className="rounded bg-sky-soft px-1.5 py-0.5 font-mono text-xs font-bold text-navy">
                    {d.years}년제
                  </span>
                </div>
                {d.careers.length > 0 && (
                  <p className="text-sm text-ink-2">
                    {d.careers.slice(0, 2).join(" · ")}
                    {d.careers.length > 2 && ` 외 ${d.careers.length - 2}`}
                  </p>
                )}
                <p className="mt-auto font-mono text-xs tabular-nums text-steel">
                  전공 {d.majorCredits}학점{certs > 0 && ` · 자격증 ${certs}종`}
                </p>
              </Link>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
