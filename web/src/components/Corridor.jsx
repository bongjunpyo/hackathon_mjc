import { useEffect, useMemo, useRef, useState } from "react";
import "../styles/corridor.css";

/* 행선판 복도 3D 씬.
   구조는 선언적으로 그리고, 스크롤 애니메이션은 ref로 직접 DOM을 만진다 —
   프레임마다 setState를 돌리면 리렌더 비용으로 스크롤이 끊긴다. */

const GAP = 1050;      // 행선판 간 깊이
const GATE_GAP = 1.6;  // 마지막 판 → 게이트 (겹침 방지)
const CAM_STOP = 500;  // 카메라는 게이트 이만큼 앞에서 멈춘다
const SEGLEN = 300;    // 바닥 세그먼트 (거대 단일 평면은 카메라 교차 시 통째로 컬링됨)

const prefersReduced = () =>
  window.matchMedia("(prefers-reduced-motion: reduce)").matches;

export default function Corridor({ semesters, targetJob, stats, onSelect }) {
  const hallwayRef = useRef(null);
  const sceneRef = useRef(null);
  const walkerRef = useRef(null);
  const postRefs = useRef([]);
  const lampRefs = useRef([]);
  const groundRefs = useRef([]);
  const [hudIndex, setHudIndex] = useState(0);

  const gateZ = -(semesters.length + GATE_GAP) * GAP;
  const depth = Math.abs(gateZ) - CAM_STOP;

  /* 바닥(중앙선·점자블록)과 펜스 세그먼트 좌표 */
  const ground = useMemo(() => {
    const road = Math.abs(gateZ);
    const items = [];
    for (let z = 0; z > -road - SEGLEN; z -= SEGLEN) {
      items.push({ cls: "railseg", z, len: SEGLEN, t: `translateZ(${z}px) rotateX(90deg)` });
      items.push({ cls: "tacseg", z, len: SEGLEN, t: `translateX(-150px) translateZ(${z}px) rotateX(90deg)` });
      items.push({ cls: "tacseg", z, len: SEGLEN, t: `translateX(150px) translateZ(${z}px) rotateX(90deg)` });
    }
    for (let z = 0; z > -road - GAP; z -= GAP) {
      items.push({ cls: "fenceseg", z, len: GAP, t: `translateX(-250px) translateZ(${z}px) rotateY(90deg)` });
      items.push({ cls: "fenceseg", z, len: GAP, t: `translateX(250px) translateZ(${z}px) rotateY(90deg)` });
    }
    return items;
  }, [gateZ]);

  const lamps = useMemo(
    () =>
      semesters.flatMap((_, i) => {
        const z = -(i + 1) * GAP + GAP / 2;
        return [
          { side: "ls", z, x: -310 },
          { side: "rs", z, x: 302 },
        ];
      }),
    [semesters.length],
  );

  useEffect(() => {
    if (prefersReduced()) return;
    const hallway = hallwayRef.current;
    const scene = sceneRef.current;
    const walker = walkerRef.current;
    let ticking = false;
    let idleTimer;

    function paint() {
      const r = hallway.getBoundingClientRect();
      const total = r.height - window.innerHeight;
      const p = Math.min(1, Math.max(0, -r.top / total));
      scene.style.transform = `translateZ(${p * depth}px)`;

      const camZ = -p * depth;
      // 카메라에 닿기 직전 요소는 페이드 — 화면을 가로막는 순간을 없앤다
      for (const el of postRefs.current) {
        if (!el) continue;
        const dz = +el.dataset.z - camZ;
        el.style.opacity = dz > -80 ? 0 : dz > -260 ? (-dz - 80) / 180 : 1;
      }
      for (const el of lampRefs.current) {
        if (!el) continue;
        const dz = +el.dataset.z - camZ;
        el.style.opacity = dz > -70 ? 0 : dz > -320 ? (-dz - 70) / 250 : 1;
      }
      for (const el of groundRefs.current) {
        if (!el) continue;
        el.style.visibility =
          +el.dataset.z - +el.dataset.len > camZ ? "hidden" : "visible";
      }

      const seg = 1 / (semesters.length + GATE_GAP);
      setHudIndex(Math.min(semesters.length, Math.floor(p / seg)));

      walker.classList.add("walking");
      clearTimeout(idleTimer);
      idleTimer = setTimeout(() => walker.classList.remove("walking"), 220);
    }

    const onScroll = () => {
      if (ticking) return;
      ticking = true;
      requestAnimationFrame(() => {
        paint();
        ticking = false;
      });
    };

    addEventListener("scroll", onScroll, { passive: true });
    addEventListener("resize", paint, { passive: true });
    paint();
    return () => {
      removeEventListener("scroll", onScroll);
      removeEventListener("resize", paint);
      clearTimeout(idleTimer);
    };
  }, [depth, semesters.length]);

  const hudLabel =
    hudIndex >= semesters.length ? "행선지 도착" : semesters[hudIndex]?.name ?? "출발 전";

  return (
    <div className="corridor">
      <div className="hallway" ref={hallwayRef} style={{ height: `${semesters.length * 102 + 3}vh` }}>
        <div className="stage">
          <Skyline />
          <div className="cloud c1" aria-hidden="true" />
          <div className="cloud c2" aria-hidden="true" />

          <div className="scene" ref={sceneRef} style={{ "--depth": `${depth}px` }}>
            {ground.map((g, i) => (
              <div
                key={`g${i}`}
                ref={(el) => (groundRefs.current[i] = el)}
                className={g.cls}
                data-z={g.z}
                data-len={g.len}
                style={{ transform: g.t }}
              />
            ))}

            {lamps.map((l, i) => (
              <div
                key={`l${i}`}
                ref={(el) => (lampRefs.current[i] = el)}
                className={`lamp ${l.side}`}
                data-z={l.z}
                style={{ transform: `translateX(${l.x}px) translateZ(${l.z}px)` }}
              />
            ))}

            {semesters.map((s, i) => {
              const z = -(i + 1) * GAP;
              return (
                <SignPost
                  key={s.name}
                  ref={(el) => (postRefs.current[i] = el)}
                  s={s}
                  index={i}
                  z={z}
                  prev={semesters[i - 1]}
                  next={semesters[i + 1]}
                  onSelect={onSelect}
                />
              );
            })}

            <div className="gate" style={{ transform: `translate3d(-50%, -50%, ${gateZ}px)` }}>
              <div className="gate-board">
                <div className="gate-kicker">FINAL DESTINATION</div>
                <div className="gate-title">{targetJob}</div>
                <div>{stats}</div>
                <div className="gate-badge">✓ 졸업요건 충족 — 검증기 통과</div>
                <div className="gate-sub">
                  이 노선의 모든 역은 졸업요건 검증기(규칙 코드)가 결정론적으로 검사했습니다
                </div>
              </div>
            </div>
          </div>

          <Walker ref={walkerRef} />

          <div className="hud" aria-label="노선 진행 상태">
            {semesters.map((s, i) => (
              <span key={s.name} className="contents">
                {i > 0 && <span className={`seg ${i <= hudIndex ? "past" : ""}`} />}
                <span
                  className={`stop ${i < hudIndex ? "past" : ""} ${i === hudIndex ? "here" : ""}`}
                  title={s.name}
                />
              </span>
            ))}
            <span className={`seg ${hudIndex >= semesters.length ? "past" : ""}`} />
            <span className={`stop ${hudIndex >= semesters.length ? "here" : ""}`} title="행선지" />
            <span className="label">{hudLabel}</span>
          </div>
        </div>
      </div>
    </div>
  );
}

function SignPost({ ref, s, index, z, prev, next, onSelect }) {
  return (
    <div
      ref={ref}
      className="signpost"
      data-z={z}
      style={{ transform: `translate3d(-50%, -50%, ${z}px)` }}
      role="button"
      tabIndex={0}
      aria-label={`${s.name} 상세 보기`}
      onClick={() => onSelect?.(index)}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          onSelect?.(index);
        }
      }}
    >
      <div className="signboard">
        <span className="sign-line">
          MJ<b>0{index + 1}</b>
        </span>
        <div className="sign-route">
          <span className="dir prev">
            <i>◀</i>
            {prev ? prev.name : "출발"}
          </span>
          <span className="dir next">
            {next ? next.name : "행선지"}
            <i>▶</i>
          </span>
        </div>
        <div className="sign-name">
          {s.name}
          <small>{s.en}</small>
        </div>
      </div>
      <div className="plaque">
        <div className="row">
          <b>이수 과목</b>
          <span className="credits">{s.credits}학점</span>
        </div>
        <ul>
          {s.courses.map((c) => (
            <li key={c.course_id ?? c.name}>{c.name}</li>
          ))}
        </ul>
        {s.certificates?.[0] && <span className="cert">🎫 {s.certificates[0].name}</span>}
      </div>
      <span className="pole l" />
      <span className="pole r" />
    </div>
  );
}

function Walker({ ref }) {
  return (
    <div className="walker" ref={ref} aria-hidden="true">
      <svg viewBox="0 0 60 100" fill="none">
        <ellipse className="w-shadow" cx="30" cy="94" rx="17" ry="4.2" />
        <g className="w-body">
          <g className="w-leg a"><rect className="w-figure" x="22.5" y="60" width="7" height="27" rx="3.5" /></g>
          <g className="w-leg b"><rect className="w-figure" x="30.5" y="60" width="7" height="27" rx="3.5" /></g>
          <g className="w-arm a"><rect className="w-figure" x="14.5" y="38" width="6" height="22" rx="3" opacity=".82" /></g>
          <g className="w-arm b"><rect className="w-figure" x="39.5" y="38" width="6" height="22" rx="3" opacity=".82" /></g>
          <rect className="w-figure" x="17" y="32" width="26" height="33" rx="10" />
          <rect className="w-bag" x="8.5" y="36" width="11" height="23" rx="5.5" />
          <rect className="w-figure" x="20" y="37" width="4" height="19" rx="2" opacity=".55" />
          <circle className="w-figure" cx="30" cy="17" r="11.5" />
          <path className="w-cap" d="M18.5 15.5 a11.5 11.5 0 0 1 23 0 l-2.5 1.2 a9 9 0 0 0 -18 0 z" />
          <rect className="w-cap" x="27" y="4.2" width="11" height="3.6" rx="1.8" transform="rotate(-8 32 6)" />
        </g>
      </svg>
    </div>
  );
}

function Skyline() {
  return (
    <div className="skyline" aria-hidden="true">
      <svg viewBox="0 0 1200 74" preserveAspectRatio="none" fill="currentColor">
        <rect x="0" y="44" width="70" height="30" /><rect x="80" y="28" width="54" height="46" />
        <rect x="144" y="50" width="90" height="24" /><rect x="248" y="18" width="40" height="56" />
        <rect x="300" y="38" width="72" height="36" /><rect x="386" y="52" width="110" height="22" />
        <rect x="510" y="30" width="48" height="44" /><rect x="570" y="44" width="86" height="30" />
        <rect x="670" y="12" width="36" height="62" /><rect x="716" y="36" width="64" height="38" />
        <rect x="794" y="50" width="120" height="24" /><rect x="928" y="26" width="50" height="48" />
        <rect x="990" y="42" width="80" height="32" /><rect x="1084" y="54" width="116" height="20" />
      </svg>
    </div>
  );
}
