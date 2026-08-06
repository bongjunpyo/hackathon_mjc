import { useEffect, useState } from "react";
import { BrowserRouter, Link, NavLink, Route, Routes } from "react-router-dom";
import { AppProvider, useApp } from "./store";
import { auth } from "./lib/api";
import Landing from "./pages/Landing";
import Login from "./pages/Login";
import Input from "./pages/Input";
import Roadmap from "./pages/Roadmap";
import Report from "./pages/Report";
import RoadmapStudio from "./pages/RoadmapStudio";
import Walk from "./pages/Walk";
import Explore from "./pages/Explore";
import DeptDetail from "./pages/DeptDetail";

function Nav() {
  const { guest } = useApp();
  const cls = ({ isActive }) =>
    `px-3 py-2 text-sm rounded-lg transition-colors ${
      isActive ? "bg-navy text-white" : "text-ink-2 hover:bg-sky-soft"
    }`;
  return (
    <header className="sticky top-0 z-40 border-b border-edge bg-white/85 backdrop-blur">
      <nav className="mx-auto flex max-w-6xl items-center gap-2 px-5 py-3">
        <Link to="/" className="mr-auto font-extrabold tracking-tight text-navy">
          MJC 취업 로드맵
        </Link>
        <NavLink to="/app/roadmap" className={cls}>
          로드맵 만들기
        </NavLink>
        <NavLink to="/app/explore" className={cls}>
          학과 탐색
        </NavLink>
        <NavLink to="/app/report" className={cls}>
          학교용 리포트
        </NavLink>
        <NavLink to="/app/login" className={cls}>
          {guest ? "로그인" : "내 정보"}
        </NavLink>
      </nav>
    </header>
  );
}

/* 이메일 인증 링크를 누르면 서버가 ?code=를 붙여 프론트로 되돌려보낸다
   (server/auth.py VERIFY_LANDING). 어느 경로로 떨어지든 잡히도록 라우트 바깥에 둔다. */
function VerifyExchange() {
  const { login } = useApp();
  const [error, setError] = useState(null);

  useEffect(() => {
    const url = new URL(window.location.href);
    const code = url.searchParams.get("code");
    if (!code) return;
    // 1회용 코드다. 주소에 남겨두면 새로고침 때 이미 쓴 코드로 다시 교환해 실패한다
    url.searchParams.delete("code");
    window.history.replaceState(null, "", url);
    auth
      .exchange(code)
      .then(({ access_token }) => login(access_token))
      .catch((err) => setError(err.message));
  }, []);

  if (!error) return null;
  return (
    <p className="mb-6 rounded-lg border border-gold/60 bg-gold/15 px-3 py-2 text-sm text-navy">
      {error} <Link to="/app/login" className="font-bold underline">로그인 화면으로</Link>
    </p>
  );
}

export default function App() {
  return (
    <AppProvider>
      <BrowserRouter>
        <Nav />
        <main className="mx-auto max-w-6xl px-5 py-8">
          <VerifyExchange />
          {/* 화면 경로는 /app/* 로 묶는다 — 동결된 API 경로(/roadmap, /report/*, /auth/*)와
              충돌하면 dev 프록시와 프로덕션 catch-all 양쪽에서 화면이 API로 새어나간다 */}
          <Routes>
            <Route path="/" element={<Landing />} />
            <Route path="/app/login" element={<Login />} />
            <Route path="/app/input" element={<Input />} />
            <Route path="/app/plan" element={<Roadmap />} />
            {/* v2 (PLAN.md P0) — 문서의 /roadmap·/explore를 /app/* 아래로 옮겼다.
                /roadmap은 동결 API 경로라 vite 프록시·정적 서빙 양쪽과 충돌한다 (PR #7) */}
            <Route path="/app/roadmap" element={<RoadmapStudio />} />
            <Route path="/app/walk" element={<Walk />} />
            <Route path="/app/explore" element={<Explore />} />
            <Route path="/app/explore/:deptId" element={<DeptDetail />} />
            <Route path="/app/report" element={<Report />} />
          </Routes>
        </main>
      </BrowserRouter>
    </AppProvider>
  );
}
