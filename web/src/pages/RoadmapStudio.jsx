import { useEffect, useRef, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import ControlBar from "../components/track/ControlBar";
import TrackCanvas from "../components/track/TrackCanvas";
import SemesterPanel from "../components/track/SemesterPanel";
import ValidationBar from "../components/track/ValidationBar";
import Walker from "../components/track/Walker";
import { postRoadmap } from "../lib/api";
import { DEPT_BY_ID, realJobs } from "../lib/depts";
import { useApp } from "../store";
import demo from "../fixtures/roadmap-demo.json";

/* v2 메인 — 2D 트랙 스튜디오 (DESIGN §2). 상태 5종:
   INIT(예시 트랙 흐림) → GENERATING(제자리걸음+문구) → READY | PARTIAL | ERROR.
   캐릭터 위치(cursor)는 "보고 있는 학기" — 이동은 API를 다시 부르지 않는다. */

const GEN_STEPS = [
  "교육과정표에서 후보 과목을 고르는 중…",
  "AI가 학기별로 과목을 배치하는 중…",
  "졸업요건 검증기로 확인하는 중…",
  "미달이면 사유를 실어 다시 짜게 하는 중…",
];

export default function RoadmapStudio() {
  // 랜딩(행선지)·학과 상세(학과)가 선택을 실어 보낸다 (DESIGN §4)
  const handoff = useLocation().state ?? {};
  const [input, setInput] = useState(() => {
    const deptId = handoff.deptId ?? "itc";
    const dept = DEPT_BY_ID[deptId];
    return {
      deptId,
      year: 1,
      semester: 1,
      completedCourses: [],
      targetJob: handoff.targetJob ?? realJobs([...(dept?.careers ?? []), ...(dept?.promoted ?? [])])[0] ?? "",
    };
  });
  const [phase, setPhase] = useState("INIT");
  const [roadmap, setRoadmap] = useState(null);
  const [error, setError] = useState(null);
  const [cursor, setCursor] = useState(0);
  const jobRef = useRef(input.targetJob); // 생성 시점의 직무 — 컨트롤을 바꿔도 트랙은 그대로
  const { setRoadmap: shareRoadmap } = useApp(); // 3D 걷기 모드(/app/walk)와 공유
  const navigate = useNavigate();

  async function generate() {
    setPhase("GENERATING");
    setError(null);
    jobRef.current = input.targetJob;
    try {
      const data = await postRoadmap(input, { strict: true });
      setRoadmap(data);
      setCursor(data.semesters.length > 0 ? 1 : 0); // 입학 → 첫 학기로 걸어간다
      setPhase(data.validation?.passed ? "READY" : "PARTIAL");
    } catch (err) {
      setError(err?.message ?? "서버에 연결할 수 없습니다");
      setPhase("ERROR");
    }
  }

  const shown = phase === "READY" || phase === "PARTIAL" ? roadmap : demo;
  const semesters = shown.semesters;
  const targetJob = phase === "INIT" || phase === "GENERATING" ? "목표 직무" : jobRef.current;
  const dimmed = phase === "INIT" || phase === "GENERATING" || phase === "ERROR";
  const semIndex = !dimmed && cursor >= 1 && cursor <= semesters.length ? cursor - 1 : null;

  return (
    <section className="flex flex-col gap-4 py-6">
      <ControlBar
        value={input}
        onChange={setInput}
        onGenerate={generate}
        loading={phase === "GENERATING"}
      />

      {/* 좌: 트랙+검증바 묶음 · 우: 패널. 바를 그리드 밖에 두면 패널 높이만큼
         트랙과 바 사이가 벌어진다 — 바는 트랙 바로 아래 붙어야 한 눈에 읽힌다 */}
      <div className="grid items-start gap-4 lg:grid-cols-[1fr_340px]">
        <div className="flex flex-col gap-3">
        <div className="relative">
          <div className={dimmed ? "opacity-35 blur-[2px] transition-[opacity,filter] duration-500" : "transition-[opacity,filter] duration-500"}>
            <TrackCanvas
              semesters={semesters}
              targetJob={targetJob}
              cursor={dimmed ? 0 : cursor}
              passed={!dimmed && shown.validation?.passed}
              shortfallRules={phase === "PARTIAL" ? shown.validation?.details : []}
              onSelect={dimmed ? () => {} : setCursor}
            />
          </div>

          {phase === "INIT" && (
            <Overlay>
              <p className="max-w-[36ch] text-balance text-center text-lg font-bold text-navy">
                학과와 목표 직무를 고르면 여기에 당신의 노선이 그려집니다
              </p>
            </Overlay>
          )}
          {phase === "GENERATING" && <Generating />}
          {phase === "ERROR" && (
            <Overlay>
              <p className="font-bold text-navy">로드맵을 만들지 못했습니다</p>
              <p className="max-w-[44ch] text-center text-sm text-ink-2">{error}</p>
              <button
                onClick={generate}
                className="rounded-xl bg-navy px-5 py-2 font-bold text-white transition-[background-color,scale] duration-200 hover:bg-navy-deep active:scale-[0.96]"
              >
                다시 시도
              </button>
            </Overlay>
          )}
        </div>

        {/* 미달 사유 — 검증기가 잡아냈다는 증거 화면 (DESIGN §2.5 PARTIAL) */}
        {phase === "PARTIAL" && shown.validation?.details?.length > 0 && (
          <div className="flex flex-col gap-1.5 rounded-xl border-2 border-gold bg-gold/15 px-4 py-3">
            <b className="text-navy">검증기가 미달을 잡았습니다 — 재생성 {shown.attempts ?? 3}회 후에도 남은 항목</b>
            {shown.validation.details.map((d) => (
              <p key={d.rule} className="text-sm text-ink-2">
                ✗ {d.label} {d.actual}/{d.required} → {d.fix}
              </p>
            ))}
          </div>
        )}

        {!dimmed && (
          <div className="flex flex-wrap items-center gap-3">
            <div className="flex-1">
              <ValidationBar validation={shown.validation} engine={shown.engine} />
            </div>
            {/* 2D=편집 모드, 3D=감상 모드. 같은 데이터·같은 캐릭터·같은 색이다 */}
            <button
              onClick={() => {
                shareRoadmap({ ...shown, target_job: jobRef.current });
                navigate("/app/walk");
              }}
              className="rounded-xl border-2 border-navy px-4 py-2.5 font-bold text-navy transition-[background-color,scale] duration-200 hover:bg-sky-soft active:scale-[0.96] focus-visible:outline-2 focus-visible:outline-gold"
            >
              3D로 걸어보기 →
            </button>
          </div>
        )}

        {phase === "READY" && shown.job_match?.note && (
          <p className="rounded-lg border border-dashed border-edge p-3 text-xs text-steel">
            ⚠ {shown.job_match.note}
          </p>
        )}
        </div>

        {semIndex != null && (
          <SemesterPanel
            semester={semesters[semIndex]}
            index={semIndex}
            targetJob={jobRef.current}
            isLast={semIndex === semesters.length - 1}
            onNext={() => setCursor(cursor + 1)}
            onGraduate={() => setCursor(semesters.length + 1)}
          />
        )}
      </div>

    </section>
  );
}

function Overlay({ children }) {
  return (
    <div className="absolute inset-0 grid place-items-center">
      <div className="flex flex-col items-center gap-3 rounded-2xl bg-white/90 px-8 py-6 shadow-[0_8px_30px_rgba(0,26,61,.14)] backdrop-blur-sm">
        {children}
      </div>
    </div>
  );
}

/* 27초 침묵을 연출로 — 제자리걸음 + 단계 문구 순환 (DESIGN §2.5) */
function Generating() {
  const [step, setStep] = useState(0);
  useEffect(() => {
    const id = setInterval(() => setStep((s) => (s + 1) % GEN_STEPS.length), 3200);
    return () => clearInterval(id);
  }, []);
  return (
    <Overlay>
      <Walker className="walking" style={{ position: "static", translate: "none" }} />
      <p className="font-mono text-sm text-navy" aria-live="polite">{GEN_STEPS[step]}</p>
      <p className="text-xs text-steel">보통 30초 안에 끝납니다 — 검증에 걸리면 최대 3회 다시 짭니다</p>
    </Overlay>
  );
}
