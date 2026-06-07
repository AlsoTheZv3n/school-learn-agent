"""Semantic mode (RET-2): pgvector similarity over content_embeddings.

Returns prose chunks plus the associated sidecar query metadata (for a possible
escalation). Shared, scale-free knowledge — no student_id, no RLS needed: this is
study material, not a person-scoped datum.
"""

from sqlalchemy import text
from sqlalchemy.orm import Session

from its.llm.embeddings import Embedder, get_embedder


def _vector_literal(embedding: list[float]) -> str:
    return "[" + ",".join(repr(float(x)) for x in embedding) + "]"


def semantic_search(session: Session, query_embedding: list[float], k: int = 5) -> list[dict]:
    rows = session.execute(
        text(
            """
            SELECT ce.chunk, ce.sidecar_query, cn.skill_id::text AS skill_id
            FROM content_embeddings ce
            JOIN content_notes cn ON cn.id = ce.note_id
            ORDER BY ce.embedding <=> CAST(:q AS vector)   -- cosine distance (HNSW)
            LIMIT :k
            """
        ),
        {"q": _vector_literal(query_embedding), "k": k},
    )
    return [dict(r._mapping) for r in rows]


def semantic_search_text(
    session: Session, query: str, k: int = 5, embedder: Embedder | None = None
) -> list[dict]:
    """Convenience: embed `query` with the configured embedder, then search."""
    embedder = embedder or get_embedder()
    return semantic_search(session, embedder.embed(query), k=k)
