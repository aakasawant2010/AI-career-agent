import uuid
from sqlalchemy import ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base, TimestampMixin, UUIDPrimaryKeyMixin

class Application(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "applications"
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    job_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), index=True)
    status: Mapped[str] = mapped_column(String(50), default="DRAFT", index=True)
    submission_mode: Mapped[str] = mapped_column(String(50), default="MANUAL_SUBMISSION_REQUIRED")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    submitted_at = mapped_column(__import__("sqlalchemy").DateTime(timezone=True), nullable=True)

class ApplicationPackage(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "application_packages"
    application_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("applications.id", ondelete="CASCADE"), unique=True, index=True)
    resume_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("resumes.id", ondelete="SET NULL"), nullable=True)
    resume_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    cover_letter: Mapped[str | None] = mapped_column(Text, nullable=True)
    answers: Mapped[dict] = mapped_column(JSON, default=dict)
    grounding_issues: Mapped[list] = mapped_column(JSON, default=list)
    readiness: Mapped[str] = mapped_column(String(50), default="NEEDS_REVIEW")

class ApplicationEvent(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "application_events"
    application_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("applications.id", ondelete="CASCADE"), index=True)
    from_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    to_status: Mapped[str] = mapped_column(String(50), index=True)
    actor: Mapped[str] = mapped_column(String(50), default="system")
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

class FollowUp(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "follow_ups"
    application_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("applications.id", ondelete="CASCADE"), index=True)
    due_at = mapped_column(__import__("sqlalchemy").DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="PENDING", index=True)  # PENDING | DONE | CANCELLED
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    completed_at = mapped_column(__import__("sqlalchemy").DateTime(timezone=True), nullable=True)
