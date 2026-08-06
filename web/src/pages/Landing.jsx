import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import Corridor from "../components/Corridor";
import SemesterDetail from "../components/SemesterDetail";
import Walker from "../components/track/Walker";
import { useApp } from "../store";
import { DEPT_BY_ID, DEPTS } from "../lib/depts";
import { pathFor } from "../lib/curricula";

/* 랜딩 — 히어로(카피+CTA / 트랙 프리뷰) → 3스텝 → 문제 한 줄 → 3D 복도.
   섹션 배열은 팀 시안, 색·폰트는 브랜드 토큰 그대로.
   복도에 쓰는 건 교육과정표의 표준 이수 경로 — 개인화는 /app/roadmap 이후. */

const STEPS = [
  {
    n: "STEP 1",
    title: "학과·직무 선택",
    body: "34개 전 학과. 학교가 교육과정표에 직접 붙인 직무 라벨 그대로 씁니다",
  },
  {
    n: "STEP 2",
    title: "엔진이 길을 놓습니다",
    body: "학기별 수강 계획 + 자격증 준비 시점 + 현장실습 타이밍",
  },
  {
    n: "STEP 3",
    title: "검증기가 확인합니다",
    body: "졸업요건 미달이면 스스로 다시 짭니다 — LLM 없는 순수 규칙 코드",
  },
];

/* 트랙 프리뷰 — 스튜디오 트랙의 축소판. 걸어온 구간은 gold 유도선, 종착은 ★ */
function TrackPreview() {
  const nodes = [
    { x: 90, label: "입학", done: true },
    { x: 290, label: "1-2", done: true },
    { x: 490, label: "2-1" },
    { x: 690, label: "3-2" },
  ];
  return (
    <div className="rounded-3xl bg-sky-soft p-8 inset-ring inset-ring-edge sm:p-10">
      <svg viewBox="0 0 880 230" className="w-full" role="img" aria-label="학기 트랙 미리보기">
        <path d="M 90 140 H 830" fill="none" stroke="var(--color-edge)" strokeWidth="16" strokeLinecap="round" />
        <path
          d="M 90 140 H 290"
          fill="none"
          stroke="color-mix(in srgb, var(--color-gold) 72%, #fff)"
          strokeWidth="16"
          strokeLinecap="round"
        />
        <path
          d="M 90 140 H 830"
          fill="none"
          stroke="color-mix(in srgb, var(--color-gold) 45%, #fff)"
          strokeWidth="6"
          strokeLinecap="round"
          strokeDasharray="0.1 26"
        />
        {nodes.map((n) => (
          <g key={n.label}>
            <circle
              cx={n.x}
              cy="140"
              r="26"
              fill="#fff"
              stroke={n.done ? "color-mix(in srgb, var(--color-navy) 40%, #fff)" : "var(--color-navy)"}
              strokeWidth="5"
            />
            {n.done && (
              <text x={n.x} y="149" textAnchor="middle" fontSize="24" fill="var(--color-navy)">
                ✓
              </text>
            )}
            <text x={n.x} y="196" textAnchor="middle" fontSize="25" fontWeight="700" fill="var(--color-ink)">
              {n.label}
            </text>
          </g>
        ))}
        <text x="830" y="162" textAnchor="middle" fontSize="76" fill="var(--color-gold)">
          ★
        </text>
        <text x="830" y="196" textAnchor="middle" fontSize="25" fontWeight="800" fill="var(--color-navy)">
          목표 직무
        </text>
      </svg>
    </div>
  );
}

export default function Landing() {
  const { input } = useApp();
  const [detailIndex, setDetailIndex] = useState(null);
  const navigate = useNavigate();

  const dept = DEPT_BY_ID[input.deptId] ?? DEPTS[0];
  const job = input.targetJob || dept.careers[0];
  const semesters = (pathFor(dept.id, job, dept.years) ?? []).map((s) => ({
    ...s,
    name: `${s.year}학년 ${s.semester}학기`,
    en: `YEAR ${s.year} · SEM ${s.semester}`,
  }));
  const totalCredits = semesters.reduce((a, s) => a + s.credits, 0);

  const cta =
    "rounded-2xl px-8 py-4 text-lg font-bold transition-[background-color,scale] duration-200 active:scale-[0.96] focus-visible:outline-2 focus-visible:outline-gold";

  return (
    <>
      {/* 히어로 */}
      <section className="grid items-center gap-10 py-14 lg:grid-cols-[1.2fr_1fr] lg:gap-12 lg:py-20">
        <div className="flex flex-col gap-6">
          <span className="font-mono text-sm tracking-[0.14em] text-steel">
            MYONGJI COLLEGE · 취업 로드맵 에이전트
          </span>
          {/* text-balance는 넣지 않는다 — br로 나눈 줄을 다시 쪼개 '그려집니/다'가 된다 */}
          <h1 className="text-[2.35rem] font-extrabold leading-[1.18] tracking-tight sm:text-[2.75rem] xl:text-[3.05rem]">
            직무를 고르면,
            <br />
            졸업까지의 <span className="mark-gold text-navy">길</span>이 그려집니다
          </h1>
          <p className="max-w-[46ch] text-xl leading-relaxed text-ink-2 text-pretty">
            전문대 3년, 되돌아올 시간은 없습니다. 학기별 수강 · 자격증 · 현장실습 타이밍을
            엔진이 짜고, <b className="text-navy">졸업요건 검증기</b>가 확인합니다.
          </p>
          <div className="flex flex-wrap gap-3">
            <button
              onClick={() => navigate("/app/roadmap", { state: { deptId: dept.id } })}
              className={`${cta} bg-navy text-white hover:bg-navy-deep`}
            >
              내 로드맵 그리기 →
            </button>
            <Link to="/app/explore" className={`${cta} border-2 border-navy text-navy hover:bg-sky-soft`}>
              학과 둘러보기
            </Link>
          </div>
        </div>
        <TrackPreview />
      </section>

      {/* 3스텝 */}
      <section className="grid gap-5 pb-14 md:grid-cols-3">
        {STEPS.map((s) => (
          <div key={s.n} className="flex flex-col gap-2.5 rounded-2xl border border-edge bg-white p-7">
            <span className="font-mono text-sm font-bold tracking-[0.1em] text-sky">{s.n}</span>
            <b className="text-2xl text-navy">{s.title}</b>
            <p className="text-lg leading-relaxed text-ink-2 text-pretty">{s.body}</p>
          </div>
        ))}
      </section>

      {/* 문제 한 줄 */}
      <section className="mb-14 rounded-2xl border-l-[6px] border-gold bg-white px-8 py-7">
        <p className="text-xl leading-relaxed text-ink text-pretty">
          지금 학생 손에 있는 건 <b className="text-navy">교육과정표 PDF 한 장</b>입니다. “이
          직무가 되려면 어느 학기에 뭘 듣고 자격증을 언제 따야 하는가”는 아무도 알려주지
          않습니다.
        </p>
      </section>

      {/* 3D 걷기 안내 */}
      <section className="flex flex-wrap items-center gap-4 pb-8">
        <Walker className="walking shrink-0" style={{ width: 52, height: 84 }} />
        <p className="text-lg text-ink-2 text-pretty">
          아래로 스크롤하면 이 노선을 <b className="text-navy">직접 걸어볼 수 있습니다</b>.
          행선판을 누르면 그 학기의 추천 이유가 열립니다.
        </p>
      </section>

      {/* 3D 복도 — 뷰포트 전체를 쓰도록 main의 좌우 여백을 벗어난다 */}
      <div className="relative left-1/2 w-screen -translate-x-1/2">
        <Corridor
          semesters={semesters}
          targetJob={job}
          stats={`${dept.years}년제 · ${semesters.length}학기 · ${totalCredits}학점`}
          onSelect={setDetailIndex}
        />
      </div>

      <SemesterDetail
        semester={detailIndex == null ? null : semesters[detailIndex]}
        index={detailIndex}
        onClose={() => setDetailIndex(null)}
      />
    </>
  );
}
