"""Phase 8 – follow-up reminders and tracking helpers."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.timeutil import as_utc
from app.models.application import Application, FollowUp

OPEN = "PENDING"
DONE = "DONE"
CANCELLED = "CANCELLED"
FOLLOW_UP_STATUSES = {OPEN, DONE, CANCELLED}


def schedule_default_follow_up(db: Session, app: Application) -> FollowUp | None:
    """Create one reminder N days after submission unless an open one already exists.

    Adds to the session without committing: the caller (status transition) commits.
    """
    existing = db.scalar(
        select(FollowUp).where(FollowUp.application_id == app.id, FollowUp.status == OPEN)
    )
    if existing is not None:
        return None
    days = get_settings().default_follow_up_days
    follow_up = FollowUp(
        application_id=app.id,
        due_at=datetime.now(timezone.utc) + timedelta(days=days),
        note=f"Follow up if you haven't heard back ({days} days after submitting)",
    )
    db.add(follow_up)
    return follow_up


def cancel_open_follow_ups(db: Session, app: Application, reason: str) -> int:
    rows = list(
        db.scalars(
            select(FollowUp).where(FollowUp.application_id == app.id, FollowUp.status == OPEN)
        )
    )
    for row in rows:
        row.status = CANCELLED
        row.note = f"{row.note} | {reason}" if row.note else reason
    return len(rows)


def update_follow_up(
    db: Session,
    follow_up: FollowUp,
    *,
    status: str | None = None,
    due_at: datetime | None = None,
    note: str | None = None,
) -> FollowUp:
    if status is not None:
        status = status.upper()
        if status not in FOLLOW_UP_STATUSES:
            raise ValueError(f"Invalid follow-up status: {status}")
        if follow_up.status != OPEN and status != follow_up.status:
            raise ValueError(f"Follow-up is already {follow_up.status.lower()}")
        follow_up.status = status
        if status == DONE:
            follow_up.completed_at = datetime.now(timezone.utc)
    if due_at is not None:
        if follow_up.status != OPEN:
            raise ValueError("Only open follow-ups can be rescheduled")
        follow_up.due_at = due_at
    if note is not None:
        follow_up.note = note
    db.commit()
    db.refresh(follow_up)
    return follow_up


def is_overdue(follow_up: FollowUp, now: datetime | None = None) -> bool:
    now = now or datetime.now(timezone.utc)
    due = as_utc(follow_up.due_at)
    return follow_up.status == OPEN and due is not None and due < now
