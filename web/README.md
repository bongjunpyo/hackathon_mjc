# web — P3 봉준표

React + Vite + Tailwind. 화면 5개: 입력 · 로드맵 뷰 · 리포트 뷰 (코어 3 먼저) + 메인 · 로그인 (통합 후).
`index.html` = 행선판 복도 시안(바닐라, 목데이터) — **메인(랜딩) 디자인 참고용**. React 전환 시 SEMESTERS 배열을 `POST /roadmap` 응답으로 교체.
게스트 모드 필수 — 로그인 없이도 입력→로드맵 경로가 항상 동작해야 한다.
API 계약: ../docs/DESIGN.md §5 (동결, `course_id`로만 통신), ../CLAUDE.md
