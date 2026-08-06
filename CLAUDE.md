# CLAUDE.md

> **진실 원천은 `docs/DESIGN.md`(설계서)다.** 이 파일은 설계서의 요약·실행 규칙이며, 두 문서가 어긋나면 설계서가 이긴다. 설계 변경은 설계서를 먼저 고치고(3인 합의) 이 파일에 반영한다.

## 프로젝트

- **한 줄 정의**: 원하는 직무를 고르면 졸업이 보장되는 학기별 로드맵(수강·자격증·현장실습)을 짜주는 전문대 특화 AI 에이전트 — 학교에는 교육과정 정합도 리포트를 제공한다.
- **데모 시나리오**: 심사위원이 **정보통신공학과**와 목표 직무 **`시스템관리·운용엔지니어`**를 고르면 학기별 로드맵과 "졸업요건 충족 ✓" 배지가 뜨고, 검증기가 미달 로드맵을 잡아 재생성시키는 장면을 보여준다.
  - 이 문장에 등장하지 않는 기능은 만들지 않는다. 범위 판단이 애매하면 이 문장으로 돌아온다.
  - **직무명은 데이터에 실재하는 값이어야 한다.** `네트워크 엔지니어`는 학교 페이지에 없다 — 원문이 "네트워크 관리 및 유지/보수 분야"라 직업명 꼴이 아니다 (이슈 #25). `시스템관리·운용엔지니어`는 교과과정표 비고 열의 라벨이라 **과목과 직접 연결**돼 있어 트랙 B 커버리지도 함께 나온다.
  - 실측(main): 규칙 엔진 0.03초 `passed=True` — 전공78/66 · 교양필수3/3 · 학기6/6 · 배치 81학점 · 남은 29학점. 직무 미정도 지원(커버리지 1위 추천). LLM 비교 모드는 34초.
  - 예외(2차 결정): 메인(랜딩)·로그인은 부가 기능으로 포함하되, **코어 통합(05:00) 이후에만** 착수한다. 게스트 모드가 있으므로 로그인이 없어도 데모 시나리오는 성립해야 한다.

## 스택

| 구분 | 선택 | 이유 |
|---|---|---|
| 프론트 | React + Vite + Tailwind | 8/6 저녁 최종 재확정. 기존 바닐라 시안(`web/index.html`)은 메인 디자인 참고용. 빌드 산출물을 FastAPI StaticFiles로 서빙해 실행 1커맨드 유지 |
| 백엔드 | FastAPI (uv, Python) + **PostgreSQL** (docker compose) | DB는 **유저 데이터 전용** — users / completed_courses / saved_roadmaps. sqlalchemy + psycopg, 마이그레이션 없이 create_all |
| 추천 엔진 | **실데이터 기반 결정론 규칙 (메인, 8/7 02시 결정)** | 근거 투명·즉시 응답·재현 가능. LLM(Claude `claude-sonnet-5`)은 `MJC_ENGINE=llm` 옵트인 비교용 보조. 검증기는 **LLM 없이 순수 규칙 코드** |
| 데이터 | `data/*.json` 시드 (전 학과, 2계층 품질) | **과목 데이터는 DB에 넣지 않는다.** 스키마는 docs/DESIGN.md §5 — 동결됨, 변경은 3인 합의 |

## 실행

```bash
docker compose up -d db                    # PostgreSQL
cd server && uv run fastapi dev main.py    # 개발 서버 (web/dist 정적 서빙 포함)
cd server && uv run pytest                 # 테스트 (검증기 룰 위주)
cd web && npm run dev                      # 프론트 개발 서버 (개발 중)
cd web && npm run build                    # 제출용 빌드 → server가 서빙
```

프론트 최초 부트스트랩(P3, 1회):

```bash
# 기존 바닐라 시안을 먼저 피신시킨다 — Vite가 web/index.html을 엔트리로 덮어쓴다
git mv web/index.html web/reference/walk-concept.html
npm create vite@latest web -- --template react
cd web && npm i && npm i -D tailwindcss @tailwindcss/vite
```

## 화면 (DESIGN.md §6 요약)

| # | 화면 | 구분 | 상태 |
|---|---|---|---|
| 1 | 입력 — 학과·학년/학기·이수 과목 체크·목표 직무 | 코어 | 먼저 |
| 2 | 로드맵 뷰 — 학기별 타임라인 + "졸업요건 충족 ✓" | 코어 | 먼저 |
| 3 | 리포트 뷰 — 직무별 커버리지·결손·라벨 불일치 (트랙 B) | 코어 | 먼저 |
| 4 | 메인(랜딩) — 서비스 소개 + 시작하기 | 부가 | 05:00 이후 |
| 5 | 로그인/회원가입 — 학번 기반 | 부가 | 05:00 이후 |

```
메인 → 로그인 ─┬→ 입력 → 로드맵 뷰 → [저장](로그인 시)
              └→ 게스트로 둘러보기 ↗
리포트 뷰: 상단 네비 "학교용 리포트" 탭으로 별도 진입
```

**게스트 모드는 필수 경로다.** 로그인이 미완이거나 컷돼도 `메인 → 게스트 → 입력 → 로드맵` 데모가 반드시 성립해야 한다. 로그인 상태를 전제로 하는 화면 로직을 짜지 않는다.

## 프론트 컨벤션 (P3)

```
web/
├── src/
│   ├── pages/       # 화면 7종 — Landing · RoadmapStudio · Walk · Explore · DeptDetail · Report · Login
│   ├── components/  # 재사용 (SignBoard, StationCard, ValidationBadge …)
│   ├── lib/api.js   # fetch 래퍼 — 게스트/토큰 분기를 여기 한 곳에만
│   └── index.css    # Tailwind 진입 + 디자인 토큰
└── reference/walk-concept.html   # 바닐라 시안 (수정 금지, 메인 디자인 참고용)
```

- **디자인 토큰은 Tailwind 테마에 등록해 쓴다** — 명지전문대 브랜드 컬러 `navy #002D65` · `sky #6DCBF9` · `gold #FFBA00`. 컴포넌트에 하드코딩한 헥사값 금지.
- **전역 상태는 Context 하나**로 끝낸다 (로드맵 결과 + 인증 토큰). Redux·Zustand·React Query 도입 금지 — 화면 7종에 과투자다.
- API 호출은 `lib/api.js`만 통한다. 컴포넌트에서 `fetch`를 직접 부르지 않는다.
- `completed_courses`는 **`course_id` 배열**로 보낸다. 과목명 문자열을 절대 키로 쓰지 않는다.
- 3D 복도 연출(랜딩)은 `reference/walk-concept.html`의 CSS perspective + sticky + 스크롤 진행률 변수 방식을 그대로 옮긴다. 새 애니메이션 라이브러리를 추가하지 않는다.
- `prefers-reduced-motion`을 존중한다 — 정보 접근성이 이 프로젝트의 공익 앵글이다.

## 폴더 소유권

한 파일은 한 사람이 맡는다. 에이전트에게도 담당 범위 밖을 고치게 두지 않는다.

| 경로 | 담당 |
|---|---|
| `pipeline/` `data/` | P1 박효민 — 수집 + LLM 추출 파이프라인, courses.json 산출, 품질 지표 (data/는 전원 읽기 가능, 쓰기는 P1만) |
| `server/` | P2 이동제 — 검증기 + 로드맵 에이전트 + 정합도 계산 + JWT 인증 + DB |
| `web/` | P3 봉준표 — 화면 7종 (랜딩·로드맵 스튜디오·3D 걷기·탐색·상세·리포트·로그인) |
| `docs/` | P1 박효민 겸임 — README, 다이어그램, PPT, 회의록, 발표 |

## 코딩 규칙

- 주변 코드와 같은 스타일로 쓴다 — 네이밍, 주석 밀도, 관용구를 맞춘다.
- 주석은 코드가 스스로 못 말하는 제약을 적을 때만 쓴다. 다음 줄이 뭘 하는지 설명하지 않는다.
- **로그인은 JWT 정석 구현** (액세스+리프레시, passlib 해싱) — 2차 결정으로 확정. 단 착수는 코어 통합 후이며, **게스트 모드가 항상 동작해야 한다** (10:00 미완 시 로그인 컷, 게스트로 데모).
- 소셜 로그인·이메일 인증·권한 등급은 만들지 않는다.
- 일어날 수 없는 상황에 대한 예외 처리를 넣지 않는다. 검증은 시스템 경계에서만.
- 미래 요구사항을 위한 추상화를 미리 만들지 않는다.
- API 계약(docs/DESIGN.md §5)은 동결 상태다. `course_id`로만 과목을 주고받는다 — 과목명 문자열 매칭 금지.
- 검증기 재생성 루프는 `max_retries: 3`. 초과 시 부분 로드맵 + 미달 사유를 **정상 응답으로** 반환한다.

## API 계약 요약 (전문은 DESIGN.md §5 — 동결)

| 엔드포인트 | 핵심 |
|---|---|
| `POST /roadmap` | in `completed_courses: [course_id]` / out `semesters[]` + `reasoning` + `validation{passed, total_credits, major_credits, liberal_credits, semesters, remaining_credits, details: [{rule, label, required, actual, shortfall, fix}]}` |
| `GET /report/{dept_id}` | `jobs[]` — coverage_pct · gaps / `certificates` — 대응있음·대응없음·**판정불가** 3분류 |
| `GET /depts` | `[{dept_id, dept_name, years, tier, careers, certificates, talent_types}]` |
| 에러 공통 | `{ error: { code, message } }` — `DEPT_NOT_FOUND`(404) · `UNKNOWN_JOB`(400) |
| `POST /auth/signup·login·refresh`, `GET /me`, `PUT /me/courses` | 인증 5종 — 코어 통합 후 착수 |

`validation.details`는 재생성 프롬프트 입력이자 발표 화면 재료다. 사람이 읽는 문자열로 뭉개지 않는다.

## 컷 규칙 (DESIGN.md §8 · 회의록 안건 5·6)

시각은 절대시각. **컷 판정은 혼자 하지 않고 단톡에 한 줄 남긴다.**

| 시각 | 판정 | 미달 시 |
|---|---|---|
| 22:00 | 파이프라인 (Tier1 추출) | Tier2를 "서브도메인 구조 동일 학과"로 축소 |
| 02:00 | **프론트 React 포팅 — 로드맵 뷰가 목데이터로 도는가** | `reference/walk-concept.html`(바닐라)을 랜딩으로 그대로 쓰고, 코어 3화면만 React로 간다 |
| 05:00 | 통합 시작 · 여기서부터 부가(메인·로그인) 착수 가능 | 코어 미완이면 부가 착수 금지 |
| 07:00 | 트랙 B API | 정적 HTML 리포트 1장으로 대체 |
| 10:00 | **기능 동결** — 이후 문서·치명 버그만 | 로그인 미완이면 게스트 모드로 컷 |
| 11:40 | 제출 (마감 12:00의 20분 전) | — |

**코어 데모가 부가 기능 때문에 깨지는 일은 금지한다.** 로그인·DB·랜딩은 언제든 잘라낼 수 있는 형태로만 붙인다.

## 커밋 규칙

- **작게, 자주.** 한 방 커밋은 히스토리를 없애고, 히스토리는 평가 대상이다. 푸시는 1시간에 1회 이상.
- 형식: `타입(범위): 요약` — 예 `feat(검증기): 3년제 총학점 룰`
- 에이전트로 큰 덩어리를 만들었으면 커밋 본문에 **검증 방법 한 줄**을 남긴다.
  ```
  feat(파이프라인): 교육과정표 HWP 추출
  
  정보통신공학과 원본 대조로 과목 수·학점 일치 확인
  ```

## 하지 말 것

- `main`을 깨뜨리는 커밋. 데모는 항상 `main`에서 띄운다. **작업 단위 브랜치(예: `p1/extract`, `p2/auth`) → main PR → 머지 후 브랜치 삭제.** force push 전면 금지.
- 담당 폴더 밖 파일 수정.
- API 키·비밀번호를 코드나 커밋에 남기는 것 (`.env`는 gitignore — 이미 걸려 있음).
- 데모에 보이지 않는 기능 구현.

## 작업 기록

에이전트에 위임한 작업은 `docs/AI_USAGE.md`에 **위임 방식과 검증 방법을 쌍으로** 기록한다.
실패 사례도 반드시 남긴다 — 검증 루프가 있다는 증거다.
