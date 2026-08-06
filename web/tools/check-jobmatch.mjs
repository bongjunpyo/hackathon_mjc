/* 화면 근거 계산이 서버(jobmap.match_labels)와 같은 답을 내는지 전 학과 대조.
   손으로 옮긴 규칙이라 이 스크립트가 두 구현이 갈라지는 것을 잡는다 (이슈 #85).

   실행: node tools/check-jobmatch.mjs > /tmp/js.json */
import { DEPTS, atomicJobs } from "../src/lib/depts.js";
import { jobEvidence } from "../src/lib/curricula.js";

const out = [];
for (const d of DEPTS) {
  const jobs = atomicJobs([...d.careers, ...(d.promoted ?? [])]);
  for (const e of jobEvidence(d.id, jobs)) {
    out.push({ dept: d.id, job: e.job, courses: e.courses, matched: e.matched.sort() });
  }
}
console.log(JSON.stringify(out));
