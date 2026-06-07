"""Ingestion pipeline (CON-2): embed ONLY prose, keep the query as sidecar metadata.

Flow per file: parse -> upsert content_notes (prose, source_path, skill_id from
frontmatter) -> chunk prose by paragraph -> embed each chunk -> content_embeddings
(with the first sidecar query attached) -> persist wikilinks as 'related' skill edges.

Idempotent per source_path: a re-ingest deletes the prior note (cascading its
embeddings) and rewrites it. Runs as the privileged owner role (content tables
carry no RLS).
"""

import re
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.orm import Session

from its.content.parser import parse_note
from its.db.models import ContentEmbedding, ContentNote
from its.llm.embeddings import Embedder, get_embedder

_PARA = re.compile(r"\n\s*\n")


def _chunks(prose: str) -> list[str]:
    parts = [p.strip() for p in _PARA.split(prose) if p.strip()]
    if parts:
        return parts
    return [prose.strip()] if prose.strip() else []


def _skill_id_for_key(session: Session, key: str) -> str | None:
    return session.execute(text("SELECT id FROM skills WHERE key = :k"), {"k": key}).scalar()


def ingest_file(
    session: Session,
    path: str | Path,
    *,
    embedder: Embedder | None = None,
    source_path: str | None = None,
) -> ContentNote:
    embedder = embedder or get_embedder()
    p = Path(path)
    parsed = parse_note(p.read_text(encoding="utf-8"))
    src = source_path if source_path is not None else str(p)

    skill_key = parsed.frontmatter.get("skill")
    skill_id = _skill_id_for_key(session, skill_key) if skill_key else None

    # idempotent rewrite for this source_path (cascade removes old embeddings)
    session.execute(text("DELETE FROM content_notes WHERE source_path = :s"), {"s": src})

    note = ContentNote(skill_id=skill_id, source_path=src, prose=parsed.prose)
    session.add(note)
    session.flush()

    sidecar = parsed.sidecar_queries[0] if parsed.sidecar_queries else None
    for chunk in _chunks(parsed.prose):
        session.add(
            ContentEmbedding(
                note_id=note.id,
                chunk=chunk,
                embedding=embedder.embed(chunk),
                sidecar_query=sidecar,
            )
        )

    # wikilinks -> 'related' skill edges (only when both endpoints resolve to skills)
    if skill_id:
        for link in parsed.links:
            target = _skill_id_for_key(session, link)
            if target and target != skill_id:
                session.execute(
                    text(
                        "INSERT INTO skill_edges (from_skill, to_skill, kind) "
                        "VALUES (:f, :t, 'related') ON CONFLICT DO NOTHING"
                    ),
                    {"f": skill_id, "t": target},
                )
    session.flush()
    return note


def ingest_vault(session: Session, vault_dir: str | Path, *, embedder: Embedder | None = None) -> int:
    """Ingest every *.md in vault_dir (recursively). Files starting with '_' are skipped."""
    embedder = embedder or get_embedder()
    count = 0
    for md in sorted(Path(vault_dir).rglob("*.md")):
        if md.name.startswith("_"):
            continue
        ingest_file(session, md, embedder=embedder, source_path=str(md))
        count += 1
    return count
