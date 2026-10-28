from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class InterviewSessionCreate(BaseModel):
    job_id: UUID | None = None
    application_id: UUID | None = None
    mode: Literal["technical", "behavioral", "mixed"] = "mixed"
    difficulty: Literal["easy", "medium", "hard"] = "medium"
    num_questions: int = Field(default=6, ge=3, le=15)

    @model_validator(mode="after")
    def _needs_target(self):
        if self.job_id is None and self.application_id is None:
            raise ValueError("Provide job_id or application_id")
        return self


class AnswerRequest(BaseModel):
    answer: str = Field(min_length=1, max_length=8000)


class QuestionResponse(BaseModel):
    """The rubric (expected_points) is intentionally not exposed until the question is answered."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    position: int
    category: str
    skill: str | None
    question: str
    difficulty: str
    source: str
    answer: str | None = None
    score: float | None = None
    feedback: dict = Field(default_factory=dict)
    answered_at: datetime | None = None


class InterviewSessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    job_id: UUID
    application_id: UUID | None
    mode: str
    difficulty: str
    status: str
    overall_score: float | None
    summary: dict = Field(default_factory=dict)
    created_at: datetime
    completed_at: datetime | None
    questions: list[QuestionResponse] = Field(default_factory=list)


class InterviewSessionListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    job_id: UUID
    application_id: UUID | None
    mode: str
    difficulty: str
    status: str
    overall_score: float | None
    created_at: datetime
    completed_at: datetime | None
