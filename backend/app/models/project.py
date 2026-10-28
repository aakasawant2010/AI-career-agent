import uuid

from sqlalchemy import Boolean, ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Project(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "projects"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )

    name: Mapped[str] = mapped_column(
        String(200),
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    technologies: Mapped[list] = mapped_column(
        JSON,
        default=list,
    )

    github_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    live_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    role: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
    )

    featured: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
    )