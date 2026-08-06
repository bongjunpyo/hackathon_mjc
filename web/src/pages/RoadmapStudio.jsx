import { useState } from "react";
import TrackCanvas from "../components/track/TrackCanvas";
import SemesterPanel from "../components/track/SemesterPanel";
import ValidationBar from "../components/track/ValidationBar";
import demo from "../fixtures/roadmap-demo.json";

/* v2 메인 — 2D 트랙 스튜디오 (DESIGN §2).
   P1: 픽스처(실측 LLM 응답)로 트랙·패널·배지를 그린다. 컨트롤 바 + API 연동은 P3.
   캐릭터 위치(cursor)는 "보고 있는 학기" — 이동은 API를 다시 부르지 않는다. */
export default function RoadmapStudio() {
  const roadmap = demo;
  const semesters = roadmap.semesters;
  const targetJob = "시스템관리·운용엔지니어"; // P3에서 컨트롤 바 상태로 대체
  const goalNode = semesters.length + 1;

  const [cursor, setCursor] = useState(0);

  // 노드 i → 학기: 1..n. 입학(0)·종착(n+1)은 패널을 닫는다
  const semIndex = cursor >= 1 && cursor <= semesters.length ? cursor - 1 : null;

  return (
    <section className="flex flex-col gap-4 py-6">
      <div className="flex items-baseline justify-between gap-3">
        <h2 className="text-2xl font-extrabold tracking-tight">
          {targetJob}<span className="text-ink-2">까지의 노선</span>
        </h2>
        <span className="font-mono text-xs text-steel">
          역을 누르면 캐릭터가 걸어가고 학기 상세가 열립니다
        </span>
      </div>

      <div className="grid gap-4 lg:grid-cols-[1fr_340px]">
        <TrackCanvas
          semesters={semesters}
          targetJob={targetJob}
          cursor={cursor}
          passed={roadmap.validation?.passed}
          shortfallRules={roadmap.validation?.passed ? [] : roadmap.validation?.details}
          onSelect={setCursor}
        />
        {semIndex != null && (
          <SemesterPanel
            semester={semesters[semIndex]}
            index={semIndex}
            targetJob={targetJob}
            isLast={semIndex === semesters.length - 1}
            onNext={() => setCursor(cursor + 1)}
            onGraduate={() => setCursor(goalNode)}
          />
        )}
      </div>

      <ValidationBar validation={roadmap.validation} engine={roadmap.engine} />
    </section>
  );
}
