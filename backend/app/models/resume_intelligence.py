import uuid

from sqlalchemy import ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, TimestampMixin, UUIDPrimaryKeyMixin


class ResumeIntelligence(
    UUIDPrimaryKeyMixin,
    TimestampMixin,
    Base,
):
    __tablename__ = "resume_intelligence"

    resume_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("resumes.id", ondelete="CASCADE"),
        unique=True,
        index=True,
    )

    skills: Mapped[list] = mapped_column(
        JSON,
        default=list,
    )

    experience: Mapped[list] = mapped_column(
        JSON,
        default=list,
    )

    education: Mapped[list] = mapped_column(
        JSON,
        default=list,
    )

    projects: Mapped[list] = mapped_column(
        JSON,
        default=list,
    )

    certifications: Mapped[list] = mapped_column(
        JSON,
        default=list,
    )

    job_titles: Mapped[list] = mapped_column(
        JSON,
        default=list,
    )

    technologies: Mapped[list] = mapped_column(
        JSON,
        default=list,
    )

    total_experience_years: Mapped[float | None] = mapped_column(
        nullable=True,
    )

    summary: Mapped[str | None] = mapped_column(
        nullable=True,
    )