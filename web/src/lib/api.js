/* 백엔드 호출 단일 창구. 컴포넌트에서 fetch를 직접 부르지 않는다.
   게스트/토큰 분기와 목데이터 폴백이 전부 여기 모여 있다. */

import { DEPT_BY_ID } from "./depts";
import { pathFor } from "./curricula";

const TOKEN_KEY = "mjc_access_token";
const TIMEOUT_MS = 4000;

export const getToken = () => localStorage.getItem(TOKEN_KEY);
export const setToken = (t) => localStorage.setItem(TOKEN_KEY, t);
export const clearToken = () => localStorage.removeItem(TOKEN_KEY);
export const isGuest = () => !getToken();

async function call(path, { method = "GET", body } = {}) {
  const ctl = new AbortController();
  const timer = setTimeout(() => ctl.abort(), TIMEOUT_MS);
  try {
    const res = await fetch(path, {
      method,
      headers: {
        "Content-Type": "application/json",
        ...(getToken() ? { Authorization: `Bearer ${getToken()}` } : {}),
      },
      body: body ? JSON.stringify(body) : undefined,
      signal: ctl.signal,
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new ApiError(err?.error?.message ?? `요청 실패 (${res.status})`, res.status);
    }
    return res.json();
  } finally {
    clearTimeout(timer);
  }
}

export class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.status = status;
  }
}

/* 로드맵 생성. 서버가 아직 없으면 목데이터로 폴백한다 —
   폴백 여부를 source로 돌려주므로 화면에서 "목데이터" 배지를 띄울 수 있다.
   (거짓 데모 방지: 플레이북 §10) */
export async function postRoadmap({ deptId, year, semester, completedCourses, targetJob }) {
  try {
    const data = await call("/roadmap", {
      method: "POST",
      body: {
        dept_id: deptId,
        current_year: year,
        current_semester: semester,
        completed_courses: completedCourses, // course_id 배열 — 과목명 금지 (동결 스키마)
        target_job: targetJob,
      },
    });
    return { ...data, source: "api" };
  } catch {
    // 서버 미연결 폴백 — 교육과정표의 표준 이수 경로를 그대로 보여준다.
    // AI가 재배치한 로드맵이 아니므로 화면에서 source로 구분해 표시한다.
    return { ...standardPath(deptId, targetJob), source: "curriculum" };
  }
}

/** 교육과정표 기준 표준 경로 + 규칙 검증 요약 (server/validator.py와 같은 룰) */
function standardPath(deptId, targetJob) {
  const dept = DEPT_BY_ID[deptId];
  const semesters = pathFor(deptId, targetJob, dept?.years) ?? [];
  const all = semesters.flatMap((s) => s.courses);
  const sum = (cat) =>
    all.filter((c) => !cat || c.category === cat).reduce((a, c) => a + c.credits, 0);

  const req = dept?.years === 2
    ? { total: 75, liberal: 6, major: 45, semesters: 4 }
    : { total: 110, liberal: 10, major: 66, semesters: 6 };
  const actual = {
    total_credits: sum(), liberal_credits: sum("교양"),
    major_credits: sum("전공"), semesters: semesters.length,
  };
  const LABEL = {
    total_credits: "총 학점", liberal_credits: "교양 학점",
    major_credits: "전공 학점", semesters: "재학 학기",
  };
  const FIX = {
    total_credits: (n) => `아무 과목으로든 ${n}학점을 더 채우세요`,
    liberal_credits: (n) => `교양 과목으로 ${n}학점을 더 채우세요`,
    major_credits: (n) => `전공 과목으로 ${n}학점을 더 채우세요`,
    semesters: (n) => `과목을 ${n}개 학기에 더 나눠 배치하세요`,
  };
  const details = Object.entries({
    total_credits: req.total, liberal_credits: req.liberal,
    major_credits: req.major, semesters: req.semesters,
  })
    .filter(([k, need]) => actual[k] < need)
    .map(([k, need]) => ({
      rule: k, label: LABEL[k], required: need, actual: actual[k],
      shortfall: need - actual[k], fix: FIX[k](need - actual[k]),
    }));

  // ?fail=1 — 검증 미달 화면을 API 없이 리허설한다 (발표 훅 장면).
  // 실제 데이터로 통과하는 학과에서 전공 6학점을 깎아 미달을 만든다.
  if (new URLSearchParams(location.search).get("fail") === "1" && details.length === 0) {
    const short = 6;
    const major = req.major - short; // 요건 아래로 내려야 ✗ 표시와 수치가 맞는다
    return {
      semesters,
      validation: {
        passed: false,
        ...actual,
        major_credits: major,
        total_credits: actual.total_credits - (actual.major_credits - major),
        details: [{
          rule: "major_credits", label: LABEL.major_credits,
          required: req.major, actual: major,
          shortfall: short, fix: FIX.major_credits(short),
        }],
      },
    };
  }
  return { semesters, validation: { passed: details.length === 0, ...actual, details } };
}

export async function getDepts() {
  try {
    return await call("/depts");
  } catch {
    return [{ dept_id: "itc", dept_name: "정보통신공학과", years: 3, tier: 1 }];
  }
}

export async function getReport(deptId) {
  return call(`/report/${deptId}`);
}

export const auth = {
  signup: (b) => call("/auth/signup", { method: "POST", body: b }),
  login: (b) => call("/auth/login", { method: "POST", body: b }),
  me: () => call("/me"),
  saveCourses: (courseIds) =>
    call("/me/courses", { method: "PUT", body: { completed_courses: courseIds } }),
};
