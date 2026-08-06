import { useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { useApp } from "../store";
import { auth } from "../lib/api";
import { DEPTS } from "../lib/depts";
import TermsBox from "../components/TermsBox";
import { REQUIRED_TERMS } from "../lib/terms";

/* 부가 화면 — 로그인 + 회원가입. 게스트 경로가 항상 살아 있어야 하므로 여기서 막지 않는다.
   가입은 토큰을 주지 않는다. 인증 메일 링크를 눌러야 로그인된다 (server/auth.py). */

const field = "w-full rounded-lg border border-edge bg-white px-3 py-2.5";
const label = "mb-1.5 block font-mono text-xs tracking-[0.1em] text-steel";
const primary =
  "rounded-xl bg-navy px-5 py-2.5 font-bold text-white transition-[background-color,scale] duration-200 hover:bg-navy-deep active:scale-[0.96] disabled:opacity-60";
const ghost =
  "rounded-xl border border-edge bg-white px-5 py-2.5 font-bold text-navy transition-[background-color,scale] duration-200 hover:bg-sky-soft active:scale-[0.96] disabled:opacity-60";

export default function Login() {
  const { guest, login } = useApp();
  const [mode, setMode] = useState("login");
  const [sentTo, setSentTo] = useState(null); // 인증 메일을 보낸 주소 — 있으면 안내 화면
  const navigate = useNavigate();

  // 로그아웃은 네비에 있다 — 로그인한 채로 이 경로에 오면 보낼 곳이 없다
  if (!guest) return <Navigate to="/app/roadmap" replace />;

  if (sentTo) {
    return <VerifySent email={sentTo} onBack={() => { setSentTo(null); setMode("login"); }} />;
  }

  const tab = (m, text) => (
    <button
      type="button"
      onClick={() => setMode(m)}
      className={`rounded-lg px-3 py-2 text-sm font-bold transition-colors ${
        mode === m ? "bg-navy text-white" : "text-ink-2 hover:bg-sky-soft"
      }`}
    >
      {text}
    </button>
  );

  return (
    <section className="flex max-w-md flex-col gap-4">
      <div className="flex gap-1.5">
        {tab("login", "로그인")}
        {tab("signup", "회원가입")}
      </div>

      {mode === "login" ? (
        <LoginForm onDone={() => navigate("/app/roadmap")} login={login} />
      ) : (
        <SignupForm
          onSent={setSentTo}
          onLoggedIn={(token) => {
            login(token);
            navigate('/app/roadmap');
          }}
        />
      )}

      <button type="button" onClick={() => navigate("/app/roadmap")} className={`self-start ${ghost}`}>
        게스트로 둘러보기
      </button>
    </section>
  );
}

function LoginForm({ onDone, login }) {
  const [form, setForm] = useState({ student_id: "", password: "" });
  const [error, setError] = useState(null);
  const [needVerify, setNeedVerify] = useState(false);
  const [busy, setBusy] = useState(false);

  async function onSubmit(e) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    setNeedVerify(false);
    try {
      const { access_token } = await auth.login(form);
      login(access_token);
      onDone();
    } catch (err) {
      setError(err.message ?? "로그인에 실패했습니다.");
      setNeedVerify(err.code === "EMAIL_NOT_VERIFIED");
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={onSubmit} className="flex flex-col gap-4">
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
          required
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
          required
        />
      </div>

      {error && <Notice>{error}</Notice>}
      {needVerify && <ResendRow />}

      <button type="submit" disabled={busy} className={`self-start ${primary}`}>
        {busy ? "확인 중…" : "로그인"}
      </button>
    </form>
  );
}

function SignupForm({ onSent, onLoggedIn }) {
  const [form, setForm] = useState({
    student_id: "",
    name: "",
    email: "",
    password: "",
    dept_id: DEPTS[0].id,
  });
  /* 이메일 인증 상태 — idle → sent(번호 입력 중) → done(티켓 확보).
     이메일을 고치면 idle로 되돌린다. 안 그러면 A로 받은 인증으로 B를 가입시킨다. */
  const [agreed, setAgreed] = useState({});
  const [step, setStep] = useState("idle");
  const [code, setCode] = useState("");
  const [ticket, setTicket] = useState("");
  const [codeError, setCodeError] = useState(null);
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);
  const [sending, setSending] = useState(false);

  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });
  const termsOk = REQUIRED_TERMS.every((t) => agreed[t.key]);

  function setEmail(e) {
    setForm({ ...form, email: e.target.value });
    setStep("idle");
    setCode("");
    setTicket("");
    setCodeError(null);
  }

  async function sendCode() {
    setSending(true);
    setCodeError(null);
    try {
      await auth.sendEmailCode(form.email);
      setStep("sent");
    } catch (err) {
      setCodeError(err.message ?? "인증번호를 보내지 못했습니다.");
    } finally {
      setSending(false);
    }
  }

  async function checkCode() {
    setSending(true);
    setCodeError(null);
    try {
      const res = await auth.verifyEmailCode(form.email, code);
      setTicket(res.email_ticket);
      setStep("done");
    } catch (err) {
      setCodeError(err.message ?? "인증에 실패했습니다.");
    } finally {
      setSending(false);
    }
  }

  async function onSubmit(e) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const res = await auth.signup({
        ...form,
        email_ticket: ticket,
        agreed_terms: Boolean(agreed.service),
        agreed_privacy: Boolean(agreed.privacy),
      });
      // 인증을 마친 가입이면 서버가 토큰을 준다 — 메일 안내 화면을 건너뛴다
      if (res.access_token) onLoggedIn(res.access_token);
      else onSent(form.email);
    } catch (err) {
      setError(err.message ?? "가입에 실패했습니다.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={onSubmit} className="flex flex-col gap-4">
      <p className="text-sm text-ink-2">
        이메일 인증번호를 받아 확인한 뒤 가입합니다. 인증하면 바로 로그인됩니다.
      </p>

      <div>
        <label className={label} htmlFor="su-sid">학번</label>
        <input
          id="su-sid"
          className={field}
          value={form.student_id}
          onChange={set("student_id")}
          autoComplete="username"
          minLength={4}
          maxLength={32}
          required
        />
      </div>
      <div>
        <label className={label} htmlFor="su-name">이름</label>
        <input
          id="su-name"
          className={field}
          value={form.name}
          onChange={set("name")}
          autoComplete="name"
          maxLength={64}
          required
        />
      </div>
      <div>
        <label className={label} htmlFor="su-email">이메일</label>
        <div className="flex gap-2">
          <input
            id="su-email"
            type="email"
            className={`${field} flex-1`}
            value={form.email}
            onChange={setEmail}
            autoComplete="email"
            readOnly={step === "done"}
            required
          />
          {step !== "done" && (
            <button
              type="button"
              onClick={sendCode}
              disabled={sending || !form.email.includes("@")}
              className="shrink-0 rounded-lg border-2 border-navy px-4 font-bold text-navy transition-[background-color,scale] duration-150 hover:bg-sky-soft active:scale-[0.96] disabled:opacity-50 focus-visible:outline-2 focus-visible:outline-gold"
            >
              {step === "sent" ? "재발송" : "인증번호 받기"}
            </button>
          )}
        </div>
      </div>

      {/* 인증번호 — 이메일 바로 아래. 가입 화면을 떠나지 않는다 */}
      {step === "sent" && (
        <div>
          <label className={label} htmlFor="su-code">인증번호</label>
          <div className="flex gap-2">
            <input
              id="su-code"
              inputMode="numeric"
              autoComplete="one-time-code"
              className={`${field} flex-1 font-mono tracking-[0.4em]`}
              value={code}
              onChange={(e) => setCode(e.target.value.replace(/\D/g, "").slice(0, 6))}
              placeholder="000000"
              maxLength={6}
            />
            <button
              type="button"
              onClick={checkCode}
              disabled={sending || code.length !== 6}
              className="shrink-0 rounded-lg bg-navy px-5 font-bold text-white transition-[background-color,scale] duration-150 hover:bg-navy-deep active:scale-[0.96] disabled:opacity-50 focus-visible:outline-2 focus-visible:outline-gold"
            >
              확인
            </button>
          </div>
          <p className="mt-1.5 text-xs text-steel">
            메일함으로 6자리 번호를 보냈습니다 · 10분 안에 입력해 주세요
          </p>
        </div>
      )}
      {step === "done" && (
        <p className="rounded-lg border border-gold/60 bg-gold/15 px-3 py-2 text-sm font-bold text-navy">
          ✓ 이메일 인증 완료 — {form.email}
        </p>
      )}
      {codeError && <Notice>{codeError}</Notice>}
      <div>
        <label className={label} htmlFor="su-dept">학과</label>
        <select id="su-dept" className={field} value={form.dept_id} onChange={set("dept_id")}>
          {DEPTS.map((d) => (
            <option key={d.id} value={d.id}>{d.name}</option>
          ))}
        </select>
      </div>
      <div>
        <label className={label} htmlFor="su-pw">비밀번호</label>
        <input
          id="su-pw"
          type="password"
          className={field}
          value={form.password}
          onChange={set("password")}
          autoComplete="new-password"
          minLength={8}
          required
        />
        <p className="mt-1.5 text-xs text-steel">8자 이상</p>
      </div>

      <TermsBox value={agreed} onChange={setAgreed} />

      {error && <Notice>{error}</Notice>}

      {/* 인증 전에는 가입을 막는다 — 인증이 가입의 전제라는 걸 화면이 말해야 한다 */}
      <button
        type="submit"
        disabled={busy || step !== "done" || !termsOk}
        className={`self-start ${primary} disabled:opacity-50`}
      >
        {busy
          ? "가입 중…"
          : step !== "done"
            ? "이메일 인증 후 가입"
            : termsOk
              ? "회원가입하기"
              : "약관 동의 후 가입"}
      </button>
    </form>
  );
}

function VerifySent({ email, onBack }) {
  return (
    <section className="flex max-w-md flex-col gap-4">
      <h2 className="text-2xl font-extrabold tracking-tight">인증 메일을 보냈습니다</h2>
      <p className="text-sm text-ink-2">
        <b className="text-ink">{email}</b> 로 보낸 링크를 누르면 인증과 동시에 로그인됩니다.
        링크는 30분 뒤 만료됩니다.
      </p>
      <ResendRow email={email} />
      <button type="button" onClick={onBack} className={`self-start ${ghost}`}>
        로그인으로
      </button>
    </section>
  );
}

/* 재발송 — 서버는 가입 여부를 알려주지 않는다(계정 열거 방지). 응답 문구를 그대로 보여준다. */
function ResendRow({ email: initial = "" }) {
  const [email, setEmail] = useState(initial);
  const [message, setMessage] = useState(null);
  const [busy, setBusy] = useState(false);

  async function resend() {
    setBusy(true);
    try {
      const res = await auth.resend(email);
      setMessage(res.message);
    } catch (err) {
      setMessage(err.message ?? "재발송에 실패했습니다.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex flex-col gap-2">
      <div className="flex flex-wrap items-end gap-2">
        <div className="min-w-48 flex-1">
          <label className={label} htmlFor="resend-email">인증 메일 재발송</label>
          <input
            id="resend-email"
            type="email"
            className={field}
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            autoComplete="email"
          />
        </div>
        <button type="button" onClick={resend} disabled={busy || !email} className={ghost}>
          {busy ? "보내는 중…" : "재발송"}
        </button>
      </div>
      {message && <p className="text-sm text-ink-2">{message}</p>}
    </div>
  );
}

function Notice({ children }) {
  return (
    <p className="rounded-lg border border-gold/60 bg-gold/15 px-3 py-2 text-sm text-navy">
      {children}
    </p>
  );
}
