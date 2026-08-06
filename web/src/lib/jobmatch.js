/* 타이핑한 직무 → 학과 직무 목록의 정확한 값으로 매핑.

   서버(server/jobmap.py)와 같은 규칙이어야 한다 — 정규화 후 완전 일치 확정,
   포함·토큰 겹침은 후보, 동률이면 목표 밖 글자가 가장 적은 것(=가장 가까운 것).
   서버는 목록에 있는 정확한 문자열만 받으므로(400), 매핑은 보내기 전에 여기서 한다. */

const SPLIT = /[\s·,/]/;
const MIN_TOKEN = 2;

const normalize = (text) => text.replace(/[\s·,/]/g, "");

export function bestJob(typed, jobs) {
  const target = normalize(typed);
  if (!target) return null;
  const tokens = typed.split(SPLIT).filter((t) => t.length >= MIN_TOKEN);

  const hits = [];
  for (const job of jobs) {
    const flat = normalize(job);
    if (target === flat) return job;
    if (target.includes(flat) || flat.includes(target)) hits.push(job);
    else if (tokens.length && tokens.every((t) => job.includes(t))) hits.push(job);
  }
  if (!hits.length) return null;
  const closest = Math.min(...hits.map((h) => normalize(h).length));
  return hits.find((h) => normalize(h).length === closest);
}

/* server/jobmap.py `match_labels()`의 포팅.

   화면이 세는 근거와 서버가 실제로 잇는 라벨이 갈리면 안 된다 — 드롭다운에
   "근거 없음"이라 써놓고 고르면 서버가 매칭에 성공하는 일이 실제로 있었다
   (정보통신 `시스템 엔지니어`, 이슈 #85).

   원본이 파이썬이라 손으로 옮긴 것이다. 규칙을 바꿀 일이 생기면 양쪽을 같이
   고치고, lib/__tests__ 없이도 tools/check-jobmatch.mjs로 전 학과 대조가 된다. */
export function matchLabels(job, labels) {
  const target = normalize(job);
  const tokens = job.split(SPLIT).filter((t) => t.length >= MIN_TOKEN);

  const hits = [];
  for (const label of labels) {
    const flat = normalize(label);
    // 완전 일치는 곧바로 확정 — 아래 최단 라벨 처리가 자기 자신을 버리는 것을 막는다
    if (target === flat) return [label];
    if (target.includes(flat) || flat.includes(target)) hits.push(label);
    else if (tokens.length && tokens.every((t) => label.includes(t))) hits.push(label);
  }

  // 토큰 겹침만 보면 너무 많이 걸린다 — 목표 밖 글자가 가장 적은 라벨만 남긴다
  if (hits.length > 1) {
    const closest = Math.min(...hits.map((h) => normalize(h).length));
    return hits.filter((h) => normalize(h).length === closest);
  }
  return hits;
}
