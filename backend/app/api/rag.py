from datetime import date, datetime
from enum import Enum
from typing import Any, Mapping
from uuid import UUID

from fastapi import APIRouter, Depends

from sqlalchemy import func, select
from sqlalchemy.inspection import inspect as sa_inspect
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser
from app.core.database import get_db
from app.models.rag import Document, DocumentChunk
from app.schemas.rag import (
    DocumentIngest,
    DocumentResponse,
    RagSearchRequest,
)
from app.services.rag import ingest_document, search


router = APIRouter(prefix="/rag", tags=["RAG"])


def _json_safe(value: Any) -> Any:
    """
    Convert SQLAlchemy ORM objects and other non-JSON-safe values
    into plain Python objects.

    This prevents FastAPI's jsonable_encoder from recursively
    traversing SQLAlchemy relationships.
    """

    # None / primitive values
    if value is None or isinstance(value, (str, int, float, bool)):
        return value

    # UUID
    if isinstance(value, UUID):
        return str(value)

    # Date / datetime
    if isinstance(value, (datetime, date)):
        return value.isoformat()

    # Enum
    if isinstance(value, Enum):
        return value.value

    # Dictionary / Mapping
    if isinstance(value, Mapping):
        return {
            str(key): _json_safe(item)
            for key, item in value.items()
        }

    # List / tuple / set
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(item) for item in value]

    # SQLAlchemy ORM object
    #
    # IMPORTANT:
    # Only serialize actual database columns.
    # We intentionally do NOT serialize relationships.
    if hasattr(value, "__table__"):
        try:
            mapper = sa_inspect(value)

            return {
                column.key: _json_safe(getattr(value, column.key))
                for column in mapper.mapper.column_attrs
            }

        except Exception:
            return str(value)

    # SQLAlchemy Row-like objects
    if hasattr(value, "_mapping"):
        return {
            str(key): _json_safe(item)
            for key, item in value._mapping.items()
        }

    # Objects exposing __dict__
    if hasattr(value, "__dict__"):
        try:
            return {
                key: _json_safe(item)
                for key, item in vars(value).items()
                if not key.startswith("_")
            }
        except Exception:
            return str(value)

    # Final fallback
    return str(value)


@router.post(
    "/documents",
    response_model=DocumentResponse,
)
def ingest(
    current_user: CurrentUser,
    data: DocumentIngest,
    db: Session = Depends(get_db),
):
    doc = ingest_document(
        db,
        current_user.id,
        data.kind,
        data.title,
        data.content,
        data.source_id,
        data.metadata,
    )

    count = (
        db.scalar(
            select(func.count()).where(
                DocumentChunk.document_id == doc.id
            )
        )
        or 0
    )

    return DocumentResponse(
        id=doc.id,
        kind=doc.kind,
        title=doc.title,
        chunks=count,
    )


@router.post("/search")
def rag_search(
    current_user: CurrentUser,
    data: RagSearchRequest,
    db: Session = Depends(get_db),
):
    results = search(
        db,
        current_user.id,
        data.query,
        data.limit,
        data.kind,
    )

    return {
        "query": data.query,
        "results": _json_safe(results),
    }