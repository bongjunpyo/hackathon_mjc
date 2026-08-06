/* 외부 시스템 안내.

   원칙: "언제·무엇"은 우리가 알려주고, "어디서"는 학교·기관 시스템으로 보낸다.
   다만 학교 산학협력 시스템은 딥링크가 통하지 않는다 — 로그인 페이지도 아니고
   메인으로 조용히 리다이렉트된다. 그래서 링크를 그냥 걸면 심사위원이 눌렀을 때
   엉뚱한 페이지에 도착한다. 눌리기 전에 무엇이 있는지 먼저 알려주고, 이동은 선택으로 둔다. */

const SANHAK = "https://sanhak.mjc.ac.kr/";
const QNET = "https://www.q-net.or.kr/man001.do?gSite=Q&gId=";

/** 현장실습·산학인턴십 과목인가. 학과마다 이름이 다르다
    (현장실습 / 사회복지현장실습 / 청소년기관 현장실습 / 콘텐츠디자인(산학인턴십) …) */
const FIELD_COURSE = /현장\s*실습|산학\s*인턴십|인턴십/;

export function externalFor(course) {
  if (!course?.name) return null;

  if (FIELD_COURSE.test(course.name)) {
    return {
      kind: "현장실습",
      title: "실습기관은 학교 산학협력 시스템에서 고릅니다",
      facts: [
        ["신청 시기", "직전 학기 중반 — 학과 공지로 안내됩니다"],
        ["운영", "WE-GO 현장실습 (산학협력처)"],
        ["준비물", "이력서 · 포트폴리오 · 지도교수 상담"],
      ],
      caution:
        "실습기관 목록과 신청은 학생 로그인이 필요합니다. 로그인 전에는 산학협력처 안내 페이지만 열립니다.",
      href: SANHAK,
      linkLabel: "산학협력 시스템 열기",
    };
  }
  return null;
}

/* 동결 계약(DESIGN.md §5)은 certificates의 원소 타입을 못 박지 않았다.
   서버는 문자열 배열("사회복지사 2급 자격증")을, 교육과정 폴백은 {name,tip} 객체를 준다.
   화면이 c.name만 읽으면 실서버에서 빈 배지가 뜬다 — 여기서 둘 다 받는다. */
export const certName = (c) => (typeof c === "string" ? c : (c?.name ?? ""));
export const certTip = (c) => (typeof c === "string" ? "" : (c?.tip ?? ""));

/** 자격증 → Q-Net. 국가기술자격이 아닌 것(OCJP 등)도 종목 검색으로 연결된다. */
export function certExternal(certName) {
  if (!certName) return null;
  return {
    kind: "자격증",
    title: "시험 일정과 응시 자격은 Q-Net에서 확인합니다",
    facts: [
      ["찾을 종목", certName],
      ["볼 것", "연간 시험일정 · 응시자격 · 접수 기간"],
    ],
    caution: "로그인 없이 열람할 수 있습니다. 접수만 회원가입이 필요합니다.",
    href: QNET,
    linkLabel: "Q-Net 열기",
  };
}
