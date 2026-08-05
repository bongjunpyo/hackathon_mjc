# CLAUDE.md — 데이터 처리 (준표)

루트 `CLAUDE.md`의 공통 계약이 먼저다. 이 문서는 그 위에 얹는 담당 규칙이다.

## 담당

`js/analytics/analytics.js` 한 파일. 전역 객체 `Analytics`로 노출한다.

**전부 순수 함수다.** 인자로 받은 배열만 읽고, 아무것도 바꾸지 않고, 값을 돌려준다.
DOM도 localStorage도 만지지 않는다. 그래서 `Store`가 아직 없어도 배열만 직접 만들어 지금 작업할 수 있다.

## 공개 함수 (계약, 혼자 바꾸지 않는다)

```js
Analytics.summary(list)        // → { totalCount, totalMembers, avgMembers, totalMin, avgMin }
Analytics.monthlyCount(list)   // → [{ month: '2026-08', count }]        month 오름차순
Analytics.byCategory(list)     // → [{ category, count, totalMin }]      count 내림차순
Analytics.weightTrend(list)    // → [{ date, weightKg }]                 date 오름차순
Analytics.kcalBalance(list)    // → [{ date, kcalIn, kcalOut, net }]     date 오름차순
```

## 핵심 규칙 — 없는 값은 건너뛴다

`weightKg`와 `kcalIn`은 **선택 입력이라 없는 기록이 섞여 있다.** 샘플 데이터에도 일부러 빈 게 들어온다.

- 없는 값은 **0으로 취급하지 않는다.** 집계 대상에서 아예 제외한다
- 평균의 분모는 전체 건수가 아니라 **값이 있는 건수**다
- 값이 하나도 없으면 빈 배열 `[]`을 돌려준다. `NaN`이나 `null`을 돌려주지 않는다
- 빈 배열이 들어와도 죽지 않는다. `summary([])`는 전부 `0`

`0 / 0`은 `NaN`이고, `NaN`이 화면에 찍히면 그대로 감점 스크린샷이 된다. 나누기 전에 분모를 확인한다.

## 칼로리 소모 추정

`kcalOut`은 저장된 값이 아니라 **여기서 계산하는 추정치**다. `durationMin`과 `category`로 낸다.

```js
const KCAL_PER_MIN = { '유산소': 10, '근력': 6, '스트레칭': 3 };
```

- 근거 없는 정밀도를 흉내내지 않는다. 이 표는 근사치이고, 그 사실을 화면에도 한 줄 적는다
- 체중을 반영한 MET 공식으로 정교하게 만들지 않는다 — 시간이 없고 데모에 보이지 않는다
- `category`가 표에 없으면 그 기록은 `kcalOut` 계산에서 제외한다
- `net = kcalIn - kcalOut`. `kcalIn`이 없는 날은 `kcalIn: null`, `net: null`로 두고 **0으로 채우지 않는다**

## 날짜 다루기

- `date`는 `'YYYY-MM-DD'` 문자열이다. `month`는 앞 7자를 자르면 된다 — `date.slice(0, 7)`
- 정렬은 문자열 비교로 충분하다. `Date` 객체로 변환하지 않는다
- 같은 날짜에 기록이 2건 이상 올 수 있다. `weightTrend`는 그날 **마지막 기록** 하나만 쓰거나 평균을 낸다 — 어느 쪽인지 정하고 이 문서에 적는다
- `kcalBalance`는 같은 날짜를 **합산**한다 (하루에 운동 2번 하면 소모도 2번)

## 하지 말 것

- `document` / `localStorage` / `Store` 참조. 이 파일은 배열 하나만 안다
- 인자로 받은 배열을 `sort`로 직접 뒤집는 것 — 원본이 바뀐다. `[...list].sort(...)`
- 화면에 어떻게 그릴지 결정하는 것. 색·라벨·단위 표기는 동제 담당
- 담당 폴더 밖 파일 수정

## 검증 방법 (커밋 전 직접 확인)

`Store`를 기다리지 말고 배열을 손으로 만들어 테스트한다.

```js
const t = [
  { date: '2026-07-30', category: '유산소',   durationMin: 30, memberCount: 5, weightKg: 70.0, kcalIn: 2000 },
  { date: '2026-08-01', category: '근력',     durationMin: 60, memberCount: 3, weightKg: 69.5 },
  { date: '2026-08-01', category: '스트레칭', durationMin: 20, memberCount: 8 },
  { date: '2026-08-03', category: '유산소',   durationMin: 45, memberCount: 4, kcalIn: 1800 },
];

Analytics.summary([])         // → 전부 0, NaN 없어야 함
Analytics.monthlyCount(t)     // → 2026-07:1, 2026-08:3
Analytics.weightTrend(t)      // → 2건만 (weightKg 없는 2건 제외)
Analytics.kcalBalance(t)      // → 8/01은 durationMin 60+20 합산, kcalIn 없으니 net은 null
Analytics.byCategory(t)       // → 유산소 count 2 / totalMin 75
```

**빈 배열과 전부-미입력 케이스를 반드시 돌려본다.** 여기서 `NaN`이 안 나오는 게 이 파일의 핵심이다.
확인한 내용을 커밋 본문에 한 줄로 남긴다.

## 작업 순서

1. `summary` — 빈 배열 방어 포함 → **커밋**
2. `monthlyCount` / `byCategory` → **커밋**
3. `weightTrend` — 미입력 제외 → **커밋**
4. `kcalBalance` — `KCAL_PER_MIN` 표 + 날짜 합산 → **커밋**

`store.js`가 없어도 1~4를 다 할 수 있다. **효민을 기다리지 말고 지금 시작한다.**
효민의 `seedSampleData()`가 나오면 그때 실데이터로 한 번 더 돌려본다.
