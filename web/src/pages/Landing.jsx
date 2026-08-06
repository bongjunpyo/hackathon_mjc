import { useState } from "react";
import { useNavigate } from "react-router-dom";
import Corridor from "../components/Corridor";
import SemesterDetail from "../components/SemesterDetail";
import { useApp } from "../store";
import { DEPT_BY_ID, DEPTS } from "../lib/depts";
import { pathFor } from "../lib/curricula";

/* 랜딩 = 행선판 복도. 스크롤로 노선을 걸어 목표 직무 게이트에 도착한다.
   여기 쓰는 건 교육과정표의 표준 이수 경로 — 개인화(이수분 반영)는 /app/input 이후. */
export default function Landing() {
  const { input, setInput } = useApp();
  const [job, setJob] = useState(input.targetJob);
  const [detailIndex, setDetailIndex] = useState(null);
  const navigate = useNavigate();

  const dept = DEPT_BY_ID[input.deptId] ?? DEPTS[0];
  const semesters = (pathFor(dept.id, job, dept.years) ?? []).map((s) => ({
    ...s,
    name: `${s.year}학년 ${s.semester}학기`,
    en: `YEAR ${s.year} · SEM ${s.semester}`,
  }));

  const totalCredits = semesters.reduce((a, s) => a + s.credits, 0);

  function start() {
    setInput({ ...input, targetJob: job });
    navigate("/app/input");
  }

  return (
    <>
      <section className="flex flex-col gap-7 py-12">
        <span className="font-mono text-xs tracking-[0.14em] text-steel">
          MYONGJI COLLEGE · 취업 로드맵 에이전트
        </span>
        <h1 className="max-w-[16ch] text-4xl font-extrabold leading-tight tracking-tight text-balance sm:text-5xl">
          목표 직무를 고르면,{" "}
          <span className="mark-gold text-navy">졸업까지의 노선</span>이 그려집니다
        </h1>
        <p className="max-w-[56ch] text-ink-2">
          전문대 3년은 되돌아올 시간이 없는 편도 노선입니다. 어느 학기에 무엇을 듣고 자격증을
          언제 딸지 — 목표 직무에서 역산한 학기별 로드맵을 졸업요건 검증기가 보증합니다.
        </p>

        {/* 승차권 */}
        <div className="flex max-w-2xl flex-wrap items-stretch overflow-hidden rounded-xl border border-edge bg-white shadow-[0_10px_34px_rgba(0,45,101,0.10)]">
          <div className="min-w-40 flex-1 border-r border-dashed border-edge px-5 py-3.5">
            <span className="mb-1 block font-mono text-xs tracking-[0.1em] text-steel">학과</span>
            <b className="text-[1.0625rem]">{dept.name}</b>
          </div>
          <div className="min-w-40 flex-1 border-r border-dashed border-edge px-5 py-3.5">
            <span className="mb-1 block font-mono text-xs tracking-[0.1em] text-steel">현재</span>
            <b className="text-[1.0625rem]">1학년 1학기</b>
          </div>
          <div className="min-w-40 flex-1 px-5 py-3.5">
            <label
              htmlFor="landing-job"
              className="mb-1 block font-mono text-xs tracking-[0.1em] text-steel"
            >
              행선지
            </label>
            <select
              id="landing-job"
              value={job}
              onChange={(e) => setJob(e.target.value)}
              className="w-full cursor-pointer bg-transparent text-[1.0625rem] font-bold text-ink focus-visible:outline-2 focus-visible:outline-gold"
            >
              {dept.careers.map((j) => (
                <option key={j}>{j}</option>
              ))}
            </select>
          </div>
          <button
            onClick={start}
            className="grid place-items-center bg-navy px-7 font-bold text-white transition-[background-color,scale] duration-200 hover:bg-navy-deep active:scale-[0.96]"
          >
            출발 →
          </button>
        </div>

        <p className="font-mono text-xs text-steel">
          아래로 스크롤하면 이 노선을 직접 걸어볼 수 있습니다. 행선판을 누르면 그 학기의 추천
          이유가 열립니다.
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
