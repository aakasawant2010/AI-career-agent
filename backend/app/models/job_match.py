import uuid

from sqlalchemy import Float, ForeignKey, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, TimestampMixin, UUIDPrimaryKeyMixin


class JobMatch(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "job_matches"
    __table_args__ = (UniqueConstraint("user_id", "job_id", name="uq_job_matches_user_job"),)

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("jobs.id", ondelete="CASCADE"), index=True
    )
    score: Mapped[float] = mapped_column(Float, index=True)
    recommendation: Mapped[str] = mapped_column(String(50), index=True)
    breakdown: Mapped[dict] = mapped_column(JSON, default=dict)
    matched_skills: Mapped[list] = mapped_column(JSON, default=list)
    missing_skills: Mapped[list] = mapped_column(JSON, default=list)
    risks: Mapped[list] = mapped_column(JSON, default=list)
    explanation: Mapped[str] = mapped_column(Text)
