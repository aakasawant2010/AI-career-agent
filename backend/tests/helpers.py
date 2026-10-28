"""Shared builders for API-level tests."""

from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.models.application import Application, ApplicationEvent
from app.models.candidate_intelligence import CandidateIntelligence
from app.models.user import User


def auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def register_and_login(client, email: str, password: str = "s3cret-pass1") -> dict:
    client.post("/auth/register", json={"email": email, "password": password, "full_name": email})
    r = client.post("/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return r.json()


def make_job(client, token: str, **overrides) -> dict:
    payload = {
        "source": "manual",
        "external_id": overrides.pop("external_id", "job-1"),
        "title": "Generative AI Engineer",
        "company": "Demo AI",
        "location": "Pune",
        "work_mode": "hybrid",
        "description": "Python, LangChain, RAG, FastAPI and AWS. 3+ years experience.",
    }
    payload.update(overrides)
    r = client.post("/jobs/import", headers=auth(token), json=payload)
    assert r.status_code == 200, r.text
    return r.json()["jobs"][0]


def make_application(client, token: str, job_id: str) -> dict:
    r = client.post("/applications", headers=auth(token), json={"job_id": job_id})
    assert r.status_code == 200, r.text
    return r.json()


def set_status(client, token: str, app_id: str, status: str, expect: int = 200):
    r = client.post(f"/applications/{app_id}/status", headers=auth(token), json={"status": status})
    assert r.status_code == expect, r.text
    return r


def walk(client, token: str, app_id: str, *statuses: str):
    for s in statuses:
        set_status(client, token, app_id, s)


TO_SUBMITTED = ("PREPARED", "PENDING_APPROVAL", "APPROVED", "SUBMITTED")


def backdate(db, app_id: str, *, submitted_days_ago: float | None = None, event_days_ago: dict | None = None):
    """Rewrite timestamps so time-based analytics can be tested deterministically."""
    import uuid

    now = datetime.now(timezone.utc)
    app = db.get(Application, uuid.UUID(app_id))
    if submitted_days_ago is not None:
        app.submitted_at = now - timedelta(days=submitted_days_ago)
    for event in db.scalars(select(ApplicationEvent).where(ApplicationEvent.application_id == app.id)):
        if event_days_ago and event.to_status in event_days_ago:
            event.created_at = now - timedelta(days=event_days_ago[event.to_status])
    db.commit()


def add_candidate(db, **overrides) -> CandidateIntelligence:
    user = db.scalar(select(User))
    data = {
        "career_profile": {"target_roles": ["Generative AI Engineer"], "total_experience_years": 3.5},
        "resume_intelligence": {},
        "projects": [{"name": "Career Agent", "technologies": ["FastAPI", "LangChain"]}],
        "core_skills": ["python", "fastapi", "langchain", "rag"],
        "technologies": ["python", "fastapi", "langchain", "rag"],
        "target_roles": ["Generative AI Engineer"],
        "preferred_locations": ["Pune"],
        "professional_summary": "AI engineer",
    }
    data.update(overrides)
    row = CandidateIntelligence(user_id=user.id, **data)
    db.add(row)
    db.commit()
    return row
