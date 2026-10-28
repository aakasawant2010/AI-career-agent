"""Phase 8 – application analytics.

All numbers are derived from the immutable ``application_events`` history, not just
the current status, so an application that reached INTERVIEW and was later
rejected still counts toward the interview stage.

Loading is separated from computing: ``load_records`` does three queries and the
``compute_*`` functions are pure, which keeps them cheap to unit test.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from statistics import median

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.timeutil import as_utc
from app.models.application import Application, ApplicationEvent, FollowUp
from app.models.job import Job
from app.models.job_match import JobMatch

PIPELINE = ["SUBMITTED", "SCREENING", "INTERVIEW", "OFFER", "ACCEPTED"]
RANK = {status: i + 1 for i, status in enumerate(PIPELINE)}
RESPONSE_STATES = {"SCREENING", "INTERVIEW", "OFFER", "ACCEPTED", "REJECTED"}
BREAKDOWN_DIMENSIONS = ("source", "company", "role", "work_mode", "match_band")


@dataclass
class AppRecord:
    id: str
    status: str
    created_at: datetime | None
    submitted_at: datetime | None
    source: str
    company: str
    role: str
    work_mode: str
    match_score: float | None
    match_band: str
    events: list[tuple[str | None, str, datetime]] = field(default_factory=list)

    @property
    def max_rank(self) -> int:
        statuses = {self.status} | {to for _, to, _ in self.events}
        return max((RANK.get(s, 0) for s in statuses), default=0)

    @property
    def submitted(self) -> bool:
        return self.max_rank >= 1

    def first_response(self) -> tuple[str, datetime] | None:
        """First event after submission that shows the employer reacted."""
        for from_status, to_status, at in sorted(self.events, key=lambda e: e[2]):
            if to_status in RESPONSE_STATES and (from_status in RANK):
                return to_status, at
        return None

    def days_to_response(self) -> float | None:
        response = self.first_response()
        submitted_at = as_utc(self.submitted_at)
        if response is None or submitted_at is None:
            return None
        return max(0.0, (as_utc(response[1]) - submitted_at).total_seconds() / 86400)


def load_records(db: Session, user_id) -> list[AppRecord]:
    rows = db.execute(
        select(Application, Job)
        .join(Job, Job.id == Application.job_id)
        .where(Application.user_id == user_id)
    ).all()
    if not rows:
        return []

    ids = [a.id for a, _ in rows]
    events: dict = defaultdict(list)
    for e in db.scalars(select(ApplicationEvent).where(ApplicationEvent.application_id.in_(ids))):
        events[e.application_id].append((e.from_status, e.to_status, as_utc(e.created_at)))

    matches = {
        m.job_id: m for m in db.scalars(select(JobMatch).where(JobMatch.user_id == user_id))
    }

    records = []
    for app, job in rows:
        match = matches.get(job.id)
        records.append(
            AppRecord(
                id=str(app.id),
                status=app.status,
                created_at=as_utc(app.created_at),
                submitted_at=as_utc(app.submitted_at),
                source=job.source or "unknown",
                company=job.company,
                role=job.title,
                work_mode=job.work_mode or "unknown",
                match_score=match.score if match else None,
                match_band=match.recommendation if match else "unscored",
                events=events.get(app.id, []),
            )
        )
    return records


def _pct(numerator: int, denominator: int) -> float:
    return round(numerator / denominator * 100, 1) if denominator else 0.0


# --------------------------------------------------------------------- funnel


def compute_funnel(records: list[AppRecord]) -> dict:
    stages = [{"stage": "CREATED", "count": len(records)}]
    for status in PIPELINE:
        stages.append(
            {"stage": status, "count": sum(1 for r in records if r.max_rank >= RANK[status])}
        )
    previous = None
    for stage in stages:
        stage["conversion_from_previous"] = (
            _pct(stage["count"], previous) if previous is not None else None
        )
        previous = stage["count"]
    submitted = stages[1]["count"]
    for stage in stages[1:]:
        stage["conversion_from_submitted"] = _pct(stage["count"], submitted)
    return {
        "stages": stages,
        "rejected": sum(1 for r in records if r.status == "REJECTED"),
        "withdrawn": sum(1 for r in records if r.status == "WITHDRAWN"),
        "active": sum(
            1 for r in records if r.status not in {"ACCEPTED", "REJECTED", "WITHDRAWN"}
        ),
    }


# ------------------------------------------------------------------- response


def compute_response(records: list[AppRecord], now: datetime | None = None) -> dict:
    now = now or datetime.now(timezone.utc)
    ghost_cutoff = now - timedelta(days=get_settings().ghosted_after_days)

    submitted = [r for r in records if r.submitted]
    responded = [r for r in submitted if r.first_response() is not None]
    positive = [
        r for r in responded if r.first_response()[0] in {"SCREENING", "INTERVIEW", "OFFER", "ACCEPTED"}
    ]
    days = sorted(d for r in responded if (d := r.days_to_response()) is not None)
    ghosted = [
        r
        for r in submitted
        if r.first_response() is None
        and r.status == "SUBMITTED"
        and r.submitted_at is not None
        and as_utc(r.submitted_at) < ghost_cutoff
    ]
    return {
        "submitted": len(submitted),
        "responded": len(responded),
        "response_rate": _pct(len(responded), len(submitted)),
        "positive_response_rate": _pct(len(positive), len(submitted)),
        "avg_days_to_response": round(sum(days) / len(days), 1) if days else None,
        "median_days_to_response": round(median(days), 1) if days else None,
        "awaiting_response": sum(1 for r in submitted if r.status == "SUBMITTED"),
        "ghosted": len(ghosted),
        "ghosted_after_days": get_settings().ghosted_after_days,
    }


# ------------------------------------------------------------------ breakdown


def _group_key(record: AppRecord, by: str) -> str:
    return {
        "source": record.source,
        "company": record.company,
        "role": record.role,
        "work_mode": record.work_mode,
        "match_band": record.match_band,
    }[by]


def compute_breakdown(records: list[AppRecord], by: str, limit: int = 20) -> list[dict]:
    if by not in BREAKDOWN_DIMENSIONS:
        raise ValueError(f"'by' must be one of {', '.join(BREAKDOWN_DIMENSIONS)}")
    groups: dict[str, list[AppRecord]] = defaultdict(list)
    for r in records:
        groups[_group_key(r, by)].append(r)

    rows = []
    for key, items in groups.items():
        submitted = [r for r in items if r.submitted]
        responded = sum(1 for r in submitted if r.first_response() is not None)
        interviews = sum(1 for r in submitted if r.max_rank >= RANK["INTERVIEW"])
        offers = sum(1 for r in submitted if r.max_rank >= RANK["OFFER"])
        scores = [r.match_score for r in items if r.match_score is not None]
        rows.append(
            {
                "key": key,
                "applications": len(items),
                "submitted": len(submitted),
                "responses": responded,
                "interviews": interviews,
                "offers": offers,
                "response_rate": _pct(responded, len(submitted)),
                "interview_rate": _pct(interviews, len(submitted)),
                "offer_rate": _pct(offers, len(submitted)),
                "avg_match_score": round(sum(scores) / len(scores), 1) if scores else None,
            }
        )
    rows.sort(key=lambda r: (-r["applications"], r["key"]))
    return rows[:limit]


# ------------------------------------------------------------------- timeline


def _week_start(dt: datetime) -> datetime:
    d = as_utc(dt)
    return (d - timedelta(days=d.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)


def compute_timeline(records: list[AppRecord], weeks: int = 12, now: datetime | None = None) -> list[dict]:
    now = now or datetime.now(timezone.utc)
    first = _week_start(now) - timedelta(weeks=weeks - 1)
    buckets = {
        (first + timedelta(weeks=i)).date().isoformat(): {"created": 0, "submitted": 0, "responses": 0}
        for i in range(weeks)
    }

    def add(dt: datetime | None, field_name: str) -> None:
        if dt is None:
            return
        key = _week_start(dt).date().isoformat()
        if key in buckets:
            buckets[key][field_name] += 1

    for r in records:
        add(r.created_at, "created")
        add(r.submitted_at, "submitted")
        response = r.first_response()
        if response:
            add(response[1], "responses")
    return [{"week_start": k, **v} for k, v in buckets.items()]


# ------------------------------------------------------------------- overview


def pending_follow_ups(db: Session, user_id, now: datetime | None = None) -> tuple[int, int]:
    """(open, overdue) follow-up counts for a user."""
    now = now or datetime.now(timezone.utc)
    due_dates = [
        as_utc(d)
        for d in db.scalars(
            select(FollowUp.due_at)
            .join(Application, Application.id == FollowUp.application_id)
            .where(Application.user_id == user_id, FollowUp.status == "PENDING")
        )
    ]
    return len(due_dates), sum(1 for d in due_dates if d < now)


def compute_overview(db: Session, user_id, records: list[AppRecord] | None = None) -> dict:
    records = records if records is not None else load_records(db, user_id)
    open_followups, overdue_followups = pending_follow_ups(db, user_id)
    scores = [r.match_score for r in records if r.match_score is not None]
    response = compute_response(records)
    by_status: dict[str, int] = defaultdict(int)
    for r in records:
        by_status[r.status] += 1
    return {
        "total_applications": len(records),
        "by_status": dict(by_status),
        "avg_match_score": round(sum(scores) / len(scores), 1) if scores else 0.0,
        "response": response,
        "funnel": compute_funnel(records),
        "follow_ups": {"open": open_followups, "overdue": overdue_followups},
        "needs_attention": {
            "awaiting_your_approval": by_status.get("PENDING_APPROVAL", 0),
            "overdue_follow_ups": overdue_followups,
            "possibly_ghosted": response["ghosted"],
        },
    }
