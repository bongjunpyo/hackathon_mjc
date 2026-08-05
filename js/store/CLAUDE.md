# CLAUDE.md — 데이터 계층 (효민)

루트 `CLAUDE.md`의 공통 계약이 먼저다. 이 문서는 그 위에 얹는 담당 규칙이다.

## 담당

`js/store/store.js` 한 파일. 전역 객체 `Store`로 노출한다.

**이 파일이 유일하게 localStorage를 만지는 곳이다.** 다른 누구도 `localStorage.getItem`을 쓰지 않는다.
저장 형식이 바뀌어도 이 파일만 고치면 되게 만든다.

## 책임

- localStorage 읽기·쓰기 (키 `"activities"`)
- 스키마 — 어떤 필드가 있고 어떤 타입인지
- 검증 — 잘못된 입력을 저장 전에 막는다
- JSON 내보내기·가져오기
- 샘플 데이터 생성

## 공개 함수 (계약, 혼자 바꾸지 않는다)

```js
Store.getAll()              // → Activity[]  createdAt 내림차순 (최신순)
Store.add(input)            // → { ok: true, activity } | { ok: false, errors }
Store.remove(id)            // → boolean  (없는 id면 false)
Store.exportJson()          // → string
Store.importJson(text)      // → { ok, added, skipped, message }
Store.seedSampleData()      // → number  (생성된 건수)
Store.clearAll()            // → void
```

- `add`는 `id`와 `createdAt`을 **여기서** 만든다. UI가 넘기지 않는다.
  `id`는 `crypto.randomUUID()` 또는 `Date.now()+랜덤`. 중복만 안 나면 된다.
- `errors`는 `{ 필드명: '한글 메시지' }` 형태. 키는 필드명 그대로:
  `title`, `date`, `memberCount`, `category`, `durationMin`, `weightKg`, `kcalIn`
- 에러 메시지는 사용자가 그대로 읽을 문장으로 쓴다. `"참여 인원은 1명 이상이어야 합니다"`

## 검증 규칙

| 필드 | 규칙 | 미입력 |
|---|---|---|
| `title` | 공백 제거 후 1자 이상 | 거부 |
| `date` | `YYYY-MM-DD`, 오늘 이후 날짜 거부 | 거부 |
| `place` | 제한 없음 | 허용 |
| `memberCount` | 1 이상의 **정수** | 거부 |
| `memo` | 제한 없음 | 허용 |
| `category` | `'유산소' \| '근력' \| '스트레칭'` | 거부 |
| `durationMin` | 1 이상의 정수 | 거부 |
| `weightKg` | 0보다 큰 수 | **허용** |
| `kcalIn` | 0보다 큰 수 | **허용** |

**빈 문자열은 `0`이 아니라 미입력이다.** `Number('')`는 `0`이라 그냥 넘기면 체중 0kg가 저장되고
준표의 평균 계산이 무너진다. 미입력이면 필드를 아예 넣지 말거나 `null`로 넣는다 — 둘 중 하나로 통일하고 여기 적어둔다.

정수 검사는 `Number.isInteger(n)`를 쓴다. `parseInt('3.7')`은 `3`이 되므로 검사 통과처럼 보인다.

날짜 비교는 문자열끼리 한다 (`input.date > todayString`). `new Date()` 비교는 시:분 때문에 오늘이 미래로 잡힌다.

## 샘플 데이터

`seedSampleData()`는 **통계 화면을 시연하기 위한 기능**이다. 다음을 지킨다.

- 최근 30일 범위로 20~25건 생성. 매일 만들지 않는다 (쉬는 날이 있어야 자연스럽다)
- `category`는 세 값이 골고루 섞이게
- `weightKg`는 **완만하게 감소**하는 값으로 만든다. 랜덤이면 추이 그래프가 의미 없어 보인다
- 일부 기록은 `weightKg` / `kcalIn`을 **비워둔다.** 준표 쪽 "없는 값 건너뛰기"가 실제로 테스트된다
- 생성한 기록에 표시를 남긴다 (예: `memo` 앞에 `[샘플]`)
- **자동 실행 금지.** 버튼 클릭으로만 돈다. 호출 전 확인은 UI가 한다

## 가져오기

`importJson`은 시스템 경계다. 남이 준 파일을 믿지 않는다.

- JSON 파싱 실패 → `{ ok: false, message }`. 예외를 밖으로 던지지 않는다
- 배열이 아니면 거부
- 각 항목을 `add`와 **같은 검증**에 태운다. 통과 못 한 건 `skipped`로 세고 나머지는 넣는다
- `id`가 겹치면 새로 발급한다

## 하지 말 것

- `alert` / `confirm` / `document` 사용. 이 파일은 화면을 모른다
- 담당 폴더 밖 파일 수정
- 검증을 UI에 미루는 것. `required` 속성은 편의일 뿐 방어선이 아니다
- 명세서 고정 7필드 이름 변경·삭제

## 검증 방법 (커밋 전 직접 확인)

콘솔에서 돌려보고 결과를 커밋 본문에 한 줄로 남긴다.

```js
Store.add({ title: '', date: '2026-08-05', memberCount: 5, category: '유산소', durationMin: 30 })
// → ok:false, errors.title 있어야 함

Store.add({ title: '러닝', date: '2026-12-31', memberCount: 5, category: '유산소', durationMin: 30 })
// → ok:false, errors.date  (미래 날짜)

Store.add({ title: '러닝', date: '2026-08-05', memberCount: 2.5, category: '유산소', durationMin: 30 })
// → ok:false, errors.memberCount  (소수)

Store.add({ title: '러닝', date: '2026-08-05', memberCount: 0, category: '유산소', durationMin: 30 })
// → ok:false  (0명)

Store.add({ title: '러닝', date: '2026-08-05', memberCount: 5, category: '수영', durationMin: 30 })
// → ok:false, errors.category  (허용 안 된 값)

Store.add({ title: '러닝', date: '2026-08-05', memberCount: 5, category: '유산소', durationMin: 30, weightKg: '' })
// → ok:true 이고, 저장된 기록에 weightKg가 0으로 들어가면 안 됨

Store.getAll()[0]   // 방금 넣은 게 맨 앞 (최신순)
```

## 작업 순서

1. `getAll` / `save` (내부) — 빈 localStorage에서 `[]` 반환되는지
2. `add` + 필수 4종 검증 → **커밋**
3. 확장 필드 검증 → **커밋**
4. `remove` → **커밋**
5. `seedSampleData` → **커밋** (여기까지 되면 준표가 실데이터로 작업 가능)
6. `exportJson` / `importJson` → **커밋**

3번까지 끝나면 동제·준표에게 알린다. 두 사람이 거기서부터 막힌 걸 풀 수 있다.
