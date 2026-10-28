import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Job(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "jobs"
    __table_args__ = (UniqueConstraint("job_hash", name="uq_jobs_job_hash"),)

    source: Mapped[str] = mapped_column(String(50), index=True)
    external_id: Mapped[str | None] = mapped_column(String(300), nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(300), index=True)
    company: Mapped[str] = mapped_column(String(300), index=True)
    location: Mapped[str | None] = mapped_column(String(500), nullable=True, index=True)
    work_mode: Mapped[str] = mapped_column(String(50), default="unknown", index=True)
    employment_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    description: Mapped[str] = mapped_column(Text)
    requirements: Mapped[str | None] = mapped_column(Text, nullable=True)
    skills: Mapped[list] = mapped_column(JSON, default=list)
    technologies: Mapped[list] = mapped_column(JSON, default=list)
    min_salary_lpa: Mapped[float | None] = mapped_column(Float, nullable=True)
    max_salary_lpa: Mapped[float | None] = mapped_column(Float, nullable=True)
    salary_text: Mapped[str | None] = mapped_column(String(500), nullable=True)
    experience_min_years: Mapped[float | None] = mapped_column(Float, nullable=True)
    experience_max_years: Mapped[float | None] = mapped_column(Float, nullable=True)
    notice_period_days: Mapped[int | None] = mapped_column(nullable=True)
    apply_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    posted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    job_hash: Mapped[str] = mapped_column(String(64), index=True)
    raw_data: Mapped[dict] = mapped_column(JSON, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
