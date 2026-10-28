from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser
from app.core.database import get_db
from app.models.application import (
    Application,
    ApplicationPackage,
    ApplicationEvent,
    FollowUp,
)
from app.models.job import Job
from app.models.job_match import JobMatch
from app.schemas.application import *
from app.schemas.tracking import ApplicationEventResponse
from app.core.timeutil import as_utc
from app.services.application import prepare, transition


router = APIRouter(
    prefix="/applications",
    tags=["Applications"],
)


# ============================================================
# CREATE APPLICATION
# ============================================================

@router.post("", response_model=ApplicationResponse)
def create(
    current_user: CurrentUser,
    data: ApplicationCreate,
    db: Session = Depends(get_db),
):
    # Verify job exists
    job = db.get(Job, data.job_id)

    if not job:
        raise HTTPException(
            status_code=404,
            detail="Job not found",
        )

    # Prevent duplicate active applications
    existing = db.scalar(
        select(Application).where(
            Application.user_id == current_user.id,
            Application.job_id == data.job_id,
            Application.status.not_in(
                ["REJECTED", "WITHDRAWN"]
            ),
        )
    )

    if existing:
        return existing

    application = Application(
        user_id=current_user.id,
        job_id=data.job_id,
        submission_mode="MANUAL_SUBMISSION_REQUIRED",
        notes=data.notes,
    )

    db.add(application)
    db.flush()

    # Audit event
    db.add(
        ApplicationEvent(
            application_id=application.id,
            to_status="DRAFT",
            actor="user",
            note="Application created",
        )
    )

    db.commit()
    db.refresh(application)

    return application


# ============================================================
# LIST APPLICATIONS
# ============================================================

@router.get("", response_model=list[ApplicationResponse])
def list_apps(
    current_user: CurrentUser,
    status: str | None = None,
    db: Session = Depends(get_db),
):
    stmt = (
        select(Application)
        .where(Application.user_id == current_user.id)
        .order_by(Application.created_at.desc())
    )

    if status:
        stmt = stmt.where(
            Application.status == status.upper()
        )

    return list(db.scalars(stmt))


# ============================================================
# ANALYTICS
# ============================================================

@router.get(
    "/analytics/summary",
    response_model=AnalyticsResponse,
)
def analytics(
    current_user: CurrentUser,
    db: Session = Depends(get_db),
):
    applications = list(
        db.scalars(
            select(Application).where(
                Application.user_id == current_user.id
            )
        )
    )

    # Applications by status
    by_status = {}

    for application in applications:
        by_status[application.status] = (
            by_status.get(application.status, 0) + 1
        )

    # Average match score
    matches = list(
        db.scalars(
            select(JobMatch).where(
                JobMatch.user_id == current_user.id
            )
        )
    )

    average_match_score = (
        sum(match.score for match in matches) / len(matches)
        if matches
        else 0
    )

    # Conversion
    submitted = by_status.get("SUBMITTED", 0)
    rejected = by_status.get("REJECTED", 0)

    closed = submitted + rejected

    conversion_rate = (
        submitted / max(closed, 1) * 100
    )

    # Pending follow-ups
    pending_followups = (
        db.scalar(
            select(func.count())
            .select_from(FollowUp)
            .join(Application)
            .where(
                Application.user_id == current_user.id,
                FollowUp.status == "PENDING",
            )
        )
        or 0
    )

    # Last 30 days
    since = (
        datetime.now(timezone.utc)
        - timedelta(days=30)
    )

    recent_applications = sum(
        1
        for application in applications
        if application.created_at
        and as_utc(application.created_at) >= since
    )

    return AnalyticsResponse(
        total=len(applications),
        by_status=by_status,
        conversion_rate=round(
            conversion_rate,
            2,
        ),
        avg_match_score=round(
            average_match_score,
            2,
        ),
        pending_followups=pending_followups,
        applications_last_30_days=recent_applications,
    )


# ============================================================
# GET APPLICATION
# ============================================================

@router.get(
    "/{application_id}",
    response_model=ApplicationResponse,
)
def get_app(
    application_id: UUID,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
):
    application = db.get(
        Application,
        application_id,
    )

    if (
        not application
        or application.user_id != current_user.id
    ):
        raise HTTPException(
            status_code=404,
            detail="Application not found",
        )

    return application


# ============================================================
# PREPARE APPLICATION PACKAGE
# ============================================================

@router.post(
    "/{application_id}/prepare",
    response_model=ApplicationPackageResponse,
)
def prepare_app(
    application_id: UUID,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
):
    application = db.get(
        Application,
        application_id,
    )

    if (
        not application
        or application.user_id != current_user.id
    ):
        raise HTTPException(
            status_code=404,
            detail="Application not found",
        )

    try:
        return prepare(
            db,
            application,
        )

    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e),
        )


# ============================================================
# GET APPLICATION PACKAGE
# ============================================================

@router.get(
    "/{application_id}/package",
    response_model=ApplicationPackageResponse,
)
def get_package(
    application_id: UUID,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
):
    application = db.get(
        Application,
        application_id,
    )

    if (
        not application
        or application.user_id != current_user.id
    ):
        raise HTTPException(
            status_code=404,
            detail="Application not found",
        )

    package = db.scalar(
        select(ApplicationPackage).where(
            ApplicationPackage.application_id
            == application.id
        )
    )

    if not package:
        raise HTTPException(
            status_code=404,
            detail="Application package not prepared",
        )

    return package


# ============================================================
# UPDATE APPLICATION STATUS
# ============================================================

@router.post(
    "/{application_id}/status",
    response_model=ApplicationResponse,
)
def update_status(
    application_id: UUID,
    data: ApplicationStatusUpdate,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
):
    application = db.get(
        Application,
        application_id,
    )

    if (
        not application
        or application.user_id != current_user.id
    ):
        raise HTTPException(
            status_code=404,
            detail="Application not found",
        )

    try:
        return transition(
            db,
            application,
            data.status,
            "user",
            data.note,
        )

    except ValueError as e:
        raise HTTPException(
            status_code=409,
            detail=str(e),
        )


# ============================================================
# APPROVE APPLICATION
# ============================================================

@router.post(
    "/{application_id}/approve",
    response_model=ApplicationResponse,
)
def approve(
    application_id: UUID,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
):
    return _transition(
        application_id,
        "APPROVED",
        current_user,
        db,
    )


# ============================================================
# SUBMIT APPLICATION
# ============================================================

@router.post(
    "/{application_id}/submit",
    response_model=ApplicationResponse,
)
def submit(
    application_id: UUID,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
):
    application = db.get(
        Application,
        application_id,
    )

    if (
        not application
        or application.user_id != current_user.id
    ):
        raise HTTPException(
            status_code=404,
            detail="Application not found",
        )

    # Safety: only manual submission is supported
    if (
        application.submission_mode
        != "MANUAL_SUBMISSION_REQUIRED"
    ):
        raise HTTPException(
            status_code=400,
            detail="Unsupported submission mode",
        )

    try:
        return transition(
            db,
            application,
            "SUBMITTED",
            "user",
            "User confirmed manual submission",
        )

    except ValueError as e:
        raise HTTPException(
            status_code=409,
            detail=str(e),
        )


# ============================================================
# INTERNAL STATUS TRANSITION
# ============================================================

def _transition(
    application_id: UUID,
    status: str,
    current_user: CurrentUser,
    db: Session,
):
    application = db.get(
        Application,
        application_id,
    )

    if (
        not application
        or application.user_id != current_user.id
    ):
        raise HTTPException(
            status_code=404,
            detail="Application not found",
        )

    try:
        return transition(
            db,
            application,
            status,
            "user",
        )

    except ValueError as e:
        raise HTTPException(
            status_code=409,
            detail=str(e),
        )


# ============================================================
# CREATE FOLLOW-UP
# ============================================================

@router.post(
    "/{application_id}/follow-ups"
)
def follow_up(
    application_id: UUID,
    data: FollowUpCreate,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
):
    application = db.get(
        Application,
        application_id,
    )

    if (
        not application
        or application.user_id != current_user.id
    ):
        raise HTTPException(
            status_code=404,
            detail="Application not found",
        )

    followup = FollowUp(
        application_id=application.id,
        due_at=data.due_at,
        note=data.note,
    )

    db.add(followup)
    db.commit()
    db.refresh(followup)

    return {
        "id": followup.id,
        "status": followup.status,
        "due_at": followup.due_at,
        "note": followup.note,
    }


# ============================================================
# APPLICATION EVENTS / AUDIT LOG
# ============================================================

@router.get(
    "/{application_id}/events",
    response_model=list[ApplicationEventResponse],
)
def events(
    application_id: UUID,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
):
    application = db.get(
        Application,
        application_id,
    )

    if (
        not application
        or application.user_id != current_user.id
    ):
        raise HTTPException(
            status_code=404,
            detail="Application not found",
        )

    return list(
        db.scalars(
            select(ApplicationEvent)
            .where(
                ApplicationEvent.application_id
                == application.id
            )
            .order_by(
                ApplicationEvent.created_at
            )
        )
    )