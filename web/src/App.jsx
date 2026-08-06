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
  const { guest, logout } = useApp();
  const cls = ({ isActive }) =>
    `px-3 py-2 text-sm rounded-lg transition-colors ${
      isActive ? "bg-navy text-white" : "text-ink-2 hover:bg-sky-soft"
    }`;
  return (
    <header className="sticky top-0 z-40 border-b border-edge bg-white/85 backdrop-blur">
      <nav className="mx-auto flex max-w-6xl items-center gap-2 px-5 py-3">
        <Link to="/" className="mr-auto flex items-center gap-2.5">
          <img src="/logo-mark.png" alt="" className="h-7 w-auto" />
          <span className="font-extrabold tracking-tight text-navy">MJC 취업 로드맵</span>
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
        {/* 로그인하면 '내 정보'에 로그아웃 하나뿐이라 한 단계를 없앤다 */}
        {guest ? (
          <NavLink to="/app/login" className={cls}>
            로그인
          </NavLink>
        ) : (
          <button
            onClick={logout}
            className="rounded-lg px-3 py-2 text-sm text-ink-2 transition-[background-color,scale] duration-150 hover:bg-sky-soft active:scale-[0.96] focus-visible:outline-2 focus-visible:outline-gold"
          >
            로그아웃
          </button>
        )}
      </nav>
    </header>
  );
}

/* 푸터 — 이 프로젝트가 무엇으로 만들어졌는지 밝히는 자리.

   데이터 출처와 산출 방식을 적는다. "AI가 짜준 로드맵"이 어디서 온 값인지
   물었을 때 화면 안에 답이 있어야 한다 (플레이북 §10 거짓 데모 금지). */
function Footer() {
  const col = "flex flex-col gap-2";
  const head = "font-mono text-xs tracking-[0.1em] text-sky";
  const item = "text-sm text-white/75";
  const link =
    "text-sm text-white/75 underline decoration-white/30 underline-offset-4 transition-colors hover:text-gold hover:decoration-gold";

  return (
    <footer className="mt-16 bg-navy text-white">
      <div className="mx-auto grid max-w-6xl gap-8 px-5 py-12 sm:grid-cols-2 lg:grid-cols-4">
        <div className={`${col} sm:col-span-2 lg:col-span-1`}>
          {/* navy 배경에서는 원본(짙은 남색 그라디언트)이 묻힌다 — 흰 실루엣으로 뒤집는다 */}
          <img
            src="/logo.png"
            alt="MAR"
            className="h-12 w-auto self-start"
            style={{ filter: "brightness(0) invert(1)", opacity: 0.92 }}
          />
          <p className="text-sm leading-relaxed text-white/75 text-pretty">
            목표 직무에서 역산한 학기별 로드맵을 졸업요건 검증기가 확인합니다.
            명지전문대학 34개 학과 교육과정표 기반.
          </p>
        </div>

        <div className={col}>
          <span className={head}>데이터 출처</span>
          <a className={link} href="https://www.mjc.ac.kr" target="_blank" rel="noreferrer">
            명지전문대학 학과별 교육과정표 ↗
          </a>
          <span className={item}>34개 학과 · 842과목 · 인재양성유형 라벨</span>
          <a
            className={link}
            href="https://www.q-net.or.kr"
            target="_blank"
            rel="noreferrer"
          >
            자격증 시행 정보 — Q-Net ↗
          </a>
          <a className={link} href="https://sanhak.mjc.ac.kr" target="_blank" rel="noreferrer">
            현장실습 — 산학협력처 ↗
          </a>
        </div>

        <div className={col}>
          <span className={head}>어떻게 만드나</span>
          <span className={item}>실데이터 추천 엔진이 학기별로 배치</span>
          <span className={item}>졸업요건 검증기(순수 규칙 코드)가 검사</span>
          <span className={item}>미달이면 사유를 실어 최대 3회 재생성</span>
          <span className={item}>LLM 비교 모드는 켤 때만 동작</span>
        </div>

        <div className={col}>
          <span className={head}>바로가기</span>
          <Link className={link} to="/app/roadmap">로드맵 만들기</Link>
          <Link className={link} to="/app/explore">학과 탐색</Link>
          <Link className={link} to="/app/report">학교용 정합도 리포트</Link>
          <a
            className={link}
            href="https://github.com/bongjunpyo/hackathon_mjc"
            target="_blank"
            rel="noreferrer"
          >
            GitHub ↗
          </a>
        </div>
      </div>

      <div className="border-t border-white/15">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center gap-x-4 gap-y-1 px-5 py-5 font-mono text-xs text-white/55">
          <span>2026 명지전문대학 RISE사업단 AI 해커톤 출품작</span>
          <span className="text-white/30">·</span>
          {/* 학교 공식 서비스로 오인되면 안 된다 — 진학·졸업 판단은 학과 확인이 최종이다 */}
          <span>학생 참고용 · 실제 수강신청과 졸업 판정은 소속 학과 확인이 우선합니다</span>
        </div>
      </div>
    </footer>
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
        <Footer />
      </BrowserRouter>
    </AppProvider>
  );
}
