import { useNavigate } from "react-router-dom";
import { useApp } from "../store";
import { JOBS } from "../lib/mock";

export default function Input() {
  const { input, setInput, generate, loading } = useApp();
  const navigate = useNavigate();

  async function onSubmit(e) {
    e.preventDefault();
    await generate();
    navigate("/app/plan");
  }

  const field = "w-full rounded-lg border border-edge bg-white px-3 py-2.5 text-ink";
  const label = "mb-1.5 block font-mono text-xs tracking-[0.1em] text-steel";

  return (
    <form onSubmit={onSubmit} className="flex max-w-xl flex-col gap-5">
      <h2 className="text-2xl font-extrabold tracking-tight">로드맵 만들기</h2>

      <div>
        <label className={label} htmlFor="dept">학과</label>
        <select
          id="dept"
          className={field}
          value={input.deptId}
          onChange={(e) => setInput({ ...input, deptId: e.target.value })}
        >
          <option value="itc">정보통신공학과</option>
        </select>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className={label} htmlFor="year">학년</label>
          <select
            id="year"
            className={field}
            value={input.year}
            onChange={(e) => setInput({ ...input, year: Number(e.target.value) })}
          >
            {[1, 2, 3].map((y) => <option key={y} value={y}>{y}학년</option>)}
          </select>
        </div>
        <div>
          <label className={label} htmlFor="sem">학기</label>
          <select
            id="sem"
            className={field}
            value={input.semester}
            onChange={(e) => setInput({ ...input, semester: Number(e.target.value) })}
          >
            {[1, 2].map((s) => <option key={s} value={s}>{s}학기</option>)}
          </select>
        </div>
      </div>

      <div>
        <label className={label} htmlFor="job">목표 직무 (행선지)</label>
        <select
          id="job"
          className={field}
          value={input.targetJob}
          onChange={(e) => setInput({ ...input, targetJob: e.target.value })}
        >
          {JOBS.map((j) => <option key={j} value={j}>{j}</option>)}
        </select>
      </div>

      {/* TODO: 이수 과목 체크 — data/courses.json(P1) 도착 후 course_id 기반으로 */}
      <p className="rounded-lg border border-dashed border-edge bg-sky-soft/60 p-3 font-mono text-xs text-steel">
        이수 과목 체크는 학과 교육과정 데이터 연동 후 추가됩니다. 지금은 1학년 1학기 기준으로
        전체 노선을 생성합니다.
      </p>

      <button
        type="submit"
        disabled={loading}
        className="self-start rounded-xl bg-navy px-6 py-3 font-bold text-white transition-[background-color,scale] duration-200 hover:bg-navy-deep active:scale-[0.96] disabled:opacity-60"
      >
        {loading ? "노선 계산 중…" : "출발 →"}
      </button>
    </form>
  );
}
