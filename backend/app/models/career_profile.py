import uuid

from sqlalchemy import Boolean, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, TimestampMixin, UUIDPrimaryKeyMixin


class CareerProfile(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "career_profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        index=True,
    )

    target_roles: Mapped[list] = mapped_column(JSON, default=list)
    preferred_locations: Mapped[list] = mapped_column(JSON, default=list)

    work_preference: Mapped[str] = mapped_column(
        String(50),
        default="any",
    )

    min_salary_lpa: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    max_salary_lpa: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    notice_period_days: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    total_experience_years: Mapped[float | None] = mapped_column(
        nullable=True,
    )

    skills: Mapped[list] = mapped_column(JSON, default=list)
    certifications: Mapped[list] = mapped_column(JSON, default=list)
    education: Mapped[list] = mapped_column(JSON, default=list)

    actively_looking: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
    )