from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field
class ApplicationCreate(BaseModel):
    job_id: UUID
    submission_mode: str = "MANUAL_SUBMISSION_REQUIRED"
    notes: str | None = None
class ApplicationStatusUpdate(BaseModel):
    status: str
    note: str | None = None
class FollowUpCreate(BaseModel):
    due_at: datetime
    note: str | None = None
class ApplicationAnswer(BaseModel):
    question: str
    answer: str
class ApplicationPackageResponse(BaseModel):
    model_config = __import__('pydantic').ConfigDict(from_attributes=True)
    application_id: UUID
    resume_id: UUID | None
    resume_content: str | None
    cover_letter: str | None
    answers: dict
    grounding_issues: list
    readiness: str
class ApplicationResponse(BaseModel):
    model_config = __import__('pydantic').ConfigDict(from_attributes=True)
    id: UUID; job_id: UUID; status: str; submission_mode: str; notes: str|None; submitted_at: datetime|None
class AnalyticsResponse(BaseModel):
    total: int
    by_status: dict[str,int]
    conversion_rate: float
    avg_match_score: float
    pending_followups: int
    applications_last_30_days: int
