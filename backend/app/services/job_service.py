from __future__ import annotations

import hashlib
import re
from collections.abc import Iterable
from datetime import datetime
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.integrations.job_sources import get_adapter
from app.models.job import Job
from app.schemas.job import JobImport


SKILL_CATALOG = [
    "python", "sql", "java", "c++", "javascript", "typescript", "fastapi", "flask", "django",
    "langchain", "langgraph", "rag", "llm", "llms", "ai agents", "agentic ai", "prompt engineering",
    "vector search", "embeddings", "pinecone", "faiss", "chromadb", "mem0", "openai", "groq", "gemini",
    "pytorch", "tensorflow", "scikit-learn", "pandas", "numpy", "postgresql", "mysql", "mongodb",
    "redis", "celery", "docker", "kubernetes", "aws", "ec2", "eks", "lambda", "terraform",
    "github actions", "git", "rest apis", "microservices", "websockets", "prometheus", "grafana",
    "langsmith", "langfuse", "deepeval", "elasticsearch", "kibana", "gcp", "azure",
]

ALIASES = {
    "genai": "generative ai",
    "generative ai": "generative ai",
    "gen ai": "generative ai",
    "artificial intelligence": "ai",
    "large language model": "llm",
    "large language models": "llm",
    "postgres": "postgresql",
    "k8s": "kubernetes",
    "tf": "terraform",
}


def normalize_token(value: str) -> str:
    value = re.sub(r"[^a-z0-9+#.\- ]+", " ", value.lower()).strip()
    return ALIASES.get(value, value)


def extract_skills(text: str) -> list[str]:
    haystack = f" {text.lower()} "
    found: list[str] = []
    for skill in SKILL_CATALOG:
        pattern = r"(?<![a-z0-9+#])" + re.escape(skill) + r"(?![a-z0-9+#])"
        if re.search(pattern, haystack) and skill not in found:
            found.append(skill)
    return sorted(found)


def parse_experience(text: str) -> tuple[float | None, float | None]:
    patterns = [
        r"(\d+(?:\.\d+)?)\s*[-–to]+\s*(\d+(?:\.\d+)?)\s*(?:years?|yrs?)",
        r"(\d+(?:\.\d+)?)\s*\+?\s*(?:years?|yrs?)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text.lower())
        if match:
            minimum = float(match.group(1))
            maximum = float(match.group(2)) if match.lastindex and match.lastindex >= 2 else None
            return minimum, maximum
    return None, None


def parse_salary_lpa(text: str) -> tuple[float | None, float | None, str | None]:
    lower = text.lower()
    salary_text = None
    match = re.search(r"(?:₹|inr|rs\.?)[^\n]{0,40}", text, re.I)
    if match:
        salary_text = match.group(0).strip()
    range_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:-|to)\s*(\d+(?:\.\d+)?)\s*(?:lpa|lakhs?|lacs?)", lower)
    if range_match:
        return float(range_match.group(1)), float(range_match.group(2)), salary_text
    single = re.search(r"(\d+(?:\.\d+)?)\s*(?:lpa|lakhs?|lacs?)", lower)
    if single:
        value = float(single.group(1))
        return value, value, salary_text
    return None, None, salary_text


def infer_work_mode(text: str) -> str:
    lower = text.lower()
    if "hybrid" in lower:
        return "hybrid"
    if "remote" in lower or "work from home" in lower or "wfh" in lower:
        return "remote"
    if "on-site" in lower or "onsite" in lower or "office" in lower:
        return "onsite"
    return "unknown"


def build_job_hash(data: JobImport) -> str:
    identity = data.external_id or ""
    if not identity:
        identity = "|".join(
            [data.source, data.company, data.title, data.location or "", data.apply_url or "", data.description[:2000]]
        )
    return hashlib.sha256(identity.strip().lower().encode("utf-8")).hexdigest()


def normalize_job(data: JobImport) -> JobImport:
    combined = "\n".join(filter(None, [data.title, data.description, data.requirements]))
    parsed_min_exp, parsed_max_exp = parse_experience(combined)
    parsed_min_salary, parsed_max_salary, parsed_salary_text = parse_salary_lpa(combined)
    skills = sorted({normalize_token(x) for x in data.skills if x.strip()})
    skills = sorted(set(skills) | set(extract_skills(combined)))
    technologies = sorted({normalize_token(x) for x in data.technologies if x.strip()} | set(skills))
    work_mode = data.work_mode if data.work_mode != "unknown" else infer_work_mode(combined)
    return data.model_copy(update={
        "skills": skills,
        "technologies": technologies,
        "work_mode": work_mode,
        "min_salary_lpa": data.min_salary_lpa if data.min_salary_lpa is not None else parsed_min_salary,
        "max_salary_lpa": data.max_salary_lpa if data.max_salary_lpa is not None else parsed_max_salary,
        "salary_text": data.salary_text or parsed_salary_text,
        "experience_min_years": data.experience_min_years if data.experience_min_years is not None else parsed_min_exp,
        "experience_max_years": data.experience_max_years if data.experience_max_years is not None else parsed_max_exp,
    })


def upsert_job(db: Session, payload: JobImport) -> tuple[Job, bool]:
    normalized = normalize_job(payload)
    job_hash = build_job_hash(normalized)
    job = db.scalar(select(Job).where(Job.job_hash == job_hash))
    values = normalized.model_dump()
    values["job_hash"] = job_hash
    if job is None:
        job = Job(**values)
        db.add(job)
        created = True
    else:
        for field, value in values.items():
            setattr(job, field, value)
        created = False
    db.commit()
    db.refresh(job)
    return job, created


def import_jobs(db: Session, payloads: Iterable[JobImport]) -> tuple[list[Job], int, int]:
    jobs: list[Job] = []
    created = updated = 0
    for payload in payloads:
        job, was_created = upsert_job(db, payload)
        jobs.append(job)
        if was_created:
            created += 1
        else:
            updated += 1
    return jobs, created, updated


def ingest_source(db: Session, source_type: str, board: str, source_url: str | None = None) -> tuple[list[Job], int, int]:
    adapter = get_adapter(source_type, board, source_url)
    payloads = [JobImport.model_validate(item) for item in adapter.fetch()]
    return import_jobs(db, payloads)


def list_jobs(
    db: Session,
    *,
    q: str | None = None,
    location: str | None = None,
    work_mode: str | None = None,
    source: str | None = None,
    min_salary_lpa: float | None = None,
    max_salary_lpa: float | None = None,
    limit: int = 20,
    offset: int = 0,
) -> tuple[list[Job], int]:
    filters = [Job.is_active.is_(True)]
    if q:
        term = f"%{q.strip()}%"
        filters.append(or_(Job.title.ilike(term), Job.company.ilike(term), Job.description.ilike(term)))
    if location:
        filters.append(Job.location.ilike(f"%{location.strip()}%"))
    if work_mode:
        filters.append(Job.work_mode == work_mode.lower())
    if source:
        filters.append(Job.source == source.lower())
    if min_salary_lpa is not None:
        filters.append(or_(Job.max_salary_lpa.is_(None), Job.max_salary_lpa >= min_salary_lpa))
    if max_salary_lpa is not None:
        filters.append(or_(Job.min_salary_lpa.is_(None), Job.min_salary_lpa <= max_salary_lpa))
    total = db.scalar(select(func.count()).select_from(Job).where(*filters)) or 0
    items = list(db.scalars(select(Job).where(*filters).order_by(Job.posted_at.desc().nullslast(), Job.created_at.desc()).offset(offset).limit(limit)))
    return items, total
