/* 2D 트랙 지오메트리 — 순수 함수만 (docs/frontend/DESIGN.md §2.3).
   노드 목록 [입학, ...학기, ★직무] → 서펜타인 좌표 · 본선 path · 역별 누적거리 %.
   캐릭터 offset-path가 본선과 같은 문자열을 쓰므로, path를 바꾸면 여기서만 바꾼다. */

export const VIEW_W = 1200;
const PER_ROW = 3;
const X0 = 150;
const X_GAP = 450;
const Y0 = 120;
const ROW_H = 190;
const CORNER = 40; // 꺾임 라운딩 반경 — 캐릭터가 모서리에서 순간 꺾이지 않게

/** i번째 노드의 서펜타인 좌표. 홀수 행은 진행 방향이 반대다. */
export function nodeXY(i) {
  const row = Math.floor(i / PER_ROW);
  let col = i % PER_ROW;
  if (row % 2 === 1) col = PER_ROW - 1 - col;
  return { x: X0 + col * X_GAP, y: Y0 + row * ROW_H };
}

export function trackHeight(count) {
  const rows = Math.ceil(count / PER_ROW);
  return Y0 + (rows - 1) * ROW_H + 165;
}

/** 노드 배열 → {nodes:[{x,y}], path, at:[각 노드의 누적거리 %]} */
export function buildTrack(count) {
  const nodes = Array.from({ length: count }, (_, i) => nodeXY(i));

  // 본선 path — 폴리라인이되 꺾이는 지점만 Q로 라운딩.
  // 서펜타인에서 꺾임은 행이 바뀌는 노드에서만 생긴다 (그 노드 앞뒤로 방향이 다름)
  let path = `M ${nodes[0].x} ${nodes[0].y}`;
  for (let i = 1; i < nodes.length; i++) {
    const prev = nodes[i - 1];
    const cur = nodes[i];
    if (prev.y === cur.y) {
      path += ` L ${cur.x} ${cur.y}`;
    } else {
      // 행 전환: 수직으로 내려가는 구간. 위·아래 모서리를 둥글린다
      const dir = Math.sign(cur.x - prev.x) || 0; // 같은 x면 0 — 순수 수직
      if (dir === 0) {
        path += ` L ${cur.x} ${cur.y}`;
      } else {
        path += ` L ${prev.x + dir * CORNER} ${prev.y}`;
        path += ` Q ${cur.x} ${prev.y} ${cur.x} ${prev.y + CORNER}`;
        path += ` L ${cur.x} ${cur.y}`;
      }
    }
  }

  // 역별 누적거리 % — 직선 구간 산술 합. Q 라운딩의 오차는 반경 40에서 1% 미만이라
  // 캐릭터 발 위치에 보이는 차이가 없다 (DESIGN §2.4)
  const dist = [0];
  for (let i = 1; i < nodes.length; i++) {
    const dx = nodes[i].x - nodes[i - 1].x;
    const dy = nodes[i].y - nodes[i - 1].y;
    dist.push(dist[i - 1] + Math.hypot(dx, dy));
  }
  const total = dist[dist.length - 1] || 1;
  const at = dist.map((d) => (d / total) * 100);

  return { nodes, path, at, height: trackHeight(count) };
}

/** 학기별 분기 항목 — 자격증 + 일정 조언 2줄 (DESIGN §3).

    조언은 데이터가 아니라 프론트 규칙이다. 지어내는 게 아니라 규칙이 정한 두 개만
    꽂는다: 현장실습 첫 학기의 직전 학기 → 이력서, 마지막 학기 → 포트폴리오. */
export function branchesOf(semesters) {
  const fieldAt = semesters.findIndex((s) => s.courses.some((c) => c.field_based));
  const resumeAt = fieldAt > 0 ? fieldAt - 1 : -1;
  const last = semesters.length - 1;

  return semesters.map((s, i) => {
    const items = (s.certificates ?? []).map((c) => ({
      kind: "cert",
      label: typeof c === "string" ? c : (c?.name ?? ""),
    }));
    if (i === resumeAt) items.push({ kind: "advice", label: "이력서 준비" });
    if (i === last) items.push({ kind: "advice", label: "포트폴리오 완성" });
    return items.filter((x) => x.label);
  });
}

/** 로드맵 semesters → 트랙 노드 메타 [입학, ...학기, 종착] */
export function trackNodes(semesters, targetJob) {
  const branches = branchesOf(semesters);
  return [
    { kind: "start", label: "입학" },
    ...semesters.map((s, i) => ({
      kind: "semester",
      index: i,
      label: `${s.year}-${s.semester}`,
      title: `${s.year}학년 ${s.semester}학기`,
      credits: s.credits ?? s.courses.reduce((a, c) => a + (c.credits ?? 0), 0),
      branches: branches[i],
    })),
    { kind: "goal", label: targetJob || "목표 직무" },
  ];
}
