import uuid

from pydantic import BaseModel


class ResumeIntelligenceResponse(BaseModel):
    id: uuid.UUID
    resume_id: uuid.UUID

    skills: list = []
    experience: list = []
    education: list = []
    projects: list = []
    certifications: list = []
    job_titles: list = []
    technologies: list = []

    total_experience_years: float | None = None
    summary: str | None = None

    model_config = {
        "from_attributes": True
    }