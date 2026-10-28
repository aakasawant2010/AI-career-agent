import uuid

from pydantic import BaseModel, Field


class ProjectCreate(BaseModel):
    name: str
    description: str | None = None
    technologies: list[str] = Field(default_factory=list)
    github_url: str | None = None
    live_url: str | None = None
    role: str | None = None
    featured: bool = False


class ProjectResponse(ProjectCreate):
    id: uuid.UUID
    user_id: uuid.UUID

    model_config = {
        "from_attributes": True
    }