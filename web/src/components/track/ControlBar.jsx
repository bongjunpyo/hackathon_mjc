import { useEffect, useState } from "react";
import { DEPTS, DEPT_BY_ID, atomicJobs, yearsOf } from "../../lib/depts";
import { allCourseIdsBefore, coursesBefore, jobEvidence } from "../../lib/curricula";

/* 컨트롤 바 (DESIGN §2.2).

   셋 다 빈 값으로 시작한다 — 예시가 골라져 있으면 "이미 고른 상태"로 읽혀서
   학생이 자기 학과를 안 바꾸고 생성한다.

   직무는 학과를 고르면 그 학과 커리큘럼에서 후보를 뽑아 채운다. 후보에 없는
   직무는 '기타(직접 입력)'로만 받는다 — 항상 열린 입력이면 오타가 그대로 서버로
   가고 400을 맞는다. */

export const OTHER = "__other__";
export const UNDECIDED = "__undecided__";

export default function ControlBar({ value, onChange, onGenerate, loading }) {
  const dept = DEPT_BY_ID[value.deptId];
  const candidates = dept
    ? jobEvidence(dept.id, atomicJobs([...dept.careers, ...(dept.promoted ?? [])]))
    : [];
  const [drawer, setDrawer] = useState(false);
  const past = dept && value.year ? coursesBefore(dept.id, value.year, value.semester) : [];
  const checked = new Set(value.completedCourses);

  /* 지나간 학기는 들었다고 보는 게 기본값 — 재수강·미이수만 학생이 푼다 */
  useEffect(() => {
    if (!value.deptId || !value.year) return;
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
      // 학과가 바뀌면 직무 후보가 통째로 달라진다 — 이전 선택을 들고 가면 400이다
      year: next && cur.year > next.years ? "" : cur.year,
      jobChoice: "",
      targetJob: "",
    }));
  }

  function pickJob(choice) {
    onChange((cur) => ({
      ...cur,
      jobChoice: choice,
      targetJob: choice === OTHER || choice === UNDECIDED ? "" : choice,
    }));
  }

  function toggle(courseId) {
    const next = new Set(value.completedCourses);
    next.has(courseId) ? next.delete(courseId) : next.add(courseId);
    onChange((cur) => ({ ...cur, completedCourses: [...next] }));
  }

  const field =
    "rounded-lg border border-edge bg-white px-2.5 py-2 text-sm text-ink focus-visible:outline-2 focus-visible:outline-gold";
  // 아직 안 고른 칸은 흐리게 — 고르면 진해진다
  const dim = (filled) => (filled ? "" : " text-steel");

  const ready =
    Boolean(value.deptId && value.year) &&
    (value.jobChoice === UNDECIDED || Boolean(value.targetJob.trim()));

  return (
    <div className="flex flex-col gap-2">
      <div className="flex flex-wrap items-center gap-2">
        <select
          aria-label="학과"
          className={`${field} min-w-44 flex-1${dim(value.deptId)}`}
          value={value.deptId}
          onChange={(e) => pickDept(e.target.value)}
        >
          <option value="">전공 선택</option>
          {DEPTS.map((d) => (
            <option key={d.id} value={d.id}>
              {d.name} ({d.years}년제)
            </option>
          ))}
        </select>

        <select
          aria-label="학년·학기"
          className={`${field}${dim(value.year)}`}
          value={value.year ? `${value.year}-${value.semester}` : ""}
          disabled={!dept}
          onChange={(e) => {
            const [y, s] = e.target.value.split("-").map(Number);
            onChange((cur) => ({ ...cur, year: y, semester: s }));
          }}
        >
          <option value="">학년과 학기</option>
          {dept &&
            yearsOf(dept).flatMap((y) =>
              [1, 2].map((s) => (
                <option key={`${y}-${s}`} value={`${y}-${s}`}>
                  {y}학년 {s}학기
                </option>
              )),
            )}
        </select>

        <select
          aria-label="목표 직무"
          className={`${field} min-w-52 flex-1${dim(value.jobChoice)}`}
          value={value.jobChoice ?? ""}
          disabled={!dept}
          onChange={(e) => pickJob(e.target.value)}
        >
          <option value="">직무 분야</option>
          {candidates.length > 0 && (
            <optgroup label="이 학과 교육과정에서 갈 수 있는 직무">
              {candidates.map((c) => (
                <option key={c.job} value={c.job}>
                  {c.job}
                  {c.courses > 0 && ` — 관련 ${c.courses}과목 ${c.credits}학점`}
                </option>
              ))}
            </optgroup>
          )}
          <optgroup label="직접 정하기">
            <option value={UNDECIDED}>아직 못 정했어요 — 추천받기</option>
            <option value={OTHER}>기타 (직접 입력)</option>
          </optgroup>
        </select>

        {past.length > 0 && (
          <button
            type="button"
            onClick={() => setDrawer((v) => !v)}
            aria-expanded={drawer}
            className={`${field} font-mono text-xs text-steel transition-[background-color,scale] duration-150 hover:bg-sky-soft active:scale-[0.96]`}
          >
            이수 {value.completedCourses.length}과목 {drawer ? "▲" : "▾"}
          </button>
        )}

        <button
          onClick={onGenerate}
          disabled={loading || !ready}
          className="rounded-xl bg-navy px-5 py-2 font-bold text-white transition-[background-color,scale] duration-200 hover:bg-navy-deep active:scale-[0.96] disabled:opacity-50 focus-visible:outline-2 focus-visible:outline-gold"
        >
          {loading ? "생성 중…" : value.jobChoice === UNDECIDED ? "추천받아 생성" : "로드맵 생성"}
        </button>
      </div>

      {/* 기타 — 후보에 없는 직무는 여기서만 받는다. 가장 가까운 라벨로 역산한다 */}
      {value.jobChoice === OTHER && (
        <input
          aria-label="직무 직접 입력"
          autoFocus
          className={`${field} max-w-md`}
          value={value.targetJob}
          placeholder="예: 네트워크 엔지니어 — 가장 가까운 교육과정 라벨로 역산합니다"
          onChange={(e) => onChange((cur) => ({ ...cur, targetJob: e.target.value }))}
        />
      )}

      {drawer && past.length > 0 && (
        <div className="flex flex-col gap-2 rounded-xl border border-edge bg-white p-3.5">
          <p className="text-xs text-ink-2">
            지나간 학기는 들은 것으로 표시했습니다. 재수강·미이수 과목만 체크를 푸세요.
          </p>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {past.map((sem) => (
              <div key={`${sem.year}-${sem.semester}`}>
                <b className="font-mono text-xs text-navy">
                  {sem.year}학년 {sem.semester}학기
                </b>
                <ul className="mt-1 flex flex-col">
                  {sem.courses.map((c) => (
                    <li key={c.course_id}>
                      <label className="flex cursor-pointer items-center gap-2 rounded px-1 py-0.5 text-xs hover:bg-sky-soft/70">
                        <input
                          type="checkbox"
                          className="size-3.5 accent-navy"
                          checked={checked.has(c.course_id)}
                          onChange={() => toggle(c.course_id)}
                        />
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
