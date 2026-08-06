import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useApp } from "../store";
import { DEPTS, DEPT_BY_ID, creditGap, yearsOf } from "../lib/depts";
import { allCourseIdsBefore, coursesBefore } from "../lib/curricula";

export default function Input() {
  const { input, setInput, generate, loading } = useApp();
  const navigate = useNavigate();

  const dept = DEPT_BY_ID[input.deptId] ?? DEPTS[0];
  const gap = creditGap(dept);
  const past = coursesBefore(dept.id, input.year, input.semester);
  const checked = new Set(input.completedCourses);

  /* 지나간 학기는 들었다고 보는 게 기본값이다 — 재수강·미이수만 학생이 푼다.
     빈 목록에서 시작하면 2학년 학생이 스무 개를 일일이 눌러야 한다. */
  useEffect(() => {
    setInput((cur) => ({
      ...cur,
      completedCourses: allCourseIdsBefore(cur.deptId, cur.year, cur.semester),
    }));
  }, [input.deptId, input.year, input.semester, setInput]);

  function toggle(courseId) {
    const next = new Set(input.completedCourses);
    next.has(courseId) ? next.delete(courseId) : next.add(courseId);
    setInput({ ...input, completedCourses: [...next] });
  }

  function toggleSemester(sem) {
    const ids = sem.courses.map((c) => c.course_id);
    const allOn = ids.every((id) => checked.has(id));
    const next = new Set(input.completedCourses);
    ids.forEach((id) => (allOn ? next.delete(id) : next.add(id)));
    setInput({ ...input, completedCourses: [...next] });
  }

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

      {past.length > 0 ? (
        <fieldset className="flex flex-col gap-3">
          <legend className={label}>이수 과목 ({input.completedCourses.length}과목)</legend>
          <p className="text-sm text-ink-2">
            지나간 학기는 들은 것으로 표시했습니다. 재수강이나 미이수 과목만 체크를 푸세요.
          </p>
          {past.map((sem) => {
            const ids = sem.courses.map((c) => c.course_id);
            const allOn = ids.every((id) => checked.has(id));
            return (
              <div key={`${sem.year}-${sem.semester}`} className="rounded-xl border border-edge p-3.5">
                <div className="mb-2 flex items-baseline justify-between gap-3">
                  <b className="text-sm text-navy">
                    {sem.year}학년 {sem.semester}학기
                  </b>
                  <button
                    type="button"
                    onClick={() => toggleSemester(sem)}
                    className="rounded-md px-2 py-1 font-mono text-xs text-steel transition-[background-color,scale] duration-150 hover:bg-sky-soft active:scale-[0.96] focus-visible:outline-2 focus-visible:outline-gold"
                  >
                    {allOn ? "전체 해제" : "전체 선택"}
                  </button>
                </div>
                <ul className="flex flex-col gap-1">
                  {sem.courses.map((c) => (
                    <li key={c.course_id}>
                      <label className="flex cursor-pointer items-center gap-2.5 rounded-lg px-2 py-1.5 text-sm transition-[background-color] duration-150 hover:bg-sky-soft/70">
                        <input
                          type="checkbox"
                          checked={checked.has(c.course_id)}
                          onChange={() => toggle(c.course_id)}
                          className="size-4 accent-navy"
                        />
                        <span className={checked.has(c.course_id) ? "" : "text-steel line-through"}>
                          {c.name}
                        </span>
                        <span className="ml-auto font-mono text-xs tabular-nums text-steel">
                          {c.credits}학점
                        </span>
                      </label>
                    </li>
                  ))}
                </ul>
              </div>
            );
          })}
        </fieldset>
      ) : (
        <p className="rounded-lg border border-dashed border-edge bg-sky-soft/60 p-3 font-mono text-xs text-steel">
          1학년 1학기는 이수한 학기가 없습니다. 전체 노선을 생성합니다.
        </p>
      )}

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
