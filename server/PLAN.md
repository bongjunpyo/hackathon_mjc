# server 구현 계획 (P2)

> 작성 2026-08-06 19:15경 · 제출 11:40 · 남은 약 16시간
> 계약 원본은 `../docs/DESIGN.md` §5 (동결). 이 문서와 어긋나면 설계서가 이긴다.

## 원칙 세 줄

1. **코어(게스트 → 입력 → 로드맵)가 무엇 때문에도 깨지지 않는다.** DB·인증·LLM 장애가 코어를 죽이면 안 된다.
2. **P1·P3를 기다리지 않는다.** 데이터는 픽스처로, LLM은 가짜 생성기로 먼저 짠다.
3. **테스트 먼저.** 룰·루프처럼 판정이 있는 코드는 변이 검사까지 한다.

## 전체 그림

```
POST /roadmap
   │
   ├─ catalog.load(dept_id)          data/*.json → 학과 교육과정 + 졸업요건 파라미터
   ├─ catalog.resolve(completed[])   course_id → {credits, category}
   │
   └─ loop.generate()                ┌─────────────────────────────┐
        ├─ agent.build_prompt()      │  생성 → 검증 → 미달이면      │
        ├─ LLM 호출                   │  details를 프롬프트에 실어    │
        ├─ validator.validate()      │  재생성 (최대 3회)           │
        └─ 초과 시 부분 반환           └─────────────────────────────┘

GET /report/{dept_id}
   └─ report.coverage()              talent_type ↔ 목표 직무 매칭 → 커버리지·결손·라벨 불일치
```

## 진행 상황

아래는 계획 시점의 기록이다. **8단계 전부 완료**됐고, 확인 방법은 각 줄에 적었다.

| | 단계 | 상태 | 확인 |
|---|---|---|---|
| **0** | [졸업요건 검증기](#0-졸업요건-검증기) | ✅ | 변이 검사 — 룰을 일부러 깨면 테스트가 잡는다 |
| **1** | [카탈로그 로더](#1-카탈로그-로더) | ✅ | `GET /depts` → 34개 학과 |
| **2** | [재생성 루프](#2-재생성-루프) | ✅ | 가짜 생성기로 1~3회 재생성 검증 |
| **3** | [FastAPI 표면](#3-fastapi-표면) | ✅ | 코어 3종 + 인증 9종, 정적 mount 마지막 |
| **4** | [로드맵 에이전트 (LLM 실연결)](#4-로드맵-에이전트-llm-실연결) | ✅ | 실 Claude API 32초 · `engine=llm` · `passed=True` |
| **5** | [실데이터 연결](#5-실데이터-연결) | ✅ | 진로↔인재양성유형 매핑 (이슈 #40) — 12과목 연결 |
| **6** | [트랙 B 정합도](#6-트랙-b-정합도) | ✅ | `GET /report/itc` → 직무 6종 커버리지 |
| **7** | [인증 · DB](#7-인증--db-부가) | ✅ | `verify_db.py` 실 PostgreSQL 13건 통과 |
| **8** | [검증 지표 · 문서](#8-검증-지표--문서) | ✅ | `metrics.py` 274 시나리오 · 15.0% → 99.3% |

테스트 **150개** 통과. 지표·명세는 [README](README.md) · [주요 기능](FEATURES.md) · [API 명세](API.md).

> **메인 엔진은 규칙(planner)이다** (PR #53, 8/7 02시 결정). LLM은 `MJC_ENGINE=llm`일
> 때만 도는 비교 데모용 보조다. 4단계는 그 보조 경로의 확인 기록이다.

---

## 0. 졸업요건 검증기

**완료.** `validator.py` · 테스트 12개 · 변이 10종 통과. PR #11.

```python
validate_roadmap(semesters, years, completed=None, completed_semesters=0)
→ { passed, total_credits, liberal_credits, major_credits, semesters, details[] }
```

남은 것: 교양필수(인성채플 1 · 성경과삶 2) 룰. `Course.required == True`로 데이터가 들고 오므로 **P1이 Tier 1 원본 확인을 끝내면** `REQUIREMENTS`에 한 줄 + 테스트 한 쌍.

---

## 1. 카탈로그 로더

`data/depts/*.json`을 읽는 **유일한 창구**. 여기가 시스템 경계다.

### 산출물

`catalog.py`

```python
load_dept(dept_id)        -> dict        # 학과 교육과정 전체
list_depts()              -> list[dict]  # GET /depts 응답 재료
resolve(dept_id, course_ids) -> list[dict]  # course_id → {course_id, name, credits, category}
```

### 경계 검증 — 로드 시점에 죽인다

CLAUDE.md "검증은 시스템 경계에서만"이 여기다. 새벽 5시에 *"왜 이 과목이 미이수로 나오지"*를 쫓는 것보다 지금 죽는 게 싸다.

| 검사 | 실패 시 |
|---|---|
| `course_id` 학과 내 유일 | 즉시 예외 + 중복 id 나열 |
| `course_id` 빈 값 없음 | 즉시 예외 |
| `category` ∈ {전공, 교양, 일반선택} | 즉시 예외 + 위반 과목명 |
| `years` ∈ {2, 3} | 즉시 예외 (검증기 `REQUIREMENTS` 키) |

`resolve()`에서 **없는 `course_id`는 조용히 버리지 않는다.** 프론트 체크박스와 데이터가 어긋난 신호이므로 로그를 남기고 목록에 담아 반환한다.

### 데이터가 아직 없다

`data/depts/*.json`은 미생성 상태(현재 `data/raw/` PDF만). **`tests/fixtures/itc.json`을 직접 만들어** 그걸로 개발한다. 스키마는 `pipeline/schema.py`의 `DeptCurriculum`을 그대로 따른다.

### 테스트

- 정상 로드 → 과목 수·학점 합
- 중복 `course_id` → 예외, 메시지에 중복 id 포함
- 빈 `course_id` → 예외
- 잘못된 `category` → 예외
- `resolve()`가 없는 id를 별도로 보고

### 완료 기준

픽스처로 `load_dept("itc")` → `validate_roadmap`에 넣을 수 있는 과목 배열이 나온다.

---

## 2. 재생성 루프

**이게 발표 훅이다.** 설계서 §11 *"LLM 위에 졸업요건 검증기를 얹었습니다"* 의 실체.

### 산출물

`loop.py`

```python
generate_roadmap(spec, generate_fn, max_retries=3)
→ { semesters, validation, attempts }
```

`generate_fn`을 **인자로 받는다.** LLM을 직접 부르지 않는다 — 루프 로직을 API 키 없이, 초 단위로 테스트하기 위해서다. 실제 LLM은 4단계에서 주입한다.

### 흐름

```
attempt 1  generate_fn(spec)                  → validator → passed? 반환
attempt 2  generate_fn(spec, feedback=details) → validator → passed? 반환
attempt 3  generate_fn(spec, feedback=details) → validator → passed? 반환
초과       마지막 로드맵 + passed:false + details를 그대로 반환 (200, 에러 아님)
```

### details → 프롬프트

`fix` 필드가 여기서 쓰인다. `shortfall: 6`만 주면 LLM이 아무 과목이나 채운다.

```
이전 로드맵이 졸업요건에 미달했습니다. 아래를 고쳐서 다시 짜세요.
- 전공 학점: 60/66 → 전공 과목으로 6학점을 더 채우세요
- 교양 학점: 8/10 → 교양 과목으로 2학점을 더 채우세요
```

### 테스트 (가짜 생성기로)

| 테스트 | 시나리오 |
|---|---|
| 1회 성공 | 첫 생성이 통과 → `attempts == 1`, LLM 1회만 호출 |
| 2회째 성공 | 첫 미달, 둘째 통과 → `attempts == 2` |
| 3회 초과 | 계속 미달 → `attempts == 3`, `passed: false`, **예외 아님** |
| 피드백 전달 | 2회차 `generate_fn`이 받은 feedback에 `fix` 문자열이 들어있다 |
| 호출 횟수 상한 | 4회 이상 호출되지 않는다 |

### 리스크

`max_retries`를 넘겨도 **200으로 반환**해야 한다. 예외를 던지면 P3 화면이 "여기까지 충족, 이것이 부족"을 못 그린다. 테스트로 못 박는다.

---

## 3. FastAPI 표면

### 산출물

`main.py` · `errors.py`

```
GET  /depts              catalog.list_depts()
POST /roadmap            catalog → loop → 응답
GET  /report/{dept_id}   6단계 전까지 501 대신 빈 jobs + 안내
```

### 라우트 등록 순서 — 이거 틀리면 502

P3가 실제로 겪었다. 클라이언트 라우트 `/roadmap`이 API 경로와 겹쳐 프록시가 화면 요청을 백엔드로 넘겼다. P3는 화면을 `/app/*`로 옮겼고, **서버는 마운트 순서로 막는다.**

```python
# 1. API 라우트 먼저
app.include_router(api)
# 2. 정적 catch-all은 반드시 마지막
app.mount("/", StaticFiles(directory="../web/dist", html=True))
```

`web/dist`가 없어도 서버가 뜨게 한다 (P3 빌드 전에도 API 테스트 가능해야 함).

### 에러 형식 — P3가 이미 읽고 있다

```json
{ "error": { "code": "DEPT_NOT_FOUND", "message": "학과를 찾을 수 없습니다" } }
```

`lib/api.js`가 `err?.error?.message`를 읽는다. 동결 스펙엔 없지만 프론트 구현이 기준이다.

### 테스트

`TestClient`로 계약 형태만 — 값이 아니라 **키가 맞는지**.

- `GET /depts` → 리스트, 각 항목에 `dept_id, dept_name, years, tier`
- `POST /roadmap` → `semesters`, `validation` 6키 전부
- 없는 `dept_id` → 404 + `{error:{code,message}}`

### 완료 기준

`uv run fastapi dev main.py` 후 `curl -X POST localhost:8000/roadmap` 이 **동결 스펙 형태의 JSON**을 낸다. (내용은 가짜 생성기 산출물)

---

## 4. 로드맵 에이전트 (LLM 실연결)

3단계까지의 `generate_fn` 자리에 진짜 LLM을 꽂는다.

### 산출물

`agent.py`

```python
build_prompt(spec, feedback=None) -> str
generate(spec, feedback=None)     -> dict   # loop.generate_fn 시그니처
```

모델은 `claude-sonnet-5` (CLAUDE.md 스택 표).

### 프롬프트에 반드시 들어갈 것

| 재료 | 출처 | 왜 |
|---|---|---|
| 학과 전체 과목 목록 (`course_id` 포함) | `catalog.load_dept` | **id를 LLM이 짓지 않게** 목록에서 고르게 한다 |
| 목표 직무 | 입력 | |
| 이수 과목 · 현재 학년/학기 | 입력 | 남은 학기 수 계산 |
| 남은 학기 수 | 계산 | 몇 칸을 채울지 |
| **교양선택 버킷** | `liberal_elective_credits` | 교육과정표에 교양이 없다. **`category:"교양"` 블록으로 배치하라고 명시** — 빠뜨리면 교양 룰이 항상 미달 |
| 자격증 목록 | `certificates` | 학기별 취득 타이밍 배치 |
| 피드백 (재생성 시) | `details[].fix` | |

### 출력 강제

`semesters[].courses[]`는 **`course_id`만** 담게 한다. 이름을 받으면 매칭이 깨진다(이슈 #9와 같은 문제). 서버가 `catalog.resolve`로 이름·학점을 붙인다.

### 리스크

- **응답 시간**: 재시도 3회면 60초까지 간다. P3 프론트 타임아웃이 현재 4초 → PR #7 코멘트로 요청해둠. 서버도 스트리밍 없이 한 방에 받으므로 프롬프트를 짧게 유지한다.
- **JSON 파싱 실패**: 스키마 검증 실패도 재시도 사유에 포함한다(졸업요건 미달과 같은 루프).

---

## 5. 실데이터 연결

P1의 `data/depts/*.json`이 나오면 픽스처를 갈아끼운다.

- 경계 검증(1단계)이 여기서 진짜로 일한다. **깨지면 P1에게 즉시 보고** — 조용히 우회하지 않는다
- Tier 1(정보통신공학과)로 데모 시나리오 한 줄기를 끝까지 통과시킨다
- `talent_type` 채움률을 센다 → 6단계 가능 여부 판단 재료

---

## 6. 트랙 B 정합도

`GET /report/{dept_id}` → `{ jobs: [{ job, coverage_pct, covered_courses, gaps, label_mismatches }] }`

### 선행 확인 — 착수 전 5분

`talent_type`이 **비어 있으면 트랙 B가 성립하지 않는다.** `pipeline/schema.py`에서 `str | None`이고 PDF `비고` 열에서 뽑는다.

```
Tier 1 학과의 talent_type 채움률을 먼저 센다
  ≥ 50%  → 계획대로 진행
  < 50%  → 07:00 컷 규칙대로 정적 HTML 리포트 1장으로 축소
```

### 계산

```
coverage_pct     = (직무 요구역량 중 학과 과목이 커버하는 비율)
covered_courses  = 그 직무에 매칭된 과목
gaps             = 커버 안 되는 요구역량
label_mismatches = talent_type 라벨과 실제 과목 내용이 어긋나는 사례
```

`label_mismatches`가 발표 재료다 — *"학교 라벨과 실제가 여기서 어긋납니다"* 1~2건이면 충분하다.

---

## 7. 인증 · DB (부가)

> **05:00 이후 착수. 10:00 미완이면 게스트 모드로 컷.**
> 컷이 진짜 컷이 되려면 **처음부터 떼어낼 수 있는 형태**로 붙여야 한다.

### 절대 규칙

- `/roadmap` · `/report` · `/depts`는 **토큰 유무와 무관하게 동작**한다
- 인증 코드가 코어 경로에 스며들면 컷 자체가 불가능해진다. 라우터를 파일 단위로 분리한다
- **DB 컨테이너가 안 떠도 코어는 산다.** 연결 실패를 앱 시작 실패로 만들지 않는다

### 산출물

| | |
|---|---|
| `docker-compose.yml` | postgres 하나. **저장소에 아직 없다** (CLAUDE.md는 이미 약속 중) |
| `db.py` | SQLAlchemy + psycopg, `create_all` (마이그레이션 없음) |
| `models.py` | users / completed_courses / saved_roadmaps |
| `auth.py` | JWT 액세스+리프레시, passlib 해싱 |

```
users             id, student_id(unique), name, dept_id, password_hash, created_at
completed_courses user_id, course_id, year, semester     ← course_name 아님 (이슈 #4)
saved_roadmaps    user_id, target_job, roadmap_json, created_at
```

### 엔드포인트 4종 (5종 아님)

`POST /auth/refresh`는 **만들지 않는다.** P3의 `lib/api.js`가 쓰지 않는다(PR #7 코멘트로 확인 요청함). 액세스 토큰 만료를 길게 잡는다. 확정되면 설계서 §5에서도 빼는 게 정직하다.

---

## 8. 검증 지표 · 문서

발표·README에 그대로 실린다. 몰아서 못 만든다.

### 검증기 효과 지표 (설계서 §9)

**재생성 루프 on/off 졸업요건 충족률 비교.** 이게 기술 점수 30점의 증거다.

설계서는 시나리오 50개인데 해당 슬롯이 새벽 5~7시다. **15개로 줄이자고 제안한다** — (학과 × 학년/학기 × 목표 직무) 조합 15개면 서사는 충분히 성립한다.

```
검증기 OFF (LLM 단독)  : 15개 중 N개 충족
검증기 ON  (재생성 루프): 15개 중 M개 충족
```

### `docs/AI_USAGE.md` 실패 사례 — 이미 3건 확보

`docs/`는 P1 담당이므로 **내용만 넘긴다.**

1. **`__pycache__` 스테일 바이트코드** — 변이본과 원본의 UTF-8 바이트 길이가 같아(`"교양"`→`"전공"`) mtime+size 기반 pyc 무효화가 변경을 놓쳤다. 복구 후에도 옛 바이트코드가 돌아 변이 검사 1차 결과 전체가 거짓이었다.
2. **`python` 스텁** — Windows Store 스텁이라 heredoc이 실행되지 않았고, 변이가 적용 안 된 채 "10 passed"가 나왔다. `uv run python`으로 교체.
3. **출력 필터가 경고를 가림** — 리팩터로 변이 스크립트의 탐색 패턴이 낡았는데 grep이 "패턴 못 찾음"을 걸러내, 변이 2종이 조용히 건너뛰어졌다.

세 건 다 **"초록불을 봤다"가 아무것도 증명하지 못한 사례**다. 하나의 교훈으로 묶인다.

---

## 리스크 요약

| | 리스크 | 대응 |
|---|---|---|
| 🔴 | 로드맵 응답 60초 → 프론트 4초 타임아웃 | PR #7에 요청 완료. 서버는 프롬프트 짧게 |
| 🔴 | 에이전트가 교양 블록을 빠뜨림 → 교양 룰 항상 미달 | 프롬프트에 명시 + 루프가 잡아 재생성 |
| 🟡 | `talent_type` 비어 트랙 B 불성립 | 착수 전 채움률 확인 → 미달 시 정적 리포트 |
| 🟡 | `data/depts/*.json` 지연 | 픽스처로 5단계까지 무관하게 진행 |
| 🟡 | JWT·DB가 코어를 잡아먹음 | 라우터 분리 + DB 실패가 앱을 죽이지 않게 |
| 🔵 | 교양필수 값 미확정 | 상수 한 줄 + 테스트 한 쌍이면 추가 가능 |

## 다음 한 걸음

**1단계 카탈로그 로더** — 픽스처 만들고 경계 검증부터. 2단계 루프가 여기 위에 얹힌다.
