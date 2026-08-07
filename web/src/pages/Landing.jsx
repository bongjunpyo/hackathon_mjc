import { Link, useNavigate } from "react-router-dom";
import Walker from "../components/track/Walker";
import { useApp } from "../store";
import { DEPT_BY_ID, DEPTS } from "../lib/depts";

/* 랜딩 — 히어로(카피+CTA / 트랙 프리뷰) → 3스텝 → 문제 한 줄.
   섹션 배열은 팀 시안, 색·폰트는 브랜드 토큰 그대로.

   3D 복도는 여기 두지 않는다 — 로드맵을 만들기 전에는 걸어볼 내용이 없다.
   생성 후 스튜디오의 "3D로 걸어보기"(/app/walk)에서 자기 로드맵을 걷는다. */

const STEPS = [
  {
    n: "STEP 1",
    title: "학과·직무 선택",
    body: "34개 전 학과. 직무를 아직 못 정했어도 학과 데이터로 추천받을 수 있습니다",
  },
  {
    n: "STEP 2",
    title: "길을 자동으로 놓아 드립니다",
    body: "학기별 수강 계획 + 자격증 준비 시점 + 현장실습 타이밍",
  },
  {
    n: "STEP 3",
    title: "졸업까지 확인합니다",
    body: "졸업 학점이 모자라면 스스로 다시 짭니다 — 끝까지 졸업이 되는 계획만 보여 드립니다",
  },
];

/* 트랙 프리뷰 — 스튜디오 트랙의 축소판. 걸어온 구간은 gold 유도선, 종착은 ★ */
function TrackPreview() {
  const nodes = [
    { x: 90, label: "입학", done: true },
    { x: 290, label: "1-1", done: true },
    { x: 490, label: "2-1" },
    { x: 690, label: "3-1" },
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
  const navigate = useNavigate();
  const dept = DEPT_BY_ID[input.deptId] ?? DEPTS[0];

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
            전문대 2·3년, 되돌아올 시간은 없습니다. 어떤 과목을 언제 듣고 자격증은 언제
            준비할지 — 학기별 계획을 자동으로 짜 주고, <b className="text-navy">졸업이 되는
            계획인지까지</b> 확인해 드립니다.
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

      {/* 3D 걷기 안내 — 걷는 건 로드맵을 만든 뒤다 */}
      <section className="mb-14 flex flex-wrap items-center gap-4 rounded-2xl bg-sky-soft px-8 py-6 inset-ring inset-ring-edge">
        <Walker className="walking shrink-0" style={{ width: 52, height: 84 }} />
        <p className="text-lg text-ink-2 text-pretty">
          로드맵을 만들면 <b className="text-navy">그 길을 직접 걸어볼 수 있습니다</b>. 행선판을
          누르면 그 학기의 추천 이유가 열립니다.
        </p>
      </section>

    </>
  );
}
