import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class JobImport(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    source: str = Field(default="manual", max_length=50)
    external_id: str | None = Field(default=None, max_length=300)
    title: str = Field(min_length=1, max_length=300)
    company: str = Field(min_length=1, max_length=300)
    location: str | None = Field(default=None, max_length=500)
    work_mode: str = Field(default="unknown", max_length=50)
    employment_type: str | None = Field(default=None, max_length=100)
    description: str = Field(min_length=1)
    requirements: str | None = None
    skills: list[str] = Field(default_factory=list)
    technologies: list[str] = Field(default_factory=list)
    min_salary_lpa: float | None = Field(default=None, ge=0)
    max_salary_lpa: float | None = Field(default=None, ge=0)
    salary_text: str | None = Field(default=None, max_length=500)
    experience_min_years: float | None = Field(default=None, ge=0)
    experience_max_years: float | None = Field(default=None, ge=0)
    notice_period_days: int | None = Field(default=None, ge=0)
    apply_url: str | None = Field(default=None, max_length=1000)
    source_url: str | None = Field(default=None, max_length=1000)
    posted_at: datetime | None = None
    raw_data: dict[str, Any] = Field(default_factory=dict)

    @field_validator("work_mode")
    @classmethod
    def normalize_work_mode(cls, value: str) -> str:
        value = value.strip().lower()
        aliases = {"wfh": "remote", "work from home": "remote", "hybrid work": "hybrid"}
        return aliases.get(value, value)


class JobResponse(JobImport):
    id: uuid.UUID
    job_hash: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class JobListResponse(BaseModel):
    items: list[JobResponse]
    total: int
    limit: int
    offset: int


class JobIngestRequest(BaseModel):
    source_type: str = Field(pattern="^(greenhouse|lever)$")
    board: str = Field(min_length=1, max_length=200)
    source_url: str | None = None


class JobImportResult(BaseModel):
    created: int
    updated: int
    skipped: int
    jobs: list[JobResponse]
