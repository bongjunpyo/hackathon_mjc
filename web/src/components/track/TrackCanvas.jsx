import { useEffect, useRef, useState } from "react";
import "../../styles/track.css";
import { VIEW_W, buildTrack, trackNodes } from "../../lib/track-geometry";
import Walker from "./Walker";

/* 2D 트랙 캔버스 (DESIGN §2.3).
   cursor = 캐릭터가 서 있는 노드 인덱스 (0=입학, 1..n=학기, n+1=★종착).
   이동·선택은 전부 부모 상태 — 여기는 좌표와 그리기만 안다. */
export default function TrackCanvas({ semesters, targetJob, cursor, passed, shortfallRules, onSelect }) {
  const meta = trackNodes(semesters, targetJob);
  const { nodes, path, at, height } = buildTrack(meta.length);
  const goal = meta.length - 1;
  const target = Math.min(cursor, goal);

  /* 캐릭터는 목표 노드까지 **한 역씩** 걷는다 (DESIGN §2.4).
     left·top을 한 번에 바꾸면 행을 건널 때 트랙 밖 대각선으로 질러간다 —
     서펜타인의 인접 노드는 한 축으로만 다르므로 역 단위 홉은 항상 트랙 위다. */
  const [pos, setPos] = useState(target);
  const dirRef = useRef(1);
  useEffect(() => {
    if (pos === target) return;
    if (matchMedia("(prefers-reduced-motion: reduce)").matches) {
      setPos(target);
      return;
    }
    const next = pos + Math.sign(target - pos);
    if (nodes[next].x !== nodes[pos].x) dirRef.current = Math.sign(nodes[next].x - nodes[pos].x);
    const t = setTimeout(() => setPos(next), 360);
    return () => clearTimeout(t);
  }, [pos, target]); // eslint-disable-line react-hooks/exhaustive-deps -- nodes는 count에서 파생
  const moving = pos !== target;
  // 종착에서는 게이트 판을 가리지 않게 앞(트랙 위)에 세운다 — 3D의 CAM_STOP과 같은 이유
  const stand = pos === goal ? { x: nodes[goal].x - 150, y: nodes[goal].y } : nodes[pos];

  // 미달(PARTIAL)이면 캐릭터가 멈춘 지점 뒤 학기를 붉게 (DESIGN §2.5)
  const shortfall = (shortfallRules?.length ?? 0) > 0;

  return (
    <div className="track-scene">
      {/* %좌표의 기준은 svg 높이여야 한다 — 씬은 그리드 stretch로 svg보다 길어질 수 있다 */}
      <div className="track-canvas">
      <svg viewBox={`0 0 ${VIEW_W} ${height}`} role="img" aria-label="학기별 로드맵 트랙">
        {/* 본선: 바탕 → 지나온 구간(gold 유도선) → 점형 블록 */}
        <path className="track-base" d={path} />
        <path
          className="track-walked"
          d={path}
          pathLength="100"
          strokeDasharray="100"
          strokeDashoffset={100 - at[pos]}
        />
        <path className="track-dots" d={path} />

        {/* 분기 가지 — 자격증이 있는 학기 노드에서 45°로 (행 방향 따라 위/아래) */}
        {meta.map((m, i) => {
          if (m.kind !== "semester" || !m.branches) return null;
          const { x, y } = nodes[i];
          const up = Math.floor(i / 3) % 2 === 1;
          const dy = up ? -64 : 64;
          return (
            <g key={`br-${i}`} aria-hidden="true">
              <path className="tbranch" d={`M ${x} ${y} l 64 ${dy}`} />
              <text x={x + 74} y={y + dy + 5} fontSize="24" textAnchor="start">🎫</text>
            </g>
          );
        })}

        {/* 역 노드 */}
        {meta.map((m, i) => {
          const { x, y } = nodes[i];
          if (m.kind === "goal") {
            return (
              <g key="goal" className="tnode" tabIndex={0} role="button"
                 aria-label={`종착 — ${m.label}`}
                 onClick={() => onSelect(i)}
                 onKeyDown={(e) => e.key === "Enter" && onSelect(i)}>
                <rect className="tgoal-board" x={x - 120} y={y - 44} width="240" height="76" rx="14" />
                <rect className="tgoal-stripe" x={x - 120} y={y + 24} width="240" height="8" rx="4" />
                <text x={x} y={y - 18} textAnchor="middle" fontSize="15"
                      fill="var(--color-sky)" fontFamily="monospace" letterSpacing="2">
                  FINAL DESTINATION
                </text>
                <text x={x} y={y + 10} textAnchor="middle" fontSize="21" fontWeight="800" fill="#fff">
                  ★ {m.label}
                </text>
                {/* 도착 + 검증 통과일 때만. passed=false에 ✓를 띄우면 거짓 데모다 */}
                {pos === goal && passed && (
                  <g className="gpop">
                    <rect x={x - 150} y={y - 96} width="300" height="40" rx="20"
                          fill="var(--color-gold)" />
                    <text x={x} y={y - 70} textAnchor="middle" fontSize="17" fontWeight="800"
                          fill="var(--color-navy-deep)">
                      ✓ 졸업요건 충족 — 검증기 통과
                    </text>
                  </g>
                )}
              </g>
            );
          }
          const state =
            shortfall && i > pos ? "shortfall"
            : i < pos ? "done"
            : i === pos ? "current"
            : "";
          return (
            <g key={m.label} className={`tnode ${state}`} tabIndex={0} role="button"
               aria-label={m.kind === "start" ? "입학" : `${m.title} · ${m.credits}학점`}
               aria-current={i === cursor ? "step" : undefined}
               onClick={() => onSelect(i)}
               onKeyDown={(e) => e.key === "Enter" && onSelect(i)}>
              <circle className="ring" cx={x} cy={y} r="22" />
              {i < cursor && (
                <text x={x} y={y + 7} textAnchor="middle" fontSize="20" fill="var(--color-navy)">✓</text>
              )}
              <text x={x} y={y + (m.kind === "start" ? 52 : 52)} textAnchor="middle"
                    fontSize="17" fontWeight="700" fill="var(--color-ink)">
                {m.kind === "start" ? "입학" : m.label}
              </text>
              {m.kind === "semester" && (
                <text x={x} y={y + 74} textAnchor="middle" fontSize="13"
                      fill="var(--color-steel)" fontFamily="monospace">
                  {m.credits}학점
                </text>
              )}
            </g>
          );
        })}

      </svg>

      {/* 캐릭터 — SVG 밖 HTML 오버레이. foreignObject 안의 offset-path는 Chromium이
         viewBox 축척을 안 먹여서 위치가 어긋난다. %좌표는 어느 폭에서든 정확하고,
         서펜타인은 인접 노드가 항상 한 축으로만 움직여 좌표 전환만으로 트랙을 따른다 */}
      <Walker
        className={moving ? "walking" : ""}
        style={{
          left: `${(stand.x / VIEW_W) * 100}%`,
          top: `${(stand.y / height) * 100}%`,
          "--dir": dirRef.current,
        }}
      />
      </div>
    </div>
  );
}
