# API 명세서 — 프론트 v2 클라이언트 계약

> 서버는 변경하지 않는다. 이 문서는 **프론트가 소비하는 계약**을 실측 응답 기준으로 적은 것이다.
> 원본: `docs/DESIGN.md` §5 (동결) · 구현: `server/main.py`. 어긋나면 server 구현이 정답.

## 0. 공통 규칙

- 모든 호출은 `lib/api.js` 단일 창구. 컴포넌트에서 `fetch` 직접 호출 금지.
- 과목은 **`course_id`로만** 주고받는다. 과목명 문자열 매칭 금지.
- 에러는 전 엔드포인트 공통 형식. 422(입력 검증 실패)도 이 형식으로 온다:

```json
{ "error": { "code": "UNKNOWN_JOB", "message": "사람이 읽는 한국어 설명" } }
```

| code | status | 언제 | 프론트 처리 |
|---|---|---|---|
| `DEPT_NOT_FOUND` | 404 | 없는 dept_id | message 표시 |
| `UNKNOWN_JOB` | 400 | 그 학과 직무가 아닌 target_job | message에 고를 수 있는 직무 목록이 들어 있음 — 그대로 표시 |
| (기타) | 422 | 필드 누락·형식 오류 | message 표시 + 컨트롤 바 하이라이트 |

## 1. `GET /depts` — 학과 목록 (컨트롤 바 소스)

응답 (배열, 학과당 1개):

```json
{
  "dept_id": "itc",
  "dept_name": "정보통신공학과",
  "years": 3,
  "tier": 1,
  "talent_types": ["시스템관리·운용엔지니어", "시스템응용SW개발엔지니어"],
  "careers": ["모바일 앱 프로그래머", "웹프로그래머", "게임 프로그래머", "..."],
  "certificates": ["정보처리산업기사", "CCNA", "..."]
}
```

- **직무 드롭다운 = `talent_types` 먼저, `careers` 이어붙임.** talent_types는 교과과정표 비고 열 라벨이라 과목(`talent_type`)과 직결된다 — 직무 역산이 실제로 걸리는 쪽. careers는 학과 소개 페이지의 진로.
- 서버 미기동 시 폴백: `lib/depts.js` (같은 파이프라인 산출물에서 생성한 번들).

## 2. `POST /roadmap` — 로드맵 생성 (메인 화면의 심장)

### 요청

```json
{
  "dept_id": "itc",
  "current_year": 2,
  "current_semester": 1,
  "completed_courses": ["itc-인성채플", "itc-프로그래밍언어실습1", "..."],
  "target_job": "시스템관리·운용엔지니어"
}
```

- `completed_courses`: 이수과목 드로어에서 체크된 `course_id` 배열. 게스트 기본값은 "선택 학기 이전 전 과목 자동 체크" 결과.

### ⚠ 지연 — 프론트가 반드시 대비할 것

| | |
|---|---|
| 정상(LLM 1회) | **약 27~50초** |
| 재생성 포함(최대 3회) | 최대 ~120초 |
| fetch timeout | **150초 이상**으로 설정 (`AbortController`). 기본 타임아웃에 걸리면 화면에선 그냥 실패로 보인다 |
| UX | GENERATING 상태 연출 필수 (DESIGN.md §2.5) — 스피너 하나로 27초를 버티게 하지 않는다 |

### 응답 (200 — 실측 형태)

```json
{
  "semesters": [
    {
      "year": 1, "semester": 1,
      "courses": [
        { "course_id": "itc-정보통신개론", "name": "정보통신개론", "year": 1, "semester": 1,
          "credits": 3, "category": "전공", "required": true,
          "talent_type": "시스템관리·운용엔지니어", "ncs": true, "field_based": false }
      ],
      "credits": 15,
      "certificates": ["정보처리기능사"],
      "notes": "전공 기초 다지기, 교양필수(채플·성경과삶) 이수, 정보처리 기능사 준비 시작"
    }
  ],
  "reasoning": "직무에서 역산한 근거 두세 문장 (rule 폴백이면 빈 문자열)",
  "validation": {
    "passed": true,
    "total_credits": 81,
    "major_credits": 78,
    "liberal_credits": 3,
    "semesters": 6,
    "remaining_credits": 29,
    "details": []
  },
  "attempts": 1,
  "engine": "llm",
  "unknown_courses": ["itc-오타난id"]
}
```

### 필드 → 화면 매핑

| 필드 | 화면 요소 |
|---|---|
| `semesters[].year/semester` | 트랙 본선 노드 (입학·★ 노드는 프론트가 앞뒤에 추가) |
| `semesters[].courses` | 학기 상세 패널 목록. `talent_type == target_job`이면 ★, `field_based`면 현장중심 태그 |
| `semesters[].credits` | 노드 보조 라벨 "15학점" |
| `semesters[].certificates` | 자격증 분기 노드 (학기당 2개까지 캔버스, 나머지 패널) |
| `semesters[].notes` | 패널 하단 💡 조언 |
| `validation.passed` | ★ 역 도착 시 배지 팝 여부 |
| `validation.details[]` | PARTIAL 상태: `{rule, label, required, actual, shortfall, fix}` — `label`+`fix`를 미달 배너에 그대로 |
| `validation.*_credits` / `semesters` | 하단 검증 배지 바: "전공 78/66 ✓ · 교양필수 3/3 ✓ · 학기 6/6 ✓" |
| `validation.remaining_credits` | 배지 바 문구 **"배치 81학점 · 졸업까지 29학점 남음"** — 총학점은 판정 대상이 아니라 정보다 (미달로 그리지 말 것) |
| `engine` | 배지 바 우측 태그: `llm`→"AI 생성" / `rule`→"규칙 생성(폴백)". 숨기지 않는다 |
| `attempts` | 2 이상이면 "검증기가 {n-1}회 재생성시킴" 문구 — 자기수정 루프의 증거, 발표 소재 |
| `unknown_courses` | 있으면 경고 토스트 "이수 과목 {n}개를 인식하지 못했습니다" |

## 3. `GET /report/{dept_id}` — 학교용 리포트

```json
{
  "dept_id": "itc", "dept_name": "정보통신공학과", "years": 3, "tier": 1,
  "extraction_confidence": 1.0,
  "jobs": [
    { "job": "시스템관리·운용엔지니어", "coverage_pct": 46.9, "credits": 38,
      "covered_courses": ["..."], "semesters": ["1-1", "2-1"], "gaps": ["...문장..."] }
  ],
  "certificates": {
    "total": 5, "evaluated": 5, "supported": 4,
    "unsupported": ["전자상거래관리사"],
    "unevaluated": ["판정 불가 자격증"],
    "detail": [ { "certificate": "CCNA", "courses": ["라우팅및스위칭"], "matched": true } ]
  },
  "ncs_ratio": 82.1,
  "field_based_courses": ["..."]
}
```

- 자격증은 **3분류**(supported / unsupported / unevaluated)다. `unevaluated`를 결손처럼 그리지 말 것 — "판정 불가"로 따로 표기한다.

## 4. 인증 (옆문 — 로그인 페이지만 사용)

| 엔드포인트 | 용도 |
|---|---|
| `POST /auth/signup` → 201 | 가입 (student_id, name, password, dept_id) |
| `POST /auth/login` → `{access_token, refresh_token}` | 로그인 |
| `POST /auth/refresh` | 토큰 갱신 |
| `GET /me` | 내 정보 + 이수내역 + 저장 로드맵 |
| `PUT /me/courses` | 이수내역 저장 (`course_id` 배열) |
| `POST /me/roadmaps` → 201 | 로드맵 저장 |

- 토큰 분기는 `lib/api.js` 한 곳에서만. **로그인 실패·미로그인이 코어 경로를 막으면 안 된다** — 저장 버튼만 로그인 요구.

## 5. 정적 번들 데이터 (서버 아님)

| 파일 | 내용 | 쓰는 화면 |
|---|---|---|
| `lib/depts.js` | 34개 학과 요약 (careers·학점) | 탐색 카드 · `GET /depts` 폴백 |
| `lib/curricula.js` | 학과별 전체 과목 (연·학기·학점·이수구분·라벨) | 학과 상세 커리큘럼 표 · 이수과목 드로어 자동 체크 |

- 파이프라인 산출물(`data/depts/*.json`)에서 생성. **손으로 고치지 말 것** — 어긋나면 P1에게 재생성 요청.
- 탐색·상세 화면은 서버 없이도 완전 동작한다 (정적 데이터만 사용). 서버가 필요한 화면은 `/roadmap`(생성)과 `/report`뿐.
