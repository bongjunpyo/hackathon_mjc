import { Link } from "react-router-dom";

/* 랜딩. 행선판 복도 3D 연출은 web/reference/walk-concept.html에서 포팅 예정 —
   부가 화면이므로 코어 통합(05:00) 이후. 지금은 진입 경로만 성립시킨다. */
export default function Landing() {
  return (
    <section className="flex flex-col gap-7 py-10">
      <span className="font-mono text-xs tracking-[0.14em] text-steel">
        MYONGJI COLLEGE · 취업 로드맵 에이전트
      </span>
      <h1 className="max-w-[16ch] text-4xl font-extrabold leading-tight tracking-tight text-balance sm:text-5xl">
        목표 직무를 고르면,{" "}
        <span className="mark-gold text-navy">졸업까지의 노선</span>이 그려집니다
      </h1>
      <p className="max-w-[56ch] text-ink-2">
        전문대 3년은 되돌아올 시간이 없는 편도 노선입니다. 어느 학기에 무엇을 듣고 자격증을 언제
        딸지 — 목표 직무에서 역산한 학기별 로드맵을 졸업요건 검증기가 보증합니다.
      </p>
      <div className="flex flex-wrap gap-3">
        <Link
          to="/app/input"
          className="rounded-xl bg-navy px-6 py-3 font-bold text-white transition-[background-color,scale] duration-200 hover:bg-navy-deep active:scale-[0.96]"
        >
          게스트로 시작하기 →
        </Link>
        <Link
          to="/app/login"
          className="rounded-xl border border-edge bg-white px-6 py-3 font-bold text-navy transition-[background-color,scale] duration-200 hover:bg-sky-soft active:scale-[0.96]"
        >
          로그인
        </Link>
      </div>
      <p className="font-mono text-xs text-steel">
        로그인하면 이수내역이 자동으로 채워지고 로드맵을 저장할 수 있습니다. 없어도 전부
        둘러볼 수 있습니다.
      </p>
    </section>
  );
}
