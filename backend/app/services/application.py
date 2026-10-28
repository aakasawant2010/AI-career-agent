from __future__ import annotations

import re
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.application import (
    Application,
    ApplicationEvent,
    ApplicationPackage,
    FollowUp,
)
from app.models.job import Job
from app.models.resume import Resume
from app.models.candidate_intelligence import CandidateIntelligence
from app.models.user import AuditLog
from app.services import tracking
from app.services.rag import search


STATES = {
    "DRAFT",
    "PREPARED",
    "PENDING_APPROVAL",
    "APPROVED",
    "SUBMITTED",
    # Phase 8: post-submission pipeline (tracked by the user, never automated)
    "SCREENING",
    "INTERVIEW",
    "OFFER",
    "ACCEPTED",
    "REJECTED",
    "WITHDRAWN",
}


ALLOWED = {
    "DRAFT": {
        "PREPARED",
        "REJECTED",
        "WITHDRAWN",
    },
    "PREPARED": {
        "PENDING_APPROVAL",
        "REJECTED",
        "WITHDRAWN",
    },
    "PENDING_APPROVAL": {
        "APPROVED",
        "REJECTED",
    },
    "APPROVED": {
        "SUBMITTED",
        "REJECTED",
    },
    "SUBMITTED": {
        "SCREENING",
        "INTERVIEW",
        "REJECTED",
        "WITHDRAWN",
    },
    "SCREENING": {
        "INTERVIEW",
        "REJECTED",
        "WITHDRAWN",
    },
    "INTERVIEW": {
        "OFFER",
        "REJECTED",
        "WITHDRAWN",
    },
    "OFFER": {
        "ACCEPTED",
        "REJECTED",  # offer declined / rescinded
        "WITHDRAWN",
    },
    "ACCEPTED": set(),
    "REJECTED": set(),
    "WITHDRAWN": set(),
}

TERMINAL_STATES = {"ACCEPTED", "REJECTED", "WITHDRAWN"}


def transition(
    db: Session,
    app: Application,
    to_status: str,
    actor: str,
    note: str | None = None,
):
    to_status = to_status.upper()

    if to_status not in STATES:
        raise ValueError(f"Invalid application status: {to_status}")

    allowed_states = ALLOWED.get(app.status, set())

    if to_status not in allowed_states:
        raise ValueError(
            f"Invalid transition {app.status} -> {to_status}"
        )

    old_status = app.status

    app.status = to_status

    if to_status == "SUBMITTED":
        app.submitted_at = datetime.now(timezone.utc)
        # Phase 8: suggest a follow-up so submitted applications don't go cold.
        tracking.schedule_default_follow_up(db, app)

    if to_status in TERMINAL_STATES:
        tracking.cancel_open_follow_ups(db, app, f"Application {to_status.lower()}")

    db.add(
        ApplicationEvent(
            application_id=app.id,
            from_status=old_status,
            to_status=to_status,
            actor=actor,
            note=note,
        )
    )

    db.add(
        AuditLog(
            user_id=app.user_id,
            action="application.status_changed",
            detail={
                "application_id": str(app.id),
                "from": old_status,
                "to": to_status,
                "actor": actor,
                "note": note,
            },
        )
    )

    db.commit()
    db.refresh(app)

    return app


def validate_grounding(
    text: str,
    candidate_text: str,
) -> list[str]:

    issues = []

    if not text:
        return issues

    source = candidate_text.lower()

    tokens = re.findall(
        r"\b(?:"
        r"\d+(?:\.\d+)?\s*years?"
        r"|python"
        r"|java"
        r"|aws"
        r"|kubernetes"
        r"|langchain"
        r"|langgraph"
        r"|fastapi"
        r"|docker"
        r"|react"
        r"|postgresql"
        r"|redis"
        r")\b",
        text.lower(),
    )

    for token in tokens:
        if token not in source:
            issues.append(
                f"Unverified claim: {token}"
            )

    return issues


def prepare(
    db: Session,
    app: Application,
):
    job = db.get(Job, app.job_id)

    if not job:
        raise ValueError("Job not found")

    resume = db.scalar(
        select(Resume)
        .where(
            Resume.user_id == app.user_id,
            Resume.is_active.is_(True),
        )
        .order_by(Resume.updated_at.desc())
    )

    if not resume:
        raise ValueError("Active resume not found")

    candidate = db.scalar(
        select(CandidateIntelligence)
        .where(
            CandidateIntelligence.user_id == app.user_id
        )
    )

    source = (
        (resume.parsed_text or "")
        + "\n"
        + (
            candidate.professional_summary
            if candidate
            else ""
        )
    )

    # RAG retrieval for job-specific context
    context = search(
        db,
        app.user_id,
        (
            (job.description or "")
            + " "
            + (job.requirements or "")
        ),
        8,
    )

    # Candidate skills
    skills = ", ".join(
        (
            candidate.core_skills
            if candidate
            else []
        )[:12]
    )

    # Grounded cover letter
    cover = (
        f"Dear Hiring Team,\n\n"
        f"I am interested in the {job.title} "
        f"opportunity at {job.company}. "
        f"My background includes {skills}. "
        f"I would welcome the opportunity to discuss "
        f"how my experience aligns with the role.\n\n"
        f"Regards"
    )

    grounding_issues = validate_grounding(
        cover,
        source,
    )

    package = db.scalar(
        select(ApplicationPackage)
        .where(
            ApplicationPackage.application_id == app.id
        )
    )

    if not package:
        package = ApplicationPackage(
            application_id=app.id
        )
        db.add(package)

    package.resume_id = resume.id
    package.resume_content = resume.parsed_text

    package.cover_letter = cover

    package.answers = {
        "Why are you interested?": (
            f"I am interested in the {job.title} role "
            f"because it aligns with my documented "
            f"experience and skills."
        )
    }

    package.grounding_issues = grounding_issues

    package.readiness = (
        "READY"
        if not grounding_issues
        else "NEEDS_REVIEW"
    )

    db.commit()
    db.refresh(package)

    # Application lifecycle:
    #
    # DRAFT
    #   ↓
    # PREPARED
    #   ↓
    # PENDING_APPROVAL
    #
    # User then explicitly approves:
    #
    # PENDING_APPROVAL
    #   ↓
    # APPROVED
    #
    if app.status == "DRAFT":
        transition(
            db,
            app,
            "PREPARED",
            "system",
            "Application package prepared",
        )

    if app.status == "PREPARED":
        transition(
            db,
            app,
            "PENDING_APPROVAL",
            "system",
            "Application package ready for user approval",
        )

    return package