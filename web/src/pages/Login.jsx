import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useApp } from "../store";
import { auth } from "../lib/api";

/* 부가 화면 — 인증 API는 코어 통합(05:00) 이후 붙는다.
   게스트 경로가 항상 살아 있어야 하므로 여기서 막지 않는다. */
export default function Login() {
  const { guest, login, logout } = useApp();
  const [form, setForm] = useState({ student_id: "", password: "" });
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);
  const navigate = useNavigate();

  async function onSubmit(e) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const { access_token } = await auth.login(form);
      login(access_token);
      navigate("/app/input");
    } catch (err) {
      setError(err.message ?? "로그인에 실패했습니다.");
    } finally {
      setBusy(false);
    }
  }

  if (!guest) {
    return (
      <section className="flex max-w-md flex-col gap-4">
        <h2 className="text-2xl font-extrabold tracking-tight">내 정보</h2>
        <button
          onClick={logout}
          className="self-start rounded-xl border border-edge bg-white px-5 py-2.5 font-bold text-navy transition-[background-color,scale] duration-200 hover:bg-sky-soft active:scale-[0.96]"
        >
          로그아웃
        </button>
      </section>
    );
  }

  const field = "w-full rounded-lg border border-edge bg-white px-3 py-2.5";
  const label = "mb-1.5 block font-mono text-xs tracking-[0.1em] text-steel";

  return (
    <form onSubmit={onSubmit} className="flex max-w-md flex-col gap-4">
      <h2 className="text-2xl font-extrabold tracking-tight">로그인</h2>
      <p className="text-sm text-ink-2">
        로그인하면 이수내역이 자동으로 채워지고 로드맵을 저장할 수 있습니다.
      </p>

      <div>
        <label className={label} htmlFor="sid">학번</label>
        <input
          id="sid"
          className={field}
          value={form.student_id}
          onChange={(e) => setForm({ ...form, student_id: e.target.value })}
          autoComplete="username"
        />
      </div>
      <div>
        <label className={label} htmlFor="pw">비밀번호</label>
        <input
          id="pw"
          type="password"
          className={field}
          value={form.password}
          onChange={(e) => setForm({ ...form, password: e.target.value })}
          autoComplete="current-password"
        />
      </div>

      {error && (
        <p className="rounded-lg border border-gold/60 bg-gold/15 px-3 py-2 text-sm text-navy">
          {error}
        </p>
      )}

      <div className="flex flex-wrap gap-3">
        <button
          type="submit"
          disabled={busy}
          className="rounded-xl bg-navy px-5 py-2.5 font-bold text-white transition-[background-color,scale] duration-200 hover:bg-navy-deep active:scale-[0.96] disabled:opacity-60"
        >
          {busy ? "확인 중…" : "로그인"}
        </button>
        <button
          type="button"
          onClick={() => navigate("/app/input")}
          className="rounded-xl border border-edge bg-white px-5 py-2.5 font-bold text-navy transition-[background-color,scale] duration-200 hover:bg-sky-soft active:scale-[0.96]"
        >
          게스트로 둘러보기
        </button>
      </div>
    </form>
  );
}
