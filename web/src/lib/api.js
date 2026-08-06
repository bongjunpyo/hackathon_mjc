/* 백엔드 호출 단일 창구. 컴포넌트에서 fetch를 직접 부르지 않는다.
   게스트/토큰 분기와 목데이터 폴백이 전부 여기 모여 있다. */

import { MOCK_FAILED_VALIDATION, MOCK_ROADMAPS } from "./mock";

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
    const mock = MOCK_ROADMAPS[targetJob] ?? MOCK_ROADMAPS["네트워크 엔지니어"];
    // ?fail=1 — 검증 미달 화면을 API 없이 리허설한다 (발표 훅 장면)
    const forceFail = new URLSearchParams(location.search).get("fail") === "1";
    return {
      ...mock,
      validation: forceFail ? MOCK_FAILED_VALIDATION : mock.validation,
      source: "mock",
    };
  }
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
