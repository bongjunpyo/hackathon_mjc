import "../../styles/walker.css";

/* 걷는 캐릭터 — 3D 복도(랜딩)에서 회수한 공유 자산 (docs/frontend/DESIGN.md).
   `walking` 클래스로 걸음 애니메이션이 돌고, 걸음 속도는 --step 변수로 맞춘다. */
export default function Walker({ ref, className = "", ...rest }) {
  return (
    <div className={`walker ${className}`} ref={ref} aria-hidden="true" {...rest}>
      <svg viewBox="0 0 60 100" fill="none">
        {/* 다리 끝이 y=87 — 그림자를 그보다 아래에 두면 확대했을 때 발과 분리돼 뜬다 */}
        <ellipse className="w-shadow" cx="30" cy="88" rx="17" ry="4.2" />
        <g className="w-body">
          <g className="w-leg a"><rect className="w-figure" x="22.5" y="60" width="7" height="27" rx="3.5" /></g>
          <g className="w-leg b"><rect className="w-figure" x="30.5" y="60" width="7" height="27" rx="3.5" /></g>
          {/* 가방은 팔·몸보다 먼저 — 앞에 그리면 작은 화면(3D)에서 노란 팔로 읽힌다 */}
          <rect className="w-bag" x="8.5" y="36" width="11" height="23" rx="5.5" />
          <g className="w-arm a"><rect className="w-figure" x="14.5" y="38" width="6" height="22" rx="3" opacity=".82" /></g>
          <g className="w-arm b"><rect className="w-figure" x="39.5" y="38" width="6" height="22" rx="3" opacity=".82" /></g>
          <rect className="w-figure" x="17" y="32" width="26" height="33" rx="10" />
          <rect className="w-figure" x="20" y="37" width="4" height="19" rx="2" opacity=".55" />
          <circle className="w-figure" cx="30" cy="17" r="11.5" />
          <path className="w-cap" d="M18.5 15.5 a11.5 11.5 0 0 1 23 0 l-2.5 1.2 a9 9 0 0 0 -18 0 z" />
          <rect className="w-cap" x="27" y="4.2" width="11" height="3.6" rx="1.8" transform="rotate(-8 32 6)" />
        </g>
      </svg>
    </div>
  );
}
