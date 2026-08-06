# 이메일 인증 설정

회원가입 화면에서 **인증번호 6자리**를 받아 넣어야 가입이 끝난다. 그 번호를 실제 메일로 보내려면 SMTP가 필요하다.

**설정하지 않아도 개발은 된다.** `SMTP_HOST`가 비어 있으면 메일을 보내지 않고 인증번호를 **서버 콘솔에 찍는다.** 서버를 직접 띄운 사람은 자기 터미널에서 번호를 꺼내 쓰면 된다.

```
[mailer] SMTP 미설정 - 콘솔로 대체
  받는사람: you@example.com
  인증번호: 246057
```

다만 **다른 사람이 가입하려면 콘솔이 아니라 메일함으로 가야 한다.** 그때 아래를 설정한다.

## 추천: Brevo (무료 300건/일)

Gmail보다 Brevo를 권한다. Gmail은 계정 비밀번호가 아니라 **앱 비밀번호**(2단계 인증 선행)를 따로 발급해야 하고, 발송 제한과 스팸 판정이 더 빡빡하다. Brevo는 트랜잭션 메일용 서비스라 이 용도에 맞다.

SMTP로 붙였으므로 Brevo가 아니어도 **SMTP 정보를 주는 서비스면 같은 환경변수로 교체**된다.

### 설정 순서

1. Brevo 계정을 만들고 **발신자 이메일을 인증**한다.
2. **SMTP & API → SMTP** 메뉴에서 서버 주소·포트·로그인·**SMTP key**를 확인한다.
3. `server/.env`에 아래를 채운다.

```env
SMTP_HOST=smtp-relay.brevo.com
SMTP_PORT=587
SMTP_USER=<Brevo SMTP 로그인 이메일>
SMTP_PASSWORD=<Brevo SMTP key>
SMTP_FROM=<1번에서 인증한 발신자 주소>
SMTP_FROM_NAME=MJC 취업 로드맵
```

> **`SMTP_PASSWORD`에는 SMTP key를 넣는다.** Brevo API key도, 계정 비밀번호도 아니다. Brevo 문서도 SMTP user는 로그인 이메일, SMTP password는 SMTP key라고 안내한다.

### 465 포트를 쓰는 릴레이라면

```env
SMTP_PORT=465
SMTP_USE_SSL=true
```

587은 평문으로 열고 STARTTLS로 올리고, 465는 처음부터 TLS다. 비워두면 587/STARTTLS로 동작한다.

## 빈 줄로 두면 안 되는 값

`.env`에 `KEY=`로 **비워 둔 줄은 값이 없는 것으로 친다** (`mailer._env`). `.env.example`을 복사해 일부만 채워도 나머지가 기본값으로 돌아온다.

전에는 그렇지 않아서, `SMTP_FROM=`을 비워 두면 발신 주소가 빈 문자열이 되고 `MAIL FROM:<>`(빈 발신자)로 나가 서버가 거절했다 — **설정은 맞는데 메일이 안 오는** 상태였다. 같은 함정이 `JWT_SECRET`에도 있었다.

## 발송이 실패해도 가입은 된다

SMTP가 거절하거나 끊기면 예외를 삼키고 **인증번호를 콘솔에 남긴 뒤** 정상 응답을 낸다. 메일 사고가 가입을 막지 않게 하려는 것이다.

대신 **화면은 성공했을 때와 똑같이 "인증번호를 보냈습니다"라고 말한다.** 메일이 안 오면 서버 콘솔에 `[mailer] 발송 실패(...)`가 찍혔는지부터 본다.

## 인증번호가 자꾸 만료된다면

인증번호와 발급 티켓은 **프로세스 메모리**에 있다 (`auth.py`의 `_email_codes`·`_email_tickets`). `fastapi dev`는 `--reload`라 **누군가 파일을 저장할 때마다 서버가 재시작되고 발급된 번호가 전부 사라진다.**

여럿이 가입을 시연하는 동안에는 reload 없이 띄운다.

```bash
uv run uvicorn main:app --host 0.0.0.0 --port 8000
```

## 다른 PC에서 접속시킬 때

메일 **링크** 방식(`/auth/resend`, 인증번호 없이 가입한 경우)은 `BACKEND_URL`을 쓴다. 기본값이 `http://localhost:8000`이라 **받는 사람 본인 PC**를 가리키므로, 다른 사람이 열면 열리지 않는다. 인증 후 리다이렉트는 `FRONTEND_URL`을 쓴다.

같은 네트워크의 다른 PC에서 접속시키려면 둘 다 실제 주소로 바꾼다.

```env
BACKEND_URL=http://192.168.0.10:8000
FRONTEND_URL=http://192.168.0.10:8000
```

> 제출 빌드는 FastAPI가 `web/dist`를 함께 서빙하므로 프론트도 **8000**이다. `5173`은 `npm run dev`를 따로 띄웠을 때만이다.

## 사용자 흐름

1. 가입 화면에서 이메일을 넣고 **인증번호 받기** → `POST /auth/email/code`
2. 메일(또는 콘솔)의 6자리를 입력 → `POST /auth/email/verify` → 30분짜리 `email_ticket`
3. 티켓을 들고 가입 → `POST /auth/signup` → 인증까지 끝났으므로 **바로 토큰 발급**
4. 티켓 없이 가입하면 인증 **링크** 메일이 나가고, 링크를 눌러야 로그인된다
