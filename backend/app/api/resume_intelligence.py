from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from uuid import UUID

from app.api.deps import CurrentUser
from app.core.database import get_db
from app.models.resume import Resume
from app.models.resume_intelligence import ResumeIntelligence
from app.schemas.resume_intelligence import ResumeIntelligenceResponse
from app.services.resume_intelligence import extract_resume_intelligence

router = APIRouter(
    prefix="/resume-intelligence",
    tags=["Resume Intelligence"],
)


@router.post("/{resume_id}/generate", response_model=ResumeIntelligenceResponse)
def generate_resume_intelligence(
    resume_id: UUID,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
):
    resume = (
        db.query(Resume)
        .filter(
            Resume.id == resume_id,
            Resume.user_id == current_user.id,
        )
        .first()
    )

    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")

    if not resume.parsed_text:
        raise HTTPException(status_code=400, detail="Resume text is empty")

    try:
        data = extract_resume_intelligence(resume.parsed_text)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    intelligence = (
        db.query(ResumeIntelligence)
        .filter(ResumeIntelligence.resume_id == resume.id)
        .first()
    )

    if not intelligence:
        intelligence = ResumeIntelligence(resume_id=resume.id)
        db.add(intelligence)

    for field in [
        "skills", "experience", "education", "projects",
        "certifications", "job_titles", "technologies",
        "total_experience_years", "summary",
    ]:
        setattr(intelligence, field, data.get(field))

    db.commit()
    db.refresh(intelligence)
    return intelligence


@router.get("/{resume_id}", response_model=ResumeIntelligenceResponse)
def get_resume_intelligence(
    resume_id: UUID,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
):
    intelligence = (
        db.query(ResumeIntelligence)
        .join(Resume, Resume.id == ResumeIntelligence.resume_id)
        .filter(
            ResumeIntelligence.resume_id == resume_id,
            Resume.user_id == current_user.id,
        )
        .first()
    )

    if not intelligence:
        raise HTTPException(status_code=404, detail="Resume intelligence not found")

    return intelligence
