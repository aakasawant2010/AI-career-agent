import uuid

from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Resume(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "resumes"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )

    name: Mapped[str] = mapped_column(
        String(200),
    )

    file_path: Mapped[str] = mapped_column(
        String(500),
    )

    file_type: Mapped[str] = mapped_column(
        String(50),
    )

    parsed_text: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
    )