/* v2 메인 — 2D 트랙 스튜디오 (docs/frontend/DESIGN.md).
   P0 골격. P1에서 TrackCanvas·SemesterPanel·ValidationBar가 들어온다. */
export default function RoadmapStudio() {
  return (
    <section className="flex flex-col gap-3 py-10">
      <h2 className="text-2xl font-extrabold tracking-tight">로드맵 스튜디오</h2>
      <p className="font-mono text-xs text-steel">P1 트랙 캔버스 작업 중 — v1은 /app/input에 그대로 있습니다.</p>
    </section>
  );
}
