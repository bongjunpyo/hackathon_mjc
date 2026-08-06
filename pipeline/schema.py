"""courses.json 스키마 — docs/DESIGN.md §5 동결본.

LLM 구조화 추출의 출력 계약이자 검증 대상. 스키마가 곧 검증기이므로
필드를 늘리려면 설계서를 먼저 고친다.
"""

from typing import Literal

from pydantic import BaseModel, Field

Category = Literal["전공", "교양", "일반선택"]


class Course(BaseModel):
    course_id: str = Field(description="dept_id-학년-학기-슬러그 (예: itc-1-1-internet-prog)")
    name: str = Field(description="교과목명. 원본의 깨진 공백을 정규화한 표시용 이름")
    year: int
    semester: int
    credits: int
    category: Category
    required: bool = Field(description="필수 이수 여부. 교양필수(인성채플·성경과삶)는 True")
    talent_type: str | None = Field(
        default=None, description="인재양성유형 — PDF 비고 열의 직무 라벨. 트랙 B ground truth"
    )
    ncs: bool = False
    field_based: bool = False


class DeptCurriculum(BaseModel):
    dept_id: str
    dept_name: str
    faculty_type_code: str | None = None
    years: int
    tier: int
    courses: list[Course]
    certificates: list[str] = []
    careers: list[str] = []
    # 교양선택은 과목마다 학점이 달라 열거하지 않는다. 필요 학점만 남기고
    # 로드맵 에이전트가 "교양선택 N학점" 블록으로 배치한다 (팀 결정 2026-08-06).
    liberal_elective_credits: int = 0
    source_url: str = ""
    extraction_confidence: float = 0.0
