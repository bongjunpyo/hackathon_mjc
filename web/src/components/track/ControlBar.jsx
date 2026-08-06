import { useEffect, useState } from "react";
import { DEPTS, DEPT_BY_ID, realJobs, yearsOf } from "../../lib/depts";
import { allCourseIdsBefore, coursesBefore } from "../../lib/curricula";

/* 컨트롤 바 (DESIGN §2.2) — Input.jsx(v1)의 로직 이식.
   직무 드롭다운은 talent_types(=careers 필드) 우선 + 홍보 진로(promoted) 이어붙임.
   서버(jobmap)가 둘 다 받으므로 어느 쪽을 골라도 로드맵이 나온다. */
export default function ControlBar({ value, onChange, onGenerate, loading }) {
  const dept = DEPT_BY_ID[value.deptId] ?? DEPTS[0];
  const jobs = realJobs([...dept.careers, ...(dept.promoted ?? []).filter((j) => !dept.careers.includes(j))]);
  const [drawer, setDrawer] = useState(false);
  const past = coursesBefore(dept.id, value.year, value.semester);
  const checked = new Set(value.completedCourses);

  /* 지나간 학기는 들었다고 보는 게 기본값 — 재수강·미이수만 학생이 푼다 (Input.jsx와 동일) */
  useEffect(() => {
    onChange((cur) => ({
      ...cur,
      completedCourses: allCourseIdsBefore(cur.deptId, cur.year, cur.semester),
    }));
  }, [value.deptId, value.year, value.semester]); // eslint-disable-line react-hooks/exhaustive-deps

  function pickDept(deptId) {
    const next = DEPT_BY_ID[deptId];
    onChange((cur) => ({
      ...cur,
      deptId,
      year: Math.min(cur.year, next.years),
      targetJob: realJobs([...next.careers, ...(next.promoted ?? [])])[0] ?? "",
    }));
  }

  function toggle(courseId) {
    const next = new Set(value.completedCourses);
    next.has(courseId) ? next.delete(courseId) : next.add(courseId);
    onChange((cur) => ({ ...cur, completedCourses: [...next] }));
  }

  const field =
    "rounded-lg border border-edge bg-white px-2.5 py-2 text-sm text-ink focus-visible:outline-2 focus-visible:outline-gold";

  return (
    <div className="flex flex-col gap-2">
      <div className="flex flex-wrap items-center gap-2">
        <select aria-label="학과" className={`${field} min-w-44 flex-1`} value={dept.id}
                onChange={(e) => pickDept(e.target.value)}>
          {DEPTS.map((d) => (
            <option key={d.id} value={d.id}>{d.name} ({d.years}년제)</option>
          ))}
        </select>
        <select aria-label="학년·학기" className={field}
                value={`${value.year}-${value.semester}`}
                onChange={(e) => {
                  const [y, s] = e.target.value.split("-").map(Number);
                  onChange((cur) => ({ ...cur, year: y, semester: s }));
                }}>
          {yearsOf(dept).flatMap((y) =>
            [1, 2].map((s) => (
              <option key={`${y}-${s}`} value={`${y}-${s}`}>{y}학년 {s}학기</option>
            )),
          )}
        </select>
        {/* 고르거나 직접 타이핑한다. 비우면 서버가 배정 학점 기준으로 추천한다 (직무 미정 모드) */}
        <input
          aria-label="목표 직무"
          list="job-options"
          className={`${field} min-w-52 flex-1`}
          value={value.targetJob}
          placeholder="직무를 고르거나 입력 — 비우면 추천받기"
          onChange={(e) => onChange((cur) => ({ ...cur, targetJob: e.target.value }))}
        />
        <datalist id="job-options">
          {jobs.map((j) => <option key={j} value={j} />)}
        </datalist>
        {past.length > 0 && (
          <button type="button" onClick={() => setDrawer((v) => !v)} aria-expanded={drawer}
                  className={`${field} font-mono text-xs text-steel transition-[background-color,scale] duration-150 hover:bg-sky-soft active:scale-[0.96]`}>
            이수 {value.completedCourses.length}과목 {drawer ? "▲" : "▾"}
          </button>
        )}
        <button
          onClick={onGenerate}
          disabled={loading}
          className="rounded-xl bg-navy px-5 py-2 font-bold text-white transition-[background-color,scale] duration-200 hover:bg-navy-deep active:scale-[0.96] disabled:opacity-60 focus-visible:outline-2 focus-visible:outline-gold"
        >
          {loading ? "생성 중…" : value.targetJob.trim() ? "로드맵 생성" : "추천받아 생성"}
        </button>
      </div>

      {drawer && past.length > 0 && (
        <div className="flex flex-col gap-2 rounded-xl border border-edge bg-white p-3.5">
          <p className="text-xs text-ink-2">
            지나간 학기는 들은 것으로 표시했습니다. 재수강·미이수 과목만 체크를 푸세요.
          </p>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {past.map((sem) => (
              <div key={`${sem.year}-${sem.semester}`}>
                <b className="font-mono text-xs text-navy">{sem.year}학년 {sem.semester}학기</b>
                <ul className="mt-1 flex flex-col">
                  {sem.courses.map((c) => (
                    <li key={c.course_id}>
                      <label className="flex cursor-pointer items-center gap-2 rounded px-1 py-0.5 text-xs hover:bg-sky-soft/70">
                        <input type="checkbox" className="size-3.5 accent-navy"
                               checked={checked.has(c.course_id)}
                               onChange={() => toggle(c.course_id)} />
                        <span className={checked.has(c.course_id) ? "" : "text-steel line-through"}>
                          {c.name}
                        </span>
                      </label>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
