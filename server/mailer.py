"""인증 메일 발송.

SMTP 설정이 있으면 진짜 메일을 보내고, 없으면 콘솔에 링크를 찍는다.
데모 당일 메일이 막혀도 시연이 죽지 않게 하기 위한 이중화다.
"""

import os
import smtplib
from email.message import EmailMessage
from html import escape

import envfile

# 아래 SMTP_* 는 import 시점에 읽힌다 — main.py의 load()만 믿으면 늦는다
envfile.load()

SMTP_HOST = os.getenv("SMTP_HOST")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
SMTP_FROM = os.getenv("SMTP_FROM", SMTP_USER or "no-reply@mjc.ac.kr")

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
    return bool(SMTP_HOST and SMTP_USER and SMTP_PASSWORD)


def send_verification(to, name, link):
    outbox.append({"to": to, "name": name, "link": link})

    # 버퍼링되면 서버를 파이프로 띄웠을 때 링크가 영영 안 보인다. SMTP가 없으면 유일한 전달 경로다
    if not configured():
        print(f"\n[mailer] SMTP 미설정 — 콘솔로 대체\n  받는사람: {to}\n  인증링크: {link}\n", flush=True)
        return False

    message = EmailMessage()
    message["Subject"] = SUBJECT
    message["From"] = SMTP_FROM
    message["To"] = to
    message.set_content(BODY.format(name=name, link=link))
    # 이름은 사용자가 넣은 값이다. HTML 본문에 그대로 끼우지 않는다
    message.add_alternative(
        HTML.format(name=escape(name), link=escape(link, quote=True)), subtype="html"
    )

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as smtp:
            smtp.starttls()
            smtp.login(SMTP_USER, SMTP_PASSWORD)
            smtp.send_message(message)
        return True
    except Exception as e:
        # 메일 실패가 회원가입을 실패시키면 안 된다. 링크는 콘솔에 남는다
        print(f"\n[mailer] 발송 실패({e}) — 콘솔로 대체\n  인증링크: {link}\n", flush=True)
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
        print(f"\n[mailer] SMTP 미설정 — 콘솔로 대체\n  받는사람: {to}\n  인증번호: {code}\n", flush=True)
        return False

    message = EmailMessage()
    message["Subject"] = CODE_SUBJECT
    message["From"] = SMTP_FROM
    message["To"] = to
    message.set_content(CODE_BODY.format(code=code))
    message.add_alternative(CODE_HTML.format(code=escape(code)), subtype="html")

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as smtp:
            smtp.starttls()
            smtp.login(SMTP_USER, SMTP_PASSWORD)
            smtp.send_message(message)
        return True
    except Exception as e:
        # 메일 실패가 가입을 막으면 안 된다. 번호는 콘솔에 남는다
        print(f"\n[mailer] 발송 실패({e}) — 콘솔로 대체\n  인증번호: {code}\n", flush=True)
        return False
