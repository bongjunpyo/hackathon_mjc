"""인증 메일 발송.

SMTP 설정이 있으면 진짜 메일을 보내고, 없으면 콘솔에 링크를 찍는다.
데모 당일 메일이 막혀도 시연이 죽지 않게 하기 위한 이중화다.
"""

import os
import smtplib
import sys
from email.message import EmailMessage
from email.utils import formataddr
from html import escape

import envfile

# 아래 SMTP_* 는 import 시점에 읽힌다 — main.py의 load()만 믿으면 늦는다
envfile.load()


def _env(key, default=""):
    """`.env`에 `KEY=` 로 비워 둔 값은 없는 것으로 친다.

    os.getenv(key, default)는 **키가 없을 때만** 기본값을 준다. .env.example을 복사해
    쓰면 안 채운 줄이 빈 문자열로 남는데, 그게 기본값을 밀어내고 들어왔다 —
    SMTP_FROM이 ''가 되어 `MAIL FROM:<>`(빈 발신자)로 나가고 서버가 거절했다.
    """
    return os.getenv(key) or default


SMTP_HOST = _env("SMTP_HOST")
SMTP_PORT = int(_env("SMTP_PORT", "587"))
SMTP_USER = _env("SMTP_USER")
SMTP_PASSWORD = _env("SMTP_PASSWORD")
SMTP_FROM = _env("SMTP_FROM", SMTP_USER or "no-reply@mjc.ac.kr")
SMTP_FROM_NAME = _env("SMTP_FROM_NAME", "MJC 취업 로드맵")
def _flag(key, default):
    value = _env(key)
    return value.lower() in ("1", "true", "yes") if value else default


# 465는 처음부터 TLS(SSL), 587은 평문으로 열고 STARTTLS로 올린다. 릴레이마다 다르다.
# 로컬 테스트용 메일 서버(Mailpit 등)는 TLS를 아예 안 받으므로 끌 수 있어야 한다
SMTP_USE_SSL = _flag("SMTP_USE_SSL", False)
SMTP_USE_TLS = _flag("SMTP_USE_TLS", True)

# 콘솔 모드에서 보낸 메일. 테스트가 여기서 링크를 꺼낸다
outbox = []

SUBJECT = "[MJC 취업 로드맵] 이메일 인증"

BODY = """{name}님, 반갑습니다.

아래 버튼을 눌러 이메일 인증을 완료해 주세요. 인증하면 바로 로그인됩니다.

    {link}

이 링크는 30분 뒤 만료됩니다. 만료되면 로그인 화면에서 재발송할 수 있습니다.
본인이 요청하지 않았다면 이 메일을 무시하세요.
"""

HTML = """<div style="font-family:system-ui,sans-serif;max-width:480px">
  <p>{name}님, 반갑습니다.</p>
  <p>아래 버튼을 눌러 이메일 인증을 완료해 주세요. 인증하면 바로 로그인됩니다.</p>
  <p><a href="{link}"
        style="display:inline-block;padding:12px 24px;background:#002D65;color:#fff;
               border-radius:8px;text-decoration:none;font-weight:700">이메일 인증하기</a></p>
  <p style="color:#6B84A0;font-size:13px">
    이 링크는 30분 뒤 만료됩니다. 만료되면 로그인 화면에서 재발송할 수 있습니다.<br>
    본인이 요청하지 않았다면 이 메일을 무시하세요.
  </p>
</div>"""


def configured():
    """호스트만 있으면 보낸다 — 인증 없는 사내 릴레이도 있다."""
    return bool(SMTP_HOST)


def _compose(to, subject, text, html):
    message = EmailMessage()
    message["Subject"] = subject
    # 표시 이름과 주소를 따로 받아 조립한다. 주소만 넣으면 받은 편지함에 계정 이메일이
    # 그대로 뜬다 — 학생이 받는 메일이라 보내는 사람이 누구인지 읽혀야 한다
    message["From"] = formataddr((SMTP_FROM_NAME, SMTP_FROM))
    message["To"] = to
    message.set_content(text)
    message.add_alternative(html, subtype="html")
    return message


def _deliver(message):
    connect = smtplib.SMTP_SSL if SMTP_USE_SSL else smtplib.SMTP
    with connect(SMTP_HOST, SMTP_PORT, timeout=10) as smtp:
        if not SMTP_USE_SSL and SMTP_USE_TLS:
            smtp.starttls()
        if SMTP_USER:
            smtp.login(SMTP_USER, SMTP_PASSWORD)
        smtp.send_message(message)


def _console(text):
    """콘솔 폴백 출력. 인코딩 때문에 요청이 죽는 일이 없어야 한다.

    한국어 Windows 기본 코드페이지(cp949)는 못 찍는 문자가 있고, 그러면 print가
    UnicodeEncodeError를 던져 가입 요청이 통째로 500이 됐다. 아래 SMTP 예외 메시지처럼
    내용을 우리가 정할 수 없는 값도 여기로 들어온다 — 폴백이 요청을 죽이면
    "메일이 막혀도 시연은 산다"는 이 함수의 존재 이유가 뒤집힌다.
    """
    try:
        print(text, flush=True)
    except UnicodeEncodeError:
        encoding = sys.stdout.encoding or "utf-8"
        print(text.encode(encoding, "replace").decode(encoding), flush=True)


def send_verification(to, name, link):
    outbox.append({"to": to, "name": name, "link": link})

    # 버퍼링되면 서버를 파이프로 띄웠을 때 링크가 영영 안 보인다. SMTP가 없으면 유일한 전달 경로다
    if not configured():
        _console(f"\n[mailer] SMTP 미설정 - 콘솔로 대체\n  받는사람: {to}\n  인증링크: {link}\n")
        return False

    # 이름은 사용자가 넣은 값이다. HTML 본문에 그대로 끼우지 않는다
    message = _compose(
        to,
        SUBJECT,
        BODY.format(name=name, link=link),
        HTML.format(name=escape(name), link=escape(link, quote=True)),
    )

    try:
        _deliver(message)
        return True
    except Exception as e:
        # 메일 실패가 회원가입을 실패시키면 안 된다. 링크는 콘솔에 남는다
        _console(f"\n[mailer] 발송 실패({e}) - 콘솔로 대체\n  인증링크: {link}\n")
        return False


CODE_SUBJECT = "[MJC 취업 로드맵] 이메일 인증번호"

CODE_BODY = """인증번호는 {code} 입니다.

회원가입 화면의 '인증번호' 칸에 입력해 주세요.
이 번호는 10분 뒤 만료됩니다. 본인이 요청하지 않았다면 이 메일을 무시하세요.
"""

CODE_HTML = """<div style="font-family:system-ui,sans-serif;max-width:480px">
  <p>회원가입 화면의 '인증번호' 칸에 아래 번호를 입력해 주세요.</p>
  <p style="font-size:32px;font-weight:800;letter-spacing:8px;color:#002D65">{code}</p>
  <p style="color:#6B84A0;font-size:13px">
    이 번호는 10분 뒤 만료됩니다.<br>본인이 요청하지 않았다면 이 메일을 무시하세요.
  </p>
</div>"""


def send_code(to, code):
    """인증번호 메일. 링크 방식(send_verification)과 달리 화면을 떠나지 않는다."""
    outbox.append({"to": to, "code": code})

    if not configured():
        _console(f"\n[mailer] SMTP 미설정 - 콘솔로 대체\n  받는사람: {to}\n  인증번호: {code}\n")
        return False

    message = _compose(
        to, CODE_SUBJECT, CODE_BODY.format(code=code), CODE_HTML.format(code=escape(code))
    )

    try:
        _deliver(message)
        return True
    except Exception as e:
        # 메일 실패가 가입을 막으면 안 된다. 번호는 콘솔에 남는다
        _console(f"\n[mailer] 발송 실패({e}) - 콘솔로 대체\n  인증번호: {code}\n")
        return False
