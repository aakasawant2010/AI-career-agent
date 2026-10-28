import uuid
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class Recommendation(str, Enum):
    STRONG_MATCH = "strong_match"
    GOOD_MATCH = "good_match"
    POSSIBLE_MATCH = "possible_match"
    LOW_MATCH = "low_match"


class MatchWeights(BaseModel):
    role: float = Field(default=25, ge=0)
    skills: float = Field(default=35, ge=0)
    experience: float = Field(default=15, ge=0)
    location: float = Field(default=10, ge=0)
    salary: float = Field(default=10, ge=0)
    notice: float = Field(default=5, ge=0)


class JobMatchResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    job_id: uuid.UUID
    score: float
    recommendation: Recommendation
    breakdown: dict
    matched_skills: list[str]
    missing_skills: list[str]
    risks: list[str]
    explanation: str
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class RecommendationResponse(BaseModel):
    job: dict
    match: JobMatchResponse


class RecommendationListResponse(BaseModel):
    items: list[RecommendationResponse]
    total: int
