from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.matching import run_matching_workflow
from app.models.candidate_intelligence import CandidateIntelligence
from app.models.job import Job
from app.models.job_match import JobMatch


def get_candidate(db: Session, user_id):
    return db.scalar(select(CandidateIntelligence).where(CandidateIntelligence.user_id == user_id))


def match_job(db: Session, user_id, job: Job, weights: dict[str, float] | None = None) -> JobMatch:
    candidate = get_candidate(db, user_id)
    if candidate is None:
        raise ValueError("Candidate intelligence not found. Generate candidate intelligence first.")
    result = run_matching_workflow(candidate, job, weights)
    match = db.scalar(select(JobMatch).where(JobMatch.user_id == user_id, JobMatch.job_id == job.id))
    if match is None:
        match = JobMatch(user_id=user_id, job_id=job.id)
        db.add(match)
    for key, value in result.items():
        setattr(match, key, value)
    db.commit()
    db.refresh(match)
    return match


def match_all_jobs(db: Session, user_id, weights: dict[str, float] | None = None) -> list[JobMatch]:
    jobs = list(db.scalars(select(Job).where(Job.is_active.is_(True))))
    return [match_job(db, user_id, job, weights) for job in jobs]
