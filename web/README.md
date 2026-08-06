# web — P3 봉준표

화면 5개 (입력·로드맵·리포트 + 메인·로그인). React + Vite + Tailwind v4.
규칙: `../CLAUDE.md` 프론트 컨벤션 · 계약: `../docs/DESIGN.md` §5(동결)

## 실행

```bash
npm i
npm run dev     # http://localhost:5173 — /roadmap 등 API는 127.0.0.1:8000으로 프록시
npm run build   # dist/ → FastAPI StaticFiles가 서빙
```

## 구조

```
src/
├── pages/       Landing · Login · Input · Roadmap · Report
├── lib/api.js   백엔드 단일 창구 (토큰·타임아웃·목데이터 폴백)
├── lib/mock.js  서버 미연결 구간 폴백 데이터 (동결 스키마 형태)
├── store.jsx    전역 상태 Context 하나 (입력·로드맵·인증)
└── index.css    Tailwind + 브랜드 토큰(@theme)
reference/
└── walk-concept.html   행선판 복도 3D 시안 (바닐라, 수정 금지 — 랜딩 포팅 원본)
```

## 규칙 요약

- 색은 `@theme`에 등록된 이름만 쓴다 (`text-navy` `bg-gold` …). 헥사값 하드코딩 금지
- `fetch`는 `lib/api.js`에서만. 컴포넌트에서 직접 호출하지 않는다
- 과목은 **`course_id`**로만 주고받는다 (과목명 문자열 매칭 금지 — 동결 스키마)
- 서버 미연결 시 로드맵 화면에 **"목데이터" 배지**가 뜬다. 가짜 수치를 진짜처럼 그리지 않는다
- 게스트 경로(`메인 → 게스트 → 입력 → 로드맵`)가 항상 살아 있어야 한다

## 알려진 사항

`npm audit`이 react-router 관련 high 2건을 보고한다. 해당 권고는 **RSC(React Server
Components) 모드**에서의 CSRF/리다이렉트 처리 건으로, 이 프로젝트는 순수 SPA(BrowserRouter)
라 경로가 존재하지 않는다. 7.11.0으로 내리면 오히려 다른 14건 범위에 들어가 최신을 유지한다.
