/* 학기 상세 패널 (DESIGN §2.6) — **학기별 전공 추천** 전용.
   자격증은 여기 없다 — 분기(동그라미)를 눌러 CertPanel(gold)에서 본다.
   과목마다 한 줄 카드로 끊는다 — 이름·태그·학점이 한 덩어리로 붙어 있으면
   6과목이 문단처럼 읽힌다. 헤더 문법(navy+gold+MJ0N)은 3D 모달과 같다. */

function CourseRow({ course, targetJob }) {
  const tag =
    course.talent_type === targetJob
      ? { text: "★ 목표직무", cls: "bg-gold text-navy-deep" }
      : course.category === "교양"
        ? { text: "교양필수", cls: "bg-sky-soft text-navy" }
        : course.talent_type
          ? { text: course.talent_type, cls: "bg-hall text-steel" }
          : null;

  return (
    <li className="flex items-center gap-2 rounded-lg border border-edge bg-white px-3 py-2">
      <span className="shrink-0 font-semibold">{course.name}</span>
      {tag && (
        <span
          title={tag.text}
          className={`min-w-0 truncate rounded px-1.5 py-0.5 text-xs font-bold ${tag.cls}`}
        >
          {tag.text}
        </span>
      )}
      {course.field_based && (
        <span className="shrink-0 rounded bg-sky-soft px-1.5 py-0.5 text-xs text-navy">현장중심</span>
      )}
      <span className="ml-auto shrink-0 font-mono text-xs tabular-nums text-steel">
        {course.credits}학점
      </span>
    </li>
  );
}

export default function SemesterPanel({ semester, index, targetJob, isLast, onNext, onGraduate, onCerts }) {
  if (!semester) return null;
  const credits =
    semester.credits ?? semester.courses.reduce((a, c) => a + (c.credits ?? 0), 0);

  return (
    <aside className="flex flex-col overflow-hidden rounded-2xl bg-white shadow-[0_3px_8px_rgba(0,26,61,.12),0_18px_44px_rgba(0,26,61,.16)]">
      <header className="border-b-[5px] border-gold bg-navy px-5 pb-3.5 pt-4 text-white">
        <span className="inline-flex h-[24px] items-center rounded-full bg-gold px-2.5 font-mono text-xs font-extrabold text-navy-deep">
          MJ0{index + 1}
        </span>
        <h3 className="mt-1 text-xl font-extrabold">
          {semester.year}학년 {semester.semester}학기{" "}
          <span className="font-mono text-base tabular-nums text-sky">· {credits}학점</span>
        </h3>
        <p className="font-mono text-xs text-sky/80">이 학기 전공 추천 · 과목 {semester.courses.length}개</p>
      </header>

      <ul className="flex flex-col gap-1.5 px-4 py-4 text-sm">
        {semester.courses.map((c) => (
          <CourseRow key={c.course_id} course={c} targetJob={targetJob} />
        ))}
      </ul>

      {semester.certificates?.length > 0 && (
        <button
          onClick={onCerts}
          className="mx-4 mb-3 rounded-xl border border-gold/60 bg-gold/10 px-3.5 py-2.5 text-left text-sm font-bold text-navy transition-[background-color,scale] duration-150 hover:bg-gold/20 active:scale-[0.98] focus-visible:outline-2 focus-visible:outline-gold"
        >
          🎫 이 학기 자격증 {semester.certificates.length}종 → 분기에서 보기
        </button>
      )}

      {semester.notes && (
        <p className="mx-4 mb-3 rounded-xl bg-sky-soft px-3.5 py-3 text-sm text-ink-2 inset-ring inset-ring-edge">
          💡 {semester.notes}
        </p>
      )}

      <div className="mt-auto border-t border-edge px-5 py-3 text-right">
        {isLast ? (
          <button
            onClick={onGraduate}
            className="rounded-xl bg-navy px-5 py-2.5 font-bold text-white transition-[background-color,scale] duration-200 hover:bg-navy-deep active:scale-[0.96] focus-visible:outline-2 focus-visible:outline-gold"
          >
            졸업 →
          </button>
        ) : (
          <button
            onClick={onNext}
            className="rounded-lg px-4 py-2 font-bold text-navy transition-[background-color,scale] duration-150 hover:bg-sky-soft active:scale-[0.96] focus-visible:outline-2 focus-visible:outline-gold"
          >
            다음 학기 →
          </button>
        )}
      </div>
    </aside>
  );
}
