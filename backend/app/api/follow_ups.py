from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser
from app.core.database import get_db
from app.core.timeutil import as_utc
from app.models.application import Application, FollowUp
from app.schemas.tracking import FollowUpResponse, FollowUpUpdate
from app.services import tracking

router = APIRouter(tags=["Follow-ups"])


def _to_response(follow_up: FollowUp, now: datetime | None = None) -> FollowUpResponse:
    data = FollowUpResponse.model_validate(follow_up)
    data.overdue = tracking.is_overdue(follow_up, now)
    return data


def _owned_follow_up(db: Session, follow_up_id: UUID, user_id) -> FollowUp:
    follow_up = db.scalar(
        select(FollowUp)
        .join(Application, Application.id == FollowUp.application_id)
        .where(FollowUp.id == follow_up_id, Application.user_id == user_id)
    )
    if follow_up is None:
        raise HTTPException(status_code=404, detail="Follow-up not found")
    return follow_up


@router.get("/follow-ups", response_model=list[FollowUpResponse])
def list_follow_ups(
    current_user: CurrentUser,
    status: str | None = Query(default=None, description="PENDING, DONE or CANCELLED"),
    due_within_days: int | None = Query(default=None, ge=0, le=365),
    db: Session = Depends(get_db),
):
    """The reminder inbox: open items first, soonest due at the top."""
    stmt = (
        select(FollowUp)
        .join(Application, Application.id == FollowUp.application_id)
        .where(Application.user_id == current_user.id)
        .order_by(FollowUp.due_at)
    )
    if status:
        stmt = stmt.where(FollowUp.status == status.upper())
    items = list(db.scalars(stmt))
    now = datetime.now(timezone.utc)
    if due_within_days is not None:
        horizon = now + timedelta(days=due_within_days)
        items = [f for f in items if f.status == "PENDING" and as_utc(f.due_at) <= horizon]
    return [_to_response(f, now) for f in items]


@router.get("/applications/{application_id}/follow-ups", response_model=list[FollowUpResponse])
def application_follow_ups(
    application_id: UUID, current_user: CurrentUser, db: Session = Depends(get_db)
):
    application = db.get(Application, application_id)
    if not application or application.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Application not found")
    items = db.scalars(
        select(FollowUp).where(FollowUp.application_id == application.id).order_by(FollowUp.due_at)
    )
    now = datetime.now(timezone.utc)
    return [_to_response(f, now) for f in items]


@router.patch("/follow-ups/{follow_up_id}", response_model=FollowUpResponse)
def update_follow_up(
    follow_up_id: UUID,
    data: FollowUpUpdate,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
):
    follow_up = _owned_follow_up(db, follow_up_id, current_user.id)
    try:
        updated = tracking.update_follow_up(
            db, follow_up, status=data.status, due_at=data.due_at, note=data.note
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return _to_response(updated)
