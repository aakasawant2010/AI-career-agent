from pydantic import BaseModel, Field
from uuid import UUID
class DocumentIngest(BaseModel):
    kind: str = Field(min_length=1, max_length=50)
    title: str
    content: str = Field(min_length=1)
    source_id: str | None = None
    metadata: dict = Field(default_factory=dict)
class DocumentResponse(BaseModel):
    id: UUID; kind: str; title: str; chunks: int
class RagSearchRequest(BaseModel):
    query: str = Field(min_length=1)
    limit: int = Field(default=8, ge=1, le=30)
    kind: str | None = None
