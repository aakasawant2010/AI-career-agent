from __future__ import annotations

import hashlib

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.rag import Document, DocumentChunk
from app.services.embeddings import embed_texts, cosine


def chunk_text(
    text: str,
    size: int = 900,
    overlap: int = 120,
) -> list[str]:
    text = " ".join((text or "").split())

    if not text:
        return []

    chunks: list[str] = []
    start = 0

    while start < len(text):
        end = min(len(text), start + size)

        if end < len(text):
            cut = text.rfind(" ", start, end)

            if cut > start + size // 2:
                end = cut

        chunks.append(text[start:end].strip())

        if end >= len(text):
            break

        start = max(end - overlap, start + 1)

    return chunks


def ingest_document(
    db: Session,
    user_id,
    kind: str,
    title: str,
    content: str,
    source_id=None,
    metadata=None,
) -> Document:
    digest = hashlib.sha256(
        content.encode("utf-8")
    ).hexdigest()

    # Prevent duplicate documents for the same user.
    doc = db.scalar(
        select(Document).where(
            Document.user_id == user_id,
            Document.content_hash == digest,
        )
    )

    if doc:
        return doc

    doc = Document(
        user_id=user_id,
        kind=kind,
        title=title,
        content=content,
        source_id=str(source_id) if source_id else None,
        doc_metadata=metadata or {},
        content_hash=digest,
    )

    db.add(doc)
    db.flush()

    chunks = chunk_text(content)
    vectors = embed_texts(chunks)

    for index, (chunk, vector) in enumerate(
        zip(chunks, vectors)
    ):
        db.add(
            DocumentChunk(
                document_id=doc.id,
                chunk_index=index,
                content=chunk,
                embedding=vector,
                metadata=metadata or {},
            )
        )

    db.commit()
    db.refresh(doc)

    return doc


def search(
    db: Session,
    user_id,
    query: str,
    limit: int = 8,
    kind: str | None = None,
) -> list[dict]:
    """
    Perform local semantic search.

    The application currently uses local embeddings and calculates
    cosine similarity in Python. This keeps local SQLite development
    independent of pgvector.
    """

    # Generate embedding for the search query.
    query_vectors = embed_texts([query])

    if not query_vectors:
        return []

    query_vector = query_vectors[0]

    # Get the user's document chunks.
    stmt = (
        select(DocumentChunk, Document)
        .join(
            Document,
            Document.id == DocumentChunk.document_id,
        )
        .where(
            Document.user_id == user_id
        )
    )

    if kind:
        stmt = stmt.where(
            Document.kind == kind
        )

    rows = db.execute(stmt).all()

    # Calculate cosine similarity.
    ranked = sorted(
        (
            (
                cosine(query_vector, chunk.embedding),
                chunk,
                document,
            )
            for chunk, document in rows
        ),
        key=lambda item: item[0],
        reverse=True,
    )

    ranked = ranked[:limit]

    results: list[dict] = []

    for score, chunk, document in ranked:

        # Convert SQLAlchemy/JSON metadata into a plain dictionary.
        raw_metadata = chunk.metadata

        if raw_metadata is None:
            metadata = {}

        elif isinstance(raw_metadata, dict):
            metadata = dict(raw_metadata)

        else:
            try:
                metadata = dict(raw_metadata)
            except (TypeError, ValueError):
                metadata = {}

        results.append(
            {
                "score": round(
                    max(
                        0.0,
                        min(
                            1.0,
                            (score + 1) / 2,
                        ),
                    ),
                    4,
                ),
                "chunk_id": str(chunk.id),
                "document_id": str(document.id),
                "title": document.title,
                "kind": document.kind,
                "content": chunk.content,
                "metadata": metadata,
            }
        )

    return results