import { useEffect, useRef, useState } from "react";
import "../../styles/track.css";
import { VIEW_W, buildTrack, trackNodes } from "../../lib/track-geometry";

/* 자격증 이름이 길다 — "국제공인정보시스템보안전문가(CISSP)"를 그대로 그리면
   옆 구간 이름표를 덮는다. 트랙에서는 줄이고 전체 이름은 패널에서 본다. */
const short = (text, n = 13) => (text.length > n ? `${text.slice(0, n)}…` : text);
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

        {/* 자격증 분기 — 그 학기 **구간 중앙**에서 갈라진다. 학기를 보내는 중에 따는
           것이라 역(노드)이 아니라 구간에 붙는 게 맞다. 이름을 같이 낸다 — 🎫만
           있으면 무슨 자격증인지 패널을 열어야 안다.

           구간당 1개까지만 건다. 정보통신공학과는 자격증이 16종이라 다 걸면
           이름표가 서로를 덮는다 — 나머지는 "외 N"으로 세고 패널에서 본다.
           세로 구간(행 전환)은 모서리라 대각으로 빼면 여백 밖으로 나간다 —
           안쪽으로 수평 분기하고 이름표를 점 옆에 둔다. */}
        {meta.map((m, i) => {
          const cert = m.branches?.find((x) => x.kind === "cert");
          if (!cert) return null;
          const extra = m.branches.filter((x) => x.kind === "cert").length - 1;
          const a = nodes[i - 1];
          const b = nodes[i];
          const mx = (a.x + b.x) / 2;
          const my = (a.y + b.y) / 2;
          const vertical = a.x === b.x;
          const inward = mx > VIEW_W / 2 ? -1 : 1;
          const cx = vertical ? mx + 110 * inward : mx + 56;
          // 세로 구간은 모서리 — 가로 구간 이름표 밴드(my+90)를 피해 비켜 건다.
          // 왼쪽 열은 아래에 종착 게이트 판이 있으므로 위로 뺀다
          const cy = vertical ? my + (inward > 0 ? -55 : 55) : my + 58;
          return (
            <g key={`cert-${i}`} className="tbranch-g cert" aria-hidden="true">
              <path className="tbranch" d={`M ${mx} ${my} L ${cx} ${cy}`} />
              <circle className="tbranch-dot" cx={cx} cy={cy} r="12" />
              <text
                className="tbranch-label"
                x={vertical ? cx + 20 * inward : Math.min(Math.max(cx, 110), VIEW_W - 110)}
                y={vertical ? cy + 6 : cy + 32}
                textAnchor={vertical ? (inward > 0 ? "start" : "end") : "middle"}
              >
                {short(cert.label)}
                {extra > 0 && ` 외 ${extra}`}
              </text>
            </g>
          );
        })}

        {/* 일정 조언(이력서·포트폴리오)은 **역 아래**에 건다 (DESIGN §3).
           자격증과 같은 구간을 쓰면 이름표가 겹친다 — 역 아래는 비어 있다 */}
        {meta.map((m, i) => {
          const advice = m.branches?.find((x) => x.kind === "advice");
          if (!advice) return null;
          const { x, y } = nodes[i];
          return (
            <g key={`adv-${i}`} className="tbranch-g advice" aria-hidden="true">
              <path className="tbranch" d={`M ${x} ${y + 82} L ${x} ${y + 104}`} />
              <circle className="tbranch-dot" cx={x} cy={y + 110} r="10" />
              <text className="tbranch-label" x={x} y={y + 138} textAnchor="middle">
                {advice.label}
              </text>
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
