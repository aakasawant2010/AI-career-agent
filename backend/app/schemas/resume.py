import uuid

from pydantic import BaseModel


class ResumeCreate(BaseModel):
    name: str
    file_path: str
    file_type: str
    parsed_text: str | None = None
    is_active: bool = False


class ResumeUpdate(BaseModel):
    name: str | None = None
    parsed_text: str | None = None
    is_active: bool | None = None


class ResumeResponse(ResumeCreate):
    id: uuid.UUID
    user_id: uuid.UUID

    model_config = {
        "from_attributes": True
    }