import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, TimestampMixin, UUIDPrimaryKeyMixin


class InterviewSession(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "interview_sessions"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("jobs.id", ondelete="CASCADE"), index=True
    )
    application_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("applications.id", ondelete="SET NULL"), nullable=True, index=True
    )
    mode: Mapped[str] = mapped_column(String(20), default="mixed")  # technical | behavioral | mixed
    difficulty: Mapped[str] = mapped_column(String(20), default="medium")  # easy | medium | hard
    status: Mapped[str] = mapped_column(String(20), default="IN_PROGRESS", index=True)
    overall_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    summary: Mapped[dict] = mapped_column(JSON, default=dict)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class InterviewQuestion(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "interview_questions"
    __table_args__ = (
        UniqueConstraint("session_id", "position", name="uq_interview_questions_session_position"),
    )

    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("interview_sessions.id", ondelete="CASCADE"), index=True
    )
    position: Mapped[int] = mapped_column(Integer)
    category: Mapped[str] = mapped_column(String(30))
    skill: Mapped[str | None] = mapped_column(String(100), nullable=True)
    question: Mapped[str] = mapped_column(Text)
    # [{"label": "...", "keywords": ["..."]}] – the hidden answer rubric
    expected_points: Mapped[list] = mapped_column(JSON, default=list)
    difficulty: Mapped[str] = mapped_column(String(20), default="medium")
    source: Mapped[str] = mapped_column(String(20), default="template")  # template | llm
    answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    feedback: Mapped[dict] = mapped_column(JSON, default=dict)
    answered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
