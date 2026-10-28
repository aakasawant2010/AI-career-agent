from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class FollowUpResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    application_id: UUID
    due_at: datetime
    status: str
    note: str | None = None
    completed_at: datetime | None = None
    overdue: bool = False


class FollowUpUpdate(BaseModel):
    status: str | None = Field(default=None, description="DONE or CANCELLED")
    due_at: datetime | None = None
    note: str | None = Field(default=None, max_length=2000)


class ApplicationEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    application_id: UUID
    from_status: str | None
    to_status: str
    actor: str
    note: str | None
    created_at: datetime


class FunnelStage(BaseModel):
    stage: str
    count: int
    conversion_from_previous: float | None = None
    conversion_from_submitted: float | None = None


class FunnelResponse(BaseModel):
    stages: list[FunnelStage]
    rejected: int
    withdrawn: int
    active: int


class ResponseStats(BaseModel):
    submitted: int
    responded: int
    response_rate: float
    positive_response_rate: float
    avg_days_to_response: float | None
    median_days_to_response: float | None
    awaiting_response: int
    ghosted: int
    ghosted_after_days: int


class BreakdownRow(BaseModel):
    key: str
    applications: int
    submitted: int
    responses: int
    interviews: int
    offers: int
    response_rate: float
    interview_rate: float
    offer_rate: float
    avg_match_score: float | None


class TimelinePoint(BaseModel):
    week_start: str
    created: int
    submitted: int
    responses: int


class OverviewResponse(BaseModel):
    total_applications: int
    by_status: dict[str, int]
    avg_match_score: float
    response: ResponseStats
    funnel: FunnelResponse
    follow_ups: dict[str, int]
    needs_attention: dict[str, int]
