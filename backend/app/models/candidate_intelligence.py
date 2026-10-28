import uuid

from sqlalchemy import ForeignKey, JSON, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, TimestampMixin, UUIDPrimaryKeyMixin


class CandidateIntelligence(
    UUIDPrimaryKeyMixin,
    TimestampMixin,
    Base,
):
    __tablename__ = "candidate_intelligence"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        index=True,
    )

    career_profile: Mapped[dict] = mapped_column(
        JSON,
        default=dict,
    )

    resume_intelligence: Mapped[dict] = mapped_column(
        JSON,
        default=dict,
    )

    projects: Mapped[list] = mapped_column(
        JSON,
        default=list,
    )

    core_skills: Mapped[list] = mapped_column(
        JSON,
        default=list,
    )

    technologies: Mapped[list] = mapped_column(
        JSON,
        default=list,
    )

    target_roles: Mapped[list] = mapped_column(
        JSON,
        default=list,
    )

    preferred_locations: Mapped[list] = mapped_column(
        JSON,
        default=list,
    )

    professional_summary: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )