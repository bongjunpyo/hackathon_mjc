import { useNavigate } from "react-router-dom";
import { useApp } from "../store";
import { DEPTS, DEPT_BY_ID, creditGap, yearsOf } from "../lib/depts";

export default function Input() {
  const { input, setInput, generate, loading } = useApp();
  const navigate = useNavigate();

  const dept = DEPT_BY_ID[input.deptId] ?? DEPTS[0];
  const gap = creditGap(dept);

  /* 학과를 바꾸면 학년·직무가 그 학과 기준으로 다시 잡혀야 한다.
     3학년이던 학생이 2년제 학과를 고르면 없는 학년이 남는다. */
  function pickDept(deptId) {
    const next = DEPT_BY_ID[deptId];
    setInput({
      ...input,
      deptId,
      deptName: next.name,
      year: Math.min(input.year, next.years),
      targetJob: next.careers[0] ?? "",
    });
  }

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
          value={dept.id}
          onChange={(e) => pickDept(e.target.value)}
        >
          {DEPTS.map((d) => (
            <option key={d.id} value={d.id}>
              {d.name} ({d.years}년제)
            </option>
          ))}
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
            {yearsOf(dept).map((y) => (
              <option key={y} value={y}>{y}학년</option>
            ))}
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
          disabled={dept.careers.length === 0}
        >
          {dept.careers.length === 0 ? (
            <option>이 학과는 인재양성유형이 교육과정표에 없습니다</option>
          ) : (
            dept.careers.map((j) => <option key={j} value={j}>{j}</option>)
          )}
        </select>
        <p className="mt-1.5 font-mono text-xs text-steel">
          학교가 교육과정표 인재양성유형 열에 직접 붙인 직무입니다 · 이 학과 {dept.careers.length}종
        </p>
      </div>

      {/* 교육과정표만으로 전공 요건을 못 채우는 학과는 사실대로 알린다 */}
      {gap && (
        <p className="rounded-lg border border-gold/60 bg-gold/15 p-3 text-sm text-navy">
          <b>이 학과는 교육과정표만으로 전공 요건을 채울 수 없습니다.</b>{" "}
          표에 실린 전공이 {gap.have}학점인데 졸업요건은 {gap.need}학점입니다. 로드맵을 만들면
          검증기가 {gap.short}학점 미달로 잡습니다 — 데이터가 아니라 교육과정 자체의 공백이라
          학교용 리포트에서 다루는 사안입니다.
        </p>
      )}

      {/* TODO: 이수 과목 체크 — course_id 기반, data/depts/*.json의 courses 사용 */}
      <p className="rounded-lg border border-dashed border-edge bg-sky-soft/60 p-3 font-mono text-xs text-steel">
        이수 과목 체크는 다음 단계입니다. 지금은 {input.year}학년 {input.semester}학기 기준으로
        남은 전체 노선을 생성합니다.
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
