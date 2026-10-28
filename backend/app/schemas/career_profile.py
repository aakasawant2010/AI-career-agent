import uuid
from pydantic import BaseModel, Field


class CareerProfileCreate(BaseModel):
    target_roles: list[str] = Field(default_factory=list)
    preferred_locations: list[str] = Field(default_factory=list)

    work_preference: str = "any"

    min_salary_lpa: int | None = None
    max_salary_lpa: int | None = None
    notice_period_days: int | None = None
    total_experience_years: float | None = None

    skills: list[str] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)
    education: list[str] = Field(default_factory=list)

    actively_looking: bool = True


class CareerProfileResponse(CareerProfileCreate):
    id: uuid.UUID
    user_id: uuid.UUID

    model_config = {"from_attributes": True}