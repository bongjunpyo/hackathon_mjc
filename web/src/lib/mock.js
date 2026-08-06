/* 서버 미연결 구간용 목데이터. 동결 스키마(DESIGN.md §5) 형태를 그대로 따른다 —
   실 API가 붙으면 이 모듈은 폴백 경로에서만 쓰인다. */

const netSemesters = [
  {
    year: 1, semester: 1, credits: 18,
    goal: "기초 체력 학기 — 코딩과 네트워크 개념을 동시에 시동",
    courses: [
      { course_id: "itc-1-1-prog1", name: "프로그래밍언어실습Ⅰ", credits: 3,
        why: "모든 후속 실습 과목이 이 언어 위에서 돈다" },
      { course_id: "itc-1-1-netbasic", name: "컴퓨터네트워크기초", credits: 3,
        why: "목표 직무의 핵심 선수과목. OSI 7계층은 면접 단골" },
      { course_id: "itc-1-1-logic", name: "디지털논리회로", credits: 3,
        why: "장비를 다루는 직무라면 하드웨어 동작 원리가 뿌리" },
    ],
    certificates: [],
  },
  {
    year: 1, semester: 2, credits: 19,
    goal: "첫 자격증 학기 — 배운 범위가 식기 전에 시험으로 굳힌다",
    courses: [
      { course_id: "itc-1-2-prog2", name: "프로그래밍언어실습Ⅱ", credits: 3,
        why: "실습Ⅰ의 연장 — 방학 전까지 미니 프로젝트 1개" },
      { course_id: "itc-1-2-netpractice", name: "네트워크실무", credits: 3,
        why: "장비 CLI를 처음 만지는 과목. CCNA의 실습 기반" },
      { course_id: "itc-1-2-db", name: "데이터베이스기초", credits: 3,
        why: "정보처리 계열 자격증 필기와 직결" },
    ],
    certificates: [
      { name: "정보처리기능사",
        tip: "필기 범위가 1학기 과목과 크게 겹친다 — 기말 직후 4주 안에 응시" },
    ],
  },
  {
    year: 2, semester: 1, credits: 18,
    goal: "직무 핵심 진입 — 수업이 곧 자격증 공부가 되는 학기",
    courses: [
      { course_id: "itc-2-1-routing", name: "라우팅·스위칭", credits: 3,
        why: "네트워크 엔지니어 직무의 몸통. CCNA 출제 범위와 정면으로 겹친다" },
      { course_id: "itc-2-1-linux", name: "리눅스서버운용", credits: 3,
        why: "현장 장비 대부분이 리눅스 기반 — 우대사항 단골" },
      { course_id: "itc-2-1-ds", name: "자료구조", credits: 3,
        why: "코딩테스트 대비는 이 학기에 뿌리를 둔다" },
    ],
    certificates: [
      { name: "CCNA 학습 시작", tip: "라우팅·스위칭 수강과 병행하면 실습이 곧 시험공부다" },
    ],
  },
  {
    year: 2, semester: 2, credits: 18,
    goal: "CCNA를 손에 쥐고 포트폴리오의 뼈대를 세우는 학기",
    courses: [
      { course_id: "itc-2-2-wireless", name: "무선네트워크", credits: 3,
        why: "유선+무선을 다 다루면 지원 가능한 공고 폭이 넓어진다" },
      { course_id: "itc-2-2-security", name: "네트워크보안", credits: 3,
        why: "보안 지식은 네트워크 직무의 연봉 프리미엄" },
      { course_id: "itc-2-2-capstone1", name: "캡스톤디자인Ⅰ", credits: 3,
        why: "취업 포트폴리오 1번 — 주제를 직무와 맞출 것" },
    ],
    certificates: [
      { name: "CCNA 취득", tip: "겨울방학 전 취득이 마지노선 — 3학년은 자리가 없다" },
    ],
  },
  {
    year: 3, semester: 1, credits: 19,
    goal: "응시 자격이 열리는 학기 — 산업기사와 클라우드로 마무리 스퍼트",
    courses: [
      { course_id: "itc-3-1-cloud", name: "클라우드인프라", credits: 3,
        why: "온프레미스+클라우드를 함께 아는 신입은 드물다" },
      { course_id: "itc-3-1-netdesign", name: "네트워크설계", credits: 3,
        why: "지금까지 배운 것을 설계 관점으로 묶는 종합 과목" },
      { course_id: "itc-3-1-capstone2", name: "캡스톤디자인Ⅱ", credits: 3,
        why: "포트폴리오 완성판 — 시연 영상까지 남겨둘 것" },
    ],
    certificates: [
      { name: "정보처리산업기사",
        tip: "전문대 관련학과는 3학년부터 응시 자격이 생긴다 — 열리자마자 바로 친다" },
    ],
  },
  {
    year: 3, semester: 2, credits: 18,
    goal: "현장으로 — 실습이 곧 채용 관문",
    courses: [
      { course_id: "itc-3-2-intern", name: "현장실습(4주)", credits: 4,
        why: "취업 연계 확률이 가장 높은 관문" },
      { course_id: "itc-3-2-career", name: "취업역량강화", credits: 2,
        why: "이력서·면접을 학점으로 준비하는 마지막 정비 시간" },
    ],
    certificates: [],
  },
];

const aiSemesters = [
  { ...netSemesters[0] },
  {
    year: 1, semester: 2, credits: 19,
    goal: "파이썬과 데이터베이스 — AI 트랙의 두 기둥",
    courses: [
      { course_id: "itc-1-2-python", name: "파이썬프로그래밍", credits: 3,
        why: "AI 생태계의 공용어" },
      { course_id: "itc-1-2-db", name: "데이터베이스기초", credits: 3,
        why: "모델보다 데이터가 먼저다 — SQL은 채용공고 필수" },
      { course_id: "itc-1-2-prog2", name: "프로그래밍언어실습Ⅱ", credits: 3,
        why: "자료구조 수강 전 마지막 언어 훈련" },
    ],
    certificates: [{ name: "정보처리기능사", tip: "기말 직후 4주 안에 응시" }],
  },
  {
    year: 2, semester: 1, credits: 18,
    goal: "수학과 자료구조 — 모델을 '쓰는' 사람에서 '이해하는' 사람으로",
    courses: [
      { course_id: "itc-2-1-ds", name: "자료구조", credits: 3,
        why: "코딩테스트와 모델 구현 양쪽의 뿌리" },
      { course_id: "itc-2-1-aimath", name: "인공지능수학", credits: 3,
        why: "선형대수·확률 없이 면접 질문을 못 넘는다" },
      { course_id: "itc-2-1-linux", name: "리눅스서버운용", credits: 3,
        why: "학습 서버·GPU 환경은 전부 리눅스" },
    ],
    certificates: [{ name: "ADsP 학습 시작", tip: "인공지능수학과 병행하면 시험공부가 겹친다" }],
  },
  {
    year: 2, semester: 2, credits: 18,
    goal: "머신러닝 진입 + 포트폴리오 1호",
    courses: [
      { course_id: "itc-2-2-ml", name: "머신러닝기초", credits: 3,
        why: "직무 핵심 과목 — 과제 산출물을 그대로 깃허브에" },
      { course_id: "itc-2-2-dataprac", name: "데이터분석실습", credits: 3,
        why: "실데이터 전처리 경험이 신입의 차별화" },
      { course_id: "itc-2-2-capstone1", name: "캡스톤디자인Ⅰ", credits: 3,
        why: "AI 주제로 잡아 포트폴리오 1호로" },
    ],
    certificates: [{ name: "ADsP 취득", tip: "겨울방학 전 취득" }],
  },
  {
    year: 3, semester: 1, credits: 19,
    goal: "응시 자격이 열리는 학기 — 딥러닝과 클라우드로 스퍼트",
    courses: [
      { course_id: "itc-3-1-dl", name: "딥러닝응용", credits: 3,
        why: "모델 서빙까지 다뤄본 전문대 신입은 드물다" },
      { course_id: "itc-3-1-cloud", name: "클라우드인프라", credits: 3,
        why: "학습·배포 인프라 경험 — AI 직무 우대사항" },
      { course_id: "itc-3-1-capstone2", name: "캡스톤디자인Ⅱ", credits: 3,
        why: "포트폴리오 완성판" },
    ],
    certificates: [{ name: "정보처리산업기사", tip: "3학년부터 응시 자격 — 열리자마자 바로" }],
  },
  { ...netSemesters[5] },
];

/* 졸업요건 4종 요약 + 미달 상세. 키 이름은 DESIGN.md §5 동결 스펙 그대로.
   validation.semesters(재학 학기 수)는 out.semesters(로드맵 배열)와 다른 값이다. */
const validation = (semesters) => ({
  passed: true,
  total_credits: semesters.reduce((a, s) => a + s.credits, 0),
  major_credits: 78,
  liberal_credits: 12,
  semesters: semesters.length,
  details: [],
});

/* 검증기가 미달을 잡아 재생성시키는 장면이 발표 훅이다 —
   API 연결 전에도 그 화면을 리허설할 수 있게 실패 표본을 남겨둔다.
   (?fail=1 쿼리로 확인) */
export const MOCK_FAILED_VALIDATION = {
  passed: false,
  total_credits: 104,
  major_credits: 60,
  liberal_credits: 12,
  semesters: 6,
  // fix 문구는 server/validator.py의 FIXES 템플릿과 같은 형식이다
  details: [
    {
      rule: "total_credits", label: "총 학점", required: 110, actual: 104, shortfall: 6,
      fix: "아무 과목으로든 6학점을 더 채우세요",
    },
    {
      rule: "major_credits", label: "전공 학점", required: 66, actual: 60, shortfall: 6,
      fix: "전공 과목으로 6학점을 더 채우세요",
    },
  ],
};

export const MOCK_ROADMAPS = {
  "네트워크 엔지니어": { semesters: netSemesters, validation: validation(netSemesters) },
  "AI 개발자": { semesters: aiSemesters, validation: validation(aiSemesters) },
};

export const JOBS = Object.keys(MOCK_ROADMAPS);
