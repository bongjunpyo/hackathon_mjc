"""PostgreSQL 실DB 검증 — Docker가 올라온 뒤 한 번 실행한다.

    docker compose up -d db          # 저장소 루트에서
    cd server && uv run python verify_db.py

SQLite로는 통과하는데 PostgreSQL에서 깨지는 것들이 있다. 특히 **타임존**이 그렇다 —
SQLite는 tz 정보를 버리고 PostgreSQL은 보존하므로, 인증 링크 만료 비교가 한쪽에서만
동작할 수 있다. 데모 직전에 발견하지 않으려고 미리 잰다.

테스트 계정은 끝에 지운다. 여러 번 돌려도 된다.
"""

import sys
import traceback
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from sqlalchemy import inspect, select

import catalog
import db
import mailer

MARK = "verify-db-임시계정"
ACCOUNT = {
    "student_id": "999999999",
    "name": MARK,
    "email": "verify-db-999999999@example.com",  # .invalid는 email-validator가 예약 도메인으로 거부한다
    "password": "verify-db-1234",
    "dept_id": None,  # 첫 학과로 채운다
}

results = []


def check(name):
    def wrap(fn):
        try:
            detail = fn()
            results.append((True, name, detail or ""))
        except Exception as e:
            results.append((False, name, f"{type(e).__name__}: {e}"))
            if "-v" in sys.argv:
                traceback.print_exc()
        return fn

    return wrap


def main():
    print(f"대상 DB : {db.DATABASE_URL}")
    if db.DATABASE_URL.startswith("sqlite"):
        print("⚠️  SQLite입니다. PostgreSQL을 재려면 docker compose up -d db 후 다시 실행하세요.\n")
    else:
        print()

    @check("연결 + create_all")
    def _():
        if not db.init_db():
            raise RuntimeError("init_db 실패 — 컨테이너가 떴는지, 포트 5432가 맞는지 확인")
        return "테이블 생성 완료"

    @check("테이블 3개와 핵심 컬럼")
    def _():
        insp = inspect(db.engine())
        tables = set(insp.get_table_names())
        missing = {"users", "completed_courses", "saved_roadmaps"} - tables
        if missing:
            raise RuntimeError(f"테이블 없음: {sorted(missing)}")
        cols = {c["name"] for c in insp.get_columns("completed_courses")}
        if "course_id" not in cols:
            raise RuntimeError(f"completed_courses에 course_id 없음 (이슈 #4) — {sorted(cols)}")
        if "course_name" in cols:
            raise RuntimeError("completed_courses에 course_name이 남아 있음 (이슈 #4)")
        return f"users / completed_courses(course_id) / saved_roadmaps"

    import models

    with db.session_factory()() as s:
        for user in s.scalars(select(models.User).where(models.User.name == MARK)):
            s.delete(user)
        s.commit()

    depts = catalog.list_depts()
    if not depts:
        results.append((False, "학과 데이터", "data/depts가 비어 있다"))
        return report()
    ACCOUNT["dept_id"] = depts[0]["dept_id"]
    job = (catalog.load_dept(ACCOUNT["dept_id"]).get("careers") or [None])[0]

    from fastapi.testclient import TestClient
    from main import app

    client = TestClient(app, follow_redirects=False)
    mailer.outbox.clear()
    state = {}

    @check("회원가입 → 201, 토큰 없음")
    def _():
        res = client.post("/auth/signup", json=ACCOUNT)
        if res.status_code != 201:
            raise RuntimeError(f"HTTP {res.status_code} {res.text[:120]}")
        if "access_token" in res.json():
            raise RuntimeError("인증 전인데 토큰을 줬다")
        return res.json().get("message", "")

    @check("학번 중복 → 409 (503이 아님)")
    def _():
        res = client.post("/auth/signup", json={**ACCOUNT, "email": "verify-db-other@example.com"})
        if res.status_code != 409:
            raise RuntimeError(f"HTTP {res.status_code} — 유니크 제약이 안 걸렸거나 핸들러가 삼켰다")
        return res.json()["error"]["code"]

    @check("타임존 왕복 (PostgreSQL만의 함정)")
    def _():
        with db.session_factory()() as s:
            user = s.scalar(select(models.User).where(models.User.name == MARK))
            raw = user.verification_expires_at
        tz = "aware" if raw.tzinfo else "naive"
        # auth._aware()가 양쪽을 처리하는지 — 이게 깨지면 인증 링크가 항상 만료로 보인다
        from auth import _aware

        if _aware(raw) < datetime.now(UTC):
            raise RuntimeError(f"방금 만든 링크가 이미 만료로 계산된다 (저장값 {tz})")
        return f"저장값 {tz} · 만료 비교 정상"

    @check("인증 전 로그인 → 403")
    def _():
        res = client.post(
            "/auth/login",
            json={"student_id": ACCOUNT["student_id"], "password": ACCOUNT["password"]},
        )
        if res.status_code != 403:
            raise RuntimeError(f"HTTP {res.status_code}")
        return res.json()["error"]["code"]

    @check("인증 링크 → 302, JWT는 URL에 없음")
    def _():
        link = mailer.outbox[-1]["link"]
        parsed = urlparse(link)
        res = client.get(f"{parsed.path}?{parsed.query}")
        if res.status_code != 302:
            raise RuntimeError(f"HTTP {res.status_code} {res.text[:120]}")
        location = res.headers["location"]
        if "access_token" in location:
            raise RuntimeError("리다이렉트 URL에 JWT가 실렸다")
        state["code"] = parse_qs(urlparse(location).query)["code"][0]
        return location

    @check("교환 코드 → 토큰, 재사용은 400")
    def _():
        body = client.post("/auth/exchange", json={"code": state["code"]}).json()
        state["token"] = body["access_token"]
        again = client.post("/auth/exchange", json={"code": state["code"]})
        if again.status_code != 400:
            raise RuntimeError(f"1회용이 아니다 — 재사용에 HTTP {again.status_code}")
        return "발급 + 1회용 확인"

    @check("인증 후 로그인 → 200")
    def _():
        res = client.post(
            "/auth/login",
            json={"student_id": ACCOUNT["student_id"], "password": ACCOUNT["password"]},
        )
        if res.status_code != 200:
            raise RuntimeError(f"HTTP {res.status_code} {res.text[:120]}")
        return "access + refresh"

    @check("이수내역 저장 → /me 왕복")
    def _():
        headers = {"Authorization": f"Bearer {state['token']}"}
        dept = catalog.load_dept(ACCOUNT["dept_id"])
        ids = [c["course_id"] for c in dept["courses"][:2]]
        client.put("/me/courses", json={"completed_courses": ids}, headers=headers)
        got = client.get("/me", headers=headers).json()
        if got["completed_courses"] != ids:
            raise RuntimeError(f"저장한 것과 다르다: {got['completed_courses']}")
        return f"{len(ids)}건"

    @check("로드맵 저장 → /me 왕복 (JSON 컬럼)")
    def _():
        headers = {"Authorization": f"Bearer {state['token']}"}
        payload = {"target_job": job or "테스트", "roadmap": {"semesters": [], "한글": "값"}}
        res = client.post("/me/roadmaps", json=payload, headers=headers)
        if res.status_code != 201:
            raise RuntimeError(f"HTTP {res.status_code}")
        saved = client.get("/me", headers=headers).json()["saved_roadmaps"]
        if saved[0]["roadmap"]["한글"] != "값":
            raise RuntimeError("한글이 왕복에서 깨졌다")
        return "한글 왕복 정상"

    @check("코어는 토큰 없이 200 (게스트 경로)")
    def _():
        res = client.post(
            "/roadmap",
            json={
                "dept_id": ACCOUNT["dept_id"],
                "current_year": 1,
                "current_semester": 1,
                "completed_courses": [],
                "target_job": job,
            },
        )
        if res.status_code != 200:
            raise RuntimeError(f"HTTP {res.status_code} {res.text[:150]}")
        v = res.json()["validation"]
        return f"passed={v['passed']} 남은학점={v['remaining_credits']}"

    @check("테스트 계정 정리")
    def _():
        with db.session_factory()() as s:
            for user in s.scalars(select(models.User).where(models.User.name == MARK)):
                s.delete(user)
            s.commit()
        return "삭제 완료"

    return report()


def report():
    print()
    for ok, name, detail in results:
        print(f"  {'✅' if ok else '❌'} {name}" + (f"  —  {detail}" if detail else ""))
    failed = [r for r in results if not r[0]]
    print()
    if failed:
        print(f"❌ {len(failed)}건 실패. 자세히 보려면 -v 를 붙여 다시 실행하세요.")
        return 1
    print(f"✅ {len(results)}건 전부 통과. 실DB로 인증·코어 경로가 동작합니다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
