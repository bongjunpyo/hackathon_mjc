# API 명세 (server)

> **구현 기준**입니다. 계약의 진실 원천은 `../docs/DESIGN.md` §5이고, 이 문서는 실제로 도는 것을 적었습니다.
> 동결 스펙과 다른 곳은 ⚠️로 표시했습니다 — 설계서 반영은 이슈 #24에서 진행 중입니다.

기본 주소 `http://localhost:8000` · 요청/응답 모두 JSON · 인증은 `Authorization: Bearer <access_token>`

| 구분 | 엔드포인트 |
|---|---|
| 코어 (토큰 불필요) | [`GET /depts`](#get-depts) · [`POST /roadmap`](#post-roadmap) · [`GET /report/{dept_id}`](#get-reportdept_id) |
| 인증 | [`POST /auth/email/code`](#post-authemailcode) · [`POST /auth/email/verify`](#post-authemailverify) · [`POST /auth/signup`](#post-authsignup) · [`GET /auth/verify`](#get-authverify) · [`POST /auth/exchange`](#post-authexchange) · [`POST /auth/login`](#post-authlogin) · [`POST /auth/resend`](#post-authresend) · [`POST /auth/refresh`](#post-authrefresh) |
| 내 정보 (토큰 필요) | [`GET /me`](#get-me) · [`PUT /me/courses`](#put-mecourses) · [`POST /me/roadmaps`](#post-meroadmaps) |

**코어 3종은 토큰이 없어도 200을 냅니다.** 게스트 모드가 필수 경로이므로 인증이 코어를 막지 않습니다.

---

## 에러 형식

**모든 실패가 같은 봉투로 나갑니다.** 입력 검증 실패(422)도 포함합니다 — FastAPI 기본 형식(`{detail:[...]}`)은 프론트 `lib/api.js`가 못 읽습니다.

```json
{ "error": { "code": "UNKNOWN_JOB", "message": "사람이 읽는 한 줄" } }
```

| 상태 | 코드 | 언제 |
|---:|---|---|
| 400 | `UNKNOWN_JOB` | `target_job`이 그 학과의 직무가 아님. 메시지에 고를 수 있는 목록이 들어 있음 |
| 400 | `INVALID_TOKEN` | 인증 링크가 유효하지 않음 (이미 썼거나 없음) |
| 400 | `TOKEN_EXPIRED` | 인증 링크 30분 만료 |
| 400 | `INVALID_CODE` | 교환 코드가 유효하지 않음 (이미 썼거나 없음) |
| 400 | `CODE_EXPIRED` | 교환 코드 60초 만료 · 이메일 인증번호 10분 만료 |
| 400 | `TERMS_REQUIRED` | 가입 요청에 `agreed_terms`·`agreed_privacy`가 참이 아님 |
| 429 | `TOO_MANY_TRIES` | 이메일 인증번호 5회 초과 시도 — 번호를 다시 받아야 함 |
| 401 | `UNAUTHORIZED` | 토큰 없음·형식 오류·위조·액세스 토큰 아님 |
| 401 | `BAD_CREDENTIALS` | 학번 또는 비밀번호 불일치 |
| 403 | `EMAIL_NOT_VERIFIED` | 이메일 인증 전 로그인 시도 |
| 404 | `DEPT_NOT_FOUND` | 학과 데이터 없음 |
| 409 | `ALREADY_REGISTERED` | 학번 또는 이메일 중복 |
| 422 | `VALIDATION_ERROR` | 입력 형식 오류 (비밀번호 8자 미만, 이메일 형식 등) |
| 503 | `DB_UNAVAILABLE` | DB 연결 실패. **인증 계열만** 해당 — 코어는 계속 200 |

---

# 코어

## `GET /depts`

학과 목록. 입력 화면의 학과·목표 직무·자격증 드롭다운 재료입니다.

```json
[
  {
    "dept_id": "itc",
    "dept_name": "정보통신공학과",
    "years": 3,
    "tier": 1,
    "talent_types": ["시스템관리·운용엔지니어", "시스템응용SW개발엔지니어"],
    "careers": ["모바일 앱 프로그래머", "웹프로그래머", "시스템 엔지니어", "..."],
    "certificates": ["정보처리 산업기사", "CCNA", "..."]
  }
]
```

⚠️ `talent_types` · `careers` · `certificates`는 동결 스펙에 없는 추가 필드입니다.

> **`talent_types`와 `careers`는 다른 축입니다.** 앞은 교육과정표의 인재양성유형(과목에 붙은 라벨), 뒤는 학과 소개 페이지의 진로입니다. **드롭다운에는 둘 다 넣으세요** — `POST /roadmap`이 둘 다 받습니다.

## `POST /roadmap`

목표 직무에서 역산한 학기별 로드맵 + 졸업요건 검증 결과.

### 요청

```json
{
  "dept_id": "itc",
  "current_year": 1,
  "current_semester": 1,
  "completed_courses": ["itc-자료구조"],
  "target_job": "시스템관리·운용엔지니어"
}
```

| 필드 | 설명 |
|---|---|
| `completed_courses` | **`course_id` 배열**. 과목명 문자열 금지 (이슈 #4·#9) |
| `target_job` | `GET /depts`의 `talent_types` 또는 `careers` 중 하나. 아니면 400 |

`current_year`·`current_semester`는 **지금 있는 학기**입니다. 로드맵은 그 학기부터 **남은 학기만** 담습니다.

### 응답

```json
{
  "semesters": [
    {
      "year": 1, "semester": 1,
      "courses": [
        { "course_id": "itc-네트워크실무", "name": "네트워크실무", "credits": 3,
          "category": "전공", "talent_type": "시스템관리·운용엔지니어", "job_related": true }
      ],
      "certificates": ["CCNA"],
      "notes": "네트워크II·무선네트워크 심화 학습 후 CCNA 자격증 취득을 목표로 한다."
    }
  ],
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
  "job_match": {
    "matched_labels": ["시스템관리·운용엔지니어"],
    "related_courses": 12,
    "note": ""
  }
}
```

### `validation` — 검증기가 판정한 것

| 필드 | 뜻 |
|---|---|
| `passed` | **전공 · 교양필수 · 재학학기**를 모두 충족했는가 |
| `total_credits` | 배치된 학점 (전공 + 교양필수) |
| `remaining_credits` | ⚠️ 졸업까지 남은 학점 |
| `details` | 미달 항목. 통과하면 빈 배열 |

> **총학점은 미달로 잡지 않습니다.** 교육과정표가 전공 전용 문서라 교양선택·일반선택이 아예 없습니다. 학생이 자유롭게 고르는 그 몫을 우리 데이터로는 판정할 근거가 없어서, **없는 과목을 지어내는 대신 `remaining_credits`로 알립니다.**
>
> 화면 문구: `배치 81학점 · 졸업까지 29학점 남음`

### `details[]` — 미달 항목

```json
{ "rule": "major_credits", "label": "전공 학점",
  "required": 66, "actual": 60, "shortfall": 6,
  "fix": "전공 과목으로 6학점을 더 채우세요" }
```

⚠️ `label`·`fix`는 동결 스펙에 없는 추가 필드입니다. `label`은 화면 표시용, **`fix`는 재생성 프롬프트에 그대로 들어갑니다** — `shortfall: 6`만 주면 생성기가 아무 과목이나 채웁니다.

| `rule` | `label` | 판정 |
|---|---|---|
| `major_credits` | 전공 학점 | 2년제 45 / 3년제 66 |
| `liberal_required` | 교양필수 | 3 (인성채플 1 + 성경과삶 2) |
| `semesters` | 재학 학기 | 2년제 4 / 3년제 6 |
| `malformed_course` | 과목 형식 오류 | 생성기가 `credits`·`category`를 빠뜨림 |

⚠️ `liberal_required`는 이전 `liberal_credits`(교양 10)를 대체합니다. **미지의 `rule`이 올 수 있으니 화면은 모르는 값도 별도 줄로 표시해 주세요.**

### 그 외 필드

| 필드 | 설명 |
|---|---|
| `attempts` | 재생성 횟수 (1~3). 검증기가 잡아 다시 짠 횟수 |
| `engine` | ⚠️ `"llm"` · `"rule"` · `"rule (llm-failed)"` — 무엇이 로드맵을 짰는가 |
| `job_match` | ⚠️ 목표 직무가 교육과정 라벨과 이어졌는가 |
| `unknown_courses` | ⚠️ 보낸 `course_id` 중 카탈로그에 없던 것 (있을 때만) |

**`job_match.matched_labels`가 비면 직무 맞춤이 안 된 것입니다.** 로드맵은 나오지만 졸업요건만 맞춘 일반 로드맵이고, `note`에 그 사실이 적힙니다. **화면에 그 문구를 띄우세요** — 조용히 넘기면 "직무 역산"이 거짓이 됩니다.

### 응답 시간 ⚠️

| 생성기 | 시간 |
|---|---|
| `planner` (키 없음) | 즉시 |
| `agent (LLM)` | **18~68초** (재생성 시 최대 3회 호출) |

**프론트 타임아웃을 90초로 잡아야 합니다.** 4초면 서버가 정상 동작하는데도 목데이터로 떨어집니다.

## `GET /report/{dept_id}`

트랙 B — 학교용 교육과정 진단.

```json
{
  "dept_id": "itc", "dept_name": "정보통신공학과",
  "tier": 1, "extraction_confidence": 1.0, "major_credits": 78,
  "jobs": [
    { "job": "시스템 엔지니어",
      "matched_labels": ["시스템관리·운용엔지니어"],
      "coverage_pct": 46.2, "covered_credits": 36,
      "covered_courses": [{ "course_id": "...", "name": "...", "credits": 3 }],
      "gaps": [] }
  ],
  "label_mismatches": [
    { "kind": "not_a_job", "labels": ["공통"], "note": "'공통'은 직무명이 아닙니다 …" }
  ]
}
```

⚠️ **`label_mismatches`가 최상위에 있습니다.** 동결 스펙은 `jobs[]` 안에 두지만, 라벨 문제는 특정 직무의 속성이 아니라 학과 데이터 전체의 성질이라 올렸습니다. job마다 같은 목록을 복제하는 것도 중복입니다.

| `kind` | 뜻 | 추가 필드 |
|---|---|---|
| `joined` | 직무 여러 개가 한 칸에 묶임 | **`parts`** (쪼갠 결과) |
| `not_a_job` | `'공통'` 등 직무가 아닌 값 | — |
| `near_duplicate` | 오타로 같은 직무가 두 라벨로 갈림 | — |
| `same_set` | 같은 묶음인데 순서·표기가 다름 | — |

> **`parts`는 `joined`에만 있습니다.** 다른 종류에서 `.join()`을 부르면 터집니다.

`gaps`가 비어 있지 않으면 그 진로에 대응하는 인재양성유형이 없다는 뜻입니다.

---

# 인증

> 흐름: **가입 → 인증 메일 → 링크 클릭 → 1회용 교환 코드 → 토큰 발급**
> 인증을 마쳐야 로그인할 수 있고, **인증하는 순간 자동으로 로그인**됩니다.

## `POST /auth/email/code`

가입 화면을 떠나지 않고 이메일을 인증합니다. 6자리 번호를 메일로 보냅니다.

```json
{ "email": "dj@mjc.ac.kr" }
```

→ `200 { "message": "인증번호를 보냈습니다. 메일함을 확인해 주세요.", "expires_in": 600 }`

**이미 가입된 이메일인지 알려주지 않습니다** (계정 열거 방지). 번호는 메일함 주인만 봅니다.
번호는 유저 행이 생기기 전이라 DB가 아니라 프로세스 메모리에 TTL과 함께 둡니다 — 서버를 재시작하면 사라지고, 재발송하면 됩니다.

## `POST /auth/email/verify`

```json
{ "email": "dj@mjc.ac.kr", "code": "482915" }
```

→ `200 { "verified": true, "email_ticket": "…" }` — 티켓 유효 30분

5회를 넘겨 틀리면 `429 TOO_MANY_TRIES`로 막고 번호를 폐기합니다.

## `POST /auth/signup`

```json
{ "student_id": "202512345", "name": "이동제",
  "email": "dj@mjc.ac.kr", "password": "hunter22!", "dept_id": "itc",
  "agreed_terms": true, "agreed_privacy": true,
  "email_ticket": "…" }
```

⚠️ `email`은 동결 스펙에 없는 추가 필드입니다 — 이메일 인증에 필수입니다. `password`는 **최소 8자**.

| 필드 | 필수 | 설명 |
|---|---|---|
| `agreed_terms` · `agreed_privacy` | ✅ | 둘 다 `true`가 아니면 `400 TERMS_REQUIRED`. 화면에서도 막지만 서버가 최종입니다 |
| `email_ticket` | — | `/auth/email/verify`가 준 티켓. 티켓의 이메일과 `email`이 같아야 인정됩니다 |

**응답이 두 가지입니다.**

```
티켓 있음(이메일 인증 완료) → 201 { "access_token": "…", "refresh_token": "…" }   즉시 로그인
티켓 없음                    → 201 { "message": "인증 메일을 보냈습니다. 메일함을 확인해 주세요." }
```

티켓 없이 가입하면 토큰을 주지 않습니다 — 메일 링크로 인증을 마쳐야 로그인됩니다.

> SMTP가 설정되지 않으면 메일을 보내지 않고 **인증 링크·인증번호를 서버 콘솔에 찍습니다.** 데모 당일 메일이 막혀도 시연이 죽지 않게 하기 위한 이중화입니다.

## `GET /auth/verify`

메일의 "인증하기" 버튼이 가는 곳. 쿼리 `?token=...`

→ `302` → `{FRONTEND_URL}/app/input?code=<60초 1회용 코드>`

**JWT를 URL에 싣지 않습니다.** 방문기록에 코드가 남아도 이미 소진돼 쓸모없습니다 (OAuth authorization code와 같은 방식).

## `POST /auth/exchange`

```json
{ "code": "..." }
```

→ `{ "access_token": "...", "refresh_token": "..." }`

**프론트가 할 일**: `/app/input` 진입 시 `?code=`가 있으면 이걸 호출해 토큰을 저장하고 주소창에서 코드를 지웁니다. 새 페이지는 필요 없습니다.

## `POST /auth/login`

```json
{ "student_id": "202512345", "password": "hunter22!" }
```

→ `{ "access_token": "...", "refresh_token": "..." }`

인증 전이면 **403 `EMAIL_NOT_VERIFIED`** — 이 코드로 재발송 버튼을 띄우세요.

## `POST /auth/resend`

```json
{ "email": "dj@mjc.ac.kr" }
```

→ `200 { "message": "가입된 이메일이라면 인증 메일을 다시 보냈습니다." }`

**가입 여부를 알려주지 않습니다** (계정 열거 방지). 재발송하면 이전 링크는 무효가 됩니다.

## `POST /auth/refresh`

```json
{ "refresh_token": "..." }
```

→ `{ "access_token": "..." }`

액세스 토큰 유효기간이 12시간이라 시연 중에는 쓸 일이 없습니다.

---

# 내 정보

## `GET /me`

```json
{ "student_id": "202512345", "name": "이동제", "email": "dj@mjc.ac.kr",
  "dept_id": "itc", "email_verified": true,
  "completed_courses": ["itc-자료구조"],
  "saved_roadmaps": [{ "target_job": "...", "roadmap": { } }] }
```

## `PUT /me/courses`

```json
{ "completed_courses": ["itc-자료구조", "itc-운영체제"] }
```

**덮어씁니다** (추가가 아님). `course_id` 배열입니다.

## `POST /me/roadmaps`

```json
{ "target_job": "시스템관리·운용엔지니어", "roadmap": { } }
```

→ `201 { "target_job": "..." }`

**같은 직무로 다시 저장하면 덮어씁니다** — 시연 중 여러 번 눌러도 목록이 쌓이지 않습니다.

---

## 동결 스펙과 다른 것 — 요약

설계서 반영은 이슈 #24에서 진행 중입니다.

| # | 차이 | 왜 |
|---|---|---|
| 1 | `details[].fix` 추가 | `shortfall`만으로는 재생성이 아무 과목이나 채운다 |
| 2 | `details[].label` 추가 | 화면에 `"major_credits"`를 띄울 수 없다 |
| 3 | `validation.semesters` 추가 | 졸업요건 4종 중 학기만 요약에서 빠져 있었다 |
| 4 | `validation.remaining_credits` 추가 + 총학점을 미달로 안 잡음 | 교육과정표에 교양선택·일반선택이 없어 판정 근거가 없다 |
| 5 | `liberal_credits` → `liberal_required` | 교양 10 → 교양필수 3 |
| 6 | `GET /depts`에 `talent_types`·`careers`·`certificates` | 프론트가 드롭다운을 하드코딩하지 않으려면 필요하다 |
| 7 | `label_mismatches`를 최상위로 | 특정 직무의 속성이 아니라 학과 데이터 전체의 성질이다 |
| 8 | 에러 형식 `{error:{code,message}}` (422 포함) | 프론트 `lib/api.js`가 읽는 형식 |
| 9 | `POST /roadmap` 400 `UNKNOWN_JOB` | 오타를 조용히 통과시키면 "직무 역산"이 거짓이 된다 |
| 10 | `signup`에 `email` | 이메일 인증에 필수 |
| 11 | `engine` · `job_match` · `unknown_courses` 추가 | 무엇이 돌았고 무엇이 어긋났는지 숨기지 않는다 |
