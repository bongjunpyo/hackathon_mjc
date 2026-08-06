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
