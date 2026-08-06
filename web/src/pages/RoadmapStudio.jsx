import { useEffect, useRef, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import ControlBar, { UNDECIDED } from "../components/track/ControlBar";
import TrackCanvas from "../components/track/TrackCanvas";
import SemesterPanel from "../components/track/SemesterPanel";
import CertPanel from "../components/track/CertPanel";
import ValidationBar from "../components/track/ValidationBar";
import Walker from "../components/track/Walker";
import { postRoadmap } from "../lib/api";
import { DEPT_BY_ID, realJobs } from "../lib/depts";
import { bestJob } from "../lib/jobmatch";
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
  const [input, setInput] = useState(() => ({
    // 예시를 미리 골라 두지 않는다 — 고른 것처럼 보이면 학생이 안 바꾸고 생성한다
    deptId: handoff.deptId ?? "",
    year: "",
    semester: 1,
    completedCourses: [],
    jobChoice: handoff.targetJob ?? "",
    targetJob: handoff.targetJob ?? "",
  }));
  const [phase, setPhase] = useState("INIT");
  const [roadmap, setRoadmap] = useState(null);
  const [error, setError] = useState(null);
  const [cursor, setCursor] = useState(0);
  const [mapNote, setMapNote] = useState(null); // 타이핑 직무 → 라벨 매핑 안내
  // 패널은 캐릭터가 **도착한 뒤** 연다 — 클릭 즉시 열리면 걷기가 장식이 된다
  const [arrived, setArrived] = useState(0);
  const jobRef = useRef(input.targetJob); // 생성 시점의 직무 — 컨트롤을 바꿔도 트랙은 그대로
  const { setRoadmap: shareRoadmap } = useApp(); // 3D 걷기 모드(/app/walk)와 공유
  const navigate = useNavigate();

  async function generate(override) {
    setPhase("GENERATING");
    setError(null);
    setMapNote(null);

    /* 타이핑한 직무는 서버 목록의 정확한 값으로 옮겨 보낸다 (서버는 목록 밖 400).
       대응이 없으면 직무 미정 모드로 — 서버가 배정 학점 기준으로 추천한다. */
    const undecided = input.jobChoice === UNDECIDED && !override?.targetJob;
    const typed = undecided ? "" : (override?.targetJob ?? input.targetJob).trim();
    const dept = DEPT_BY_ID[input.deptId];
    const jobs = realJobs([...(dept?.careers ?? []), ...(dept?.promoted ?? [])]);
    let sendJob = typed;
    if (typed && !jobs.includes(typed)) {
      const matched = bestJob(typed, jobs);
      if (matched) {
        sendJob = matched;
        setMapNote(`입력하신 '${typed}' → 가장 가까운 교육과정 라벨 '${matched}'로 역산했습니다`);
      } else {
        sendJob = "";
        setMapNote(`'${typed}'에 대응하는 이 학과 라벨이 없습니다 — 배정 학점 기준 추천으로 그렸습니다`);
      }
    }

    jobRef.current = sendJob || "추천 직무";
    try {
      const data = await postRoadmap({ ...input, targetJob: sendJob }, { strict: true });
      setRoadmap(data);
      if (data.target_job) jobRef.current = data.target_job; // 미정 모드가 채택한 직무
      setArrived(0);
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
  // 도착 지점 기준 학기. i-0.5(분기)는 그 구간이 이끄는 학기 i다
  const semNode = Math.ceil(arrived);
  const semIndex =
    !dimmed && arrived === cursor && semNode >= 1 && semNode <= semesters.length
      ? semNode - 1
      : null;

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
              onArrive={setArrived}
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

        {/* 직무 미정·자유 입력의 결과를 숨기지 않는다 — 어떤 직무로 그렸고 왜인지 */}
        {!dimmed && mapNote && (
          <p className="rounded-lg border border-dashed border-edge bg-sky-soft/60 p-3 text-sm text-ink-2">
            {mapNote}
          </p>
        )}
        {!dimmed && shown.job_recommended && (
          <div className="flex flex-col gap-2 rounded-xl border-2 border-gold bg-gold/15 px-4 py-3">
            <b className="text-navy">
              직무 미정 — 배정 학점이 가장 많은 <span className="mark-gold">{shown.target_job}</span>로 그렸습니다
            </b>
            <div className="flex flex-wrap items-center gap-1.5">
              <span className="font-mono text-xs text-steel">다른 후보</span>
              {(shown.recommended_jobs ?? []).map((r) => (
                <button
                  key={r.job}
                  onClick={() => {
                    setInput((cur) => ({ ...cur, jobChoice: r.job, targetJob: r.job }));
                    generate({ targetJob: r.job });
                  }}
                  className={`rounded-lg border px-2.5 py-1 text-xs font-bold transition-[background-color,scale] duration-150 active:scale-[0.96] focus-visible:outline-2 focus-visible:outline-gold ${
                    r.job === shown.target_job
                      ? "border-navy bg-navy text-white"
                      : "border-edge bg-white text-navy hover:bg-sky-soft"
                  }`}
                >
                  {r.job} · {r.credits}학점
                </button>
              ))}
            </div>
          </div>
        )}
        {!dimmed && (
          <div className="flex flex-wrap items-center gap-3">
            <div className="flex-1">
              <ValidationBar validation={shown.validation} engine={shown.engine} attempts={shown.attempts} />
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

        {/* 역 도착(정수) = 학기별 전공 추천, 분기 도착(소수) = 자격증 — 내용이 다르다 */}
        {semIndex != null && (Number.isInteger(arrived) ? (
          <SemesterPanel
            semester={semesters[semIndex]}
            index={semIndex}
            targetJob={jobRef.current}
            isLast={semIndex === semesters.length - 1}
            onNext={() => setCursor(Math.floor(cursor) + 1)}
            onGraduate={() => setCursor(semesters.length + 1)}
            onCerts={
              semesters[semIndex].certificates?.length
                ? () => setCursor(semIndex + 0.5)
                : undefined
            }
          />
        ) : (
          <CertPanel
            semester={semesters[semIndex]}
            index={semIndex}
            onCourses={() => setCursor(semIndex + 1)}
          />
        ))}
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
