from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser
from app.core.database import get_db
from app.models.job import Job
from app.models.job_match import JobMatch
from app.schemas.job import JobImport, JobImportResult, JobIngestRequest, JobListResponse, JobResponse
from app.schemas.job_match import JobMatchResponse, MatchWeights, RecommendationListResponse, RecommendationResponse
from app.services.job_matching import match_all_jobs, match_job
from app.services.job_service import import_jobs, ingest_source, list_jobs, normalize_job

router = APIRouter(prefix="/jobs", tags=["Jobs"])


@router.post("/import", response_model=JobImportResult)
def import_job(current_user: CurrentUser, data: JobImport, db: Session = Depends(get_db)):
    del current_user
    try:
        jobs, created, updated = import_jobs(db, [data])
        return JobImportResult(created=created, updated=updated, skipped=0, jobs=jobs)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Job import failed: {exc}") from exc


@router.post("/import/bulk", response_model=JobImportResult)
def import_jobs_bulk(current_user: CurrentUser, data: list[JobImport], db: Session = Depends(get_db)):
    del current_user
    if not data:
        raise HTTPException(status_code=400, detail="At least one job is required")
    try:
        jobs, created, updated = import_jobs(db, data)
        return JobImportResult(created=created, updated=updated, skipped=0, jobs=jobs)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Bulk job import failed: {exc}") from exc


@router.post("/ingest", response_model=JobImportResult)
def ingest_jobs(current_user: CurrentUser, data: JobIngestRequest, db: Session = Depends(get_db)):
    del current_user
    try:
        jobs, created, updated = ingest_source(db, data.source_type, data.board, data.source_url)
        return JobImportResult(created=created, updated=updated, skipped=0, jobs=jobs)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Job source ingestion failed: {exc}") from exc


@router.get("", response_model=JobListResponse)
def get_jobs(
    current_user: CurrentUser,
    q: str | None = Query(default=None),
    location: str | None = Query(default=None),
    work_mode: str | None = Query(default=None),
    source: str | None = Query(default=None),
    min_salary_lpa: float | None = Query(default=None, ge=0),
    max_salary_lpa: float | None = Query(default=None, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    del current_user
    items, total = list_jobs(db, q=q, location=location, work_mode=work_mode, source=source, min_salary_lpa=min_salary_lpa, max_salary_lpa=max_salary_lpa, limit=limit, offset=offset)
    return JobListResponse(items=items, total=total, limit=limit, offset=offset)


@router.get("/recommendations", response_model=RecommendationListResponse)
def recommendations(
    current_user: CurrentUser,
    minimum_score: float = Query(default=0, ge=0, le=100),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    matches = list(db.scalars(select(JobMatch).where(JobMatch.user_id == current_user.id, JobMatch.score >= minimum_score).order_by(JobMatch.score.desc()).limit(limit)))
    items = []
    for match in matches:
        job = db.get(Job, match.job_id)
        if job:
            items.append(RecommendationResponse(job=JobResponse.model_validate(job).model_dump(mode="json"), match=JobMatchResponse.model_validate(match)))
    return RecommendationListResponse(items=items, total=len(items))


@router.get("/{job_id}", response_model=JobResponse)
def get_job(job_id: UUID, current_user: CurrentUser, db: Session = Depends(get_db)):
    del current_user
    job = db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.post("/{job_id}/analyze", response_model=JobResponse)
def analyze_job(job_id: UUID, current_user: CurrentUser, db: Session = Depends(get_db)):
    del current_user
    job = db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    payload = JobImport.model_validate(job)
    normalized = normalize_job(payload)
    for field, value in normalized.model_dump().items():
        setattr(job, field, value)
    db.commit()
    db.refresh(job)
    return job


@router.post("/{job_id}/match", response_model=JobMatchResponse)
def match_single_job(job_id: UUID, current_user: CurrentUser, weights: MatchWeights | None = None, db: Session = Depends(get_db)):
    job = db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    try:
        match = match_job(db, current_user.id, job, weights.model_dump() if weights else None)
        return match
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/match-all", response_model=list[JobMatchResponse])
def match_all(current_user: CurrentUser, weights: MatchWeights | None = None, db: Session = Depends(get_db)):
    try:
        matches = match_all_jobs(db, current_user.id, weights.model_dump() if weights else None)
        return matches
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
