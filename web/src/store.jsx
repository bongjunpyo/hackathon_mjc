/* 전역 상태는 이 Context 하나로 끝낸다 (CLAUDE.md 프론트 컨벤션).
   담는 것: 입력값 · 로드맵 결과 · 인증 상태. 그 외는 컴포넌트 로컬 상태. */

import { createContext, useContext, useState } from "react";
import { clearToken, isGuest, postRoadmap, setToken } from "./lib/api";

const AppContext = createContext(null);

export function AppProvider({ children }) {
  const [input, setInput] = useState({
    deptId: "itc",
    deptName: "정보통신공학과",
    year: 1,
    semester: 1,
    completedCourses: [], // course_id 배열
    targetJob: "시스템응용SW개발엔지니어",
  });
  const [roadmap, setRoadmap] = useState(null);
  const [loading, setLoading] = useState(false);
  const [guest, setGuest] = useState(isGuest());

  async function generate(overrides = {}) {
    const req = { ...input, ...overrides };
    setInput(req);
    setLoading(true);
    try {
      const data = await postRoadmap(req);
      setRoadmap(data);
      return data;
    } finally {
      setLoading(false);
    }
  }

  function login(token) {
    setToken(token);
    setGuest(false);
  }
  function logout() {
    clearToken();
    setGuest(true);
  }

  return (
    <AppContext.Provider
      value={{ input, setInput, roadmap, setRoadmap, loading, generate, guest, login, logout }}
    >
      {children}
    </AppContext.Provider>
  );
}

export function useApp() {
  const ctx = useContext(AppContext);
  if (!ctx) throw new Error("useApp must be used inside AppProvider");
  return ctx;
}
