"""생성 → 검증 → 재생성 루프.

LLM은 그럴듯한 거짓말을 한다. 그래서 생성물을 졸업요건 검증기에 대입하고,
미달이면 미달 사유를 그대로 프롬프트에 실어 다시 짜게 한다.

LLM을 직접 부르지 않고 `generate_fn`을 인자로 받는다 — 루프 로직을 API 키 없이
초 단위로 테스트하기 위해서다. 실제 모델은 agent.py에서 주입한다.
"""

from validator import validate_roadmap

# 동결 계약의 `max_retries: 3`을 **총 생성 3회**로 해석한다.
# "재시도 3회"로 읽으면 총 4회가 되고, LLM 호출 한 번이 5~15초라 60초를 넘긴다.
# 프론트 타임아웃과 발표 시연 시간을 감안한 선택 — 바꾸려면 이 상수만 고친다.
MAX_ATTEMPTS = 3


def build_feedback(details):
    """미달 항목을 재생성 프롬프트로 바꾼다.

    `shortfall`만 주면 LLM이 아무 과목이나 채운다. `fix`의 "전공 과목으로"까지
    실어야 제대로 고친다.
    """
    lines = "\n".join(
        f"- {d['label']}: {d['actual']}/{d['required']} → {d['fix']}" for d in details
    )
    return f"이전 로드맵이 졸업요건에 미달했습니다. 아래를 고쳐서 다시 짜세요.\n{lines}"


def generate_roadmap(spec, generate_fn, max_attempts=MAX_ATTEMPTS):
    """상한을 넘겨도 예외를 던지지 않는다.

    부분 로드맵 + 미달 사유를 정상 응답으로 돌려줘야 화면이 "여기까지 충족,
    이것이 부족"을 그릴 수 있다 (docs/DESIGN.md §5).
    """
    feedback = None
    for attempt in range(1, max_attempts + 1):
        roadmap = generate_fn(spec, feedback, attempt)
        validation = validate_roadmap(
            roadmap["semesters"],
            spec["dept"]["years"],
            completed=spec.get("completed"),
            completed_semesters=spec.get("completed_semesters", 0),
        )
        if validation["passed"]:
            break
        feedback = build_feedback(validation["details"])

    return {**roadmap, "validation": validation, "attempts": attempt}
