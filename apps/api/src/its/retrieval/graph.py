"""Graph traversal (RET-5): recursive CTE over skill_edges, with a depth limit.

The Obsidian [[wikilink]] graph is treated identically (note edges land in the same
skill_edges table); no separate graph store while traversal depth stays small.
"""

from sqlalchemy import text
from sqlalchemy.orm import Session


def prerequisites(session: Session, skill_id: str, max_depth: int = 5) -> list[dict]:
    """All prerequisite skills of `skill_id`, transitively, with their min depth."""
    rows = session.execute(
        text(
            """
            WITH RECURSIVE deps(skill_id, depth) AS (
                SELECT from_skill, 1 FROM skill_edges
                  WHERE to_skill = :sid AND kind = 'prerequisite'
                UNION ALL
                SELECT se.from_skill, d.depth + 1
                  FROM skill_edges se JOIN deps d ON se.to_skill = d.skill_id
                  WHERE se.kind = 'prerequisite' AND d.depth < :md
            )
            SELECT skill_id::text AS skill_id, min(depth) AS depth
            FROM deps GROUP BY skill_id ORDER BY depth
            """
        ),
        {"sid": skill_id, "md": max_depth},
    )
    return [dict(r._mapping) for r in rows]
