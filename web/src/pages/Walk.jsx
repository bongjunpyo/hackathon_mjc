import { useState } from "react";
import { Link, Navigate } from "react-router-dom";
import Corridor from "../components/Corridor";
import SemesterDetail from "../components/SemesterDetail";
import { useApp } from "../store";

/* 3D 걷기 모드 — 스튜디오에서 생성한 로드맵을 복도로 걸어본다 (읽기 전용).
   편집·재생성은 전부 2D 스튜디오 몫. 여기는 랜딩의 복도를 데이터만 바꿔 재사용한다.
   Corridor가 window 스크롤 기반이라 오버레이가 아니라 라우트다. */
export default function Walk() {
  const { roadmap } = useApp();
  const [detailIndex, setDetailIndex] = useState(null);

  if (!roadmap?.semesters?.length) return <Navigate to="/app/roadmap" replace />;

  const job = roadmap.target_job ?? "목표 직무";
  const semesters = roadmap.semesters.map((s) => ({
    ...s,
    credits: s.credits ?? s.courses.reduce((a, c) => a + (c.credits ?? 0), 0),
    name: `${s.year}학년 ${s.semester}학기`,
    en: `YEAR ${s.year} · SEM ${s.semester}`,
  }));
  const totalCredits = semesters.reduce((a, s) => a + s.credits, 0);
  const passed = roadmap.validation?.passed ?? false;

  return (
    <>
      <div className="flex items-baseline justify-between gap-3 py-4">
        <h2 className="text-xl font-extrabold tracking-tight">
          {job}<span className="text-ink-2"> — 3D 걷기</span>
        </h2>
        <Link
          to="/app/roadmap"
          className="rounded-lg px-3 py-1.5 text-sm font-bold text-navy transition-[background-color,scale] duration-150 hover:bg-sky-soft active:scale-[0.96] focus-visible:outline-2 focus-visible:outline-gold"
        >
          ← 스튜디오로
        </Link>
      </div>

      <div className="relative left-1/2 w-screen -translate-x-1/2">
        <Corridor
          semesters={semesters}
          targetJob={job}
          stats={`${semesters.length}학기 · ${totalCredits}학점 · ${roadmap.engine === "llm" ? "AI 생성" : "실데이터 추천 엔진"}`}
          passed={passed}
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
