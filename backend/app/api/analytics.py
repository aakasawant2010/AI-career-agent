from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser
from app.core.database import get_db
from app.schemas.tracking import (
    BreakdownRow,
    FunnelResponse,
    OverviewResponse,
    ResponseStats,
    TimelinePoint,
)
from app.services import analytics

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/overview", response_model=OverviewResponse)
def overview(current_user: CurrentUser, db: Session = Depends(get_db)):
    """One-call dashboard payload: totals, funnel, response stats, what needs attention."""
    return analytics.compute_overview(db, current_user.id)


@router.get("/funnel", response_model=FunnelResponse)
def funnel(current_user: CurrentUser, db: Session = Depends(get_db)):
    return analytics.compute_funnel(analytics.load_records(db, current_user.id))


@router.get("/response", response_model=ResponseStats)
def response_stats(current_user: CurrentUser, db: Session = Depends(get_db)):
    return analytics.compute_response(analytics.load_records(db, current_user.id))


@router.get("/breakdown", response_model=list[BreakdownRow])
def breakdown(
    current_user: CurrentUser,
    by: str = Query(default="source", description="source | company | role | work_mode | match_band"),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    try:
        return analytics.compute_breakdown(analytics.load_records(db, current_user.id), by, limit)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/timeline", response_model=list[TimelinePoint])
def timeline(
    current_user: CurrentUser,
    weeks: int = Query(default=12, ge=1, le=52),
    db: Session = Depends(get_db),
):
    return analytics.compute_timeline(analytics.load_records(db, current_user.id), weeks)
