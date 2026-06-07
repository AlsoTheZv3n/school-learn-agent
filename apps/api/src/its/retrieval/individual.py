"""Individual mode (RET-3, safety-critical): always scoped to one student_id.

Double safeguard: require_student_scope (SAF-2, fail-closed) AND RLS. Even if the
code forgot the filter, RLS refuses foreign rows. Run inside a scoped_session.
"""

from sqlalchemy import text
from sqlalchemy.orm import Session

from its.auth.deps import Principal
from its.safety.scoping import require_student_scope


def mastery_overview(session: Session, principal: Principal) -> list[dict]:
    sid = require_student_scope(principal)  # fail-closed: no scope -> ScopeError
    rows = session.execute(
        text(
            """
            SELECT ls.skill_id::text AS skill_id, s.name, ls.mastery,
                   ls.uncertainty, ls.attempts_count
            FROM learner_state ls
            JOIN skills s ON s.id = ls.skill_id
            WHERE ls.student_id = :sid
            ORDER BY s.name
            """
        ),
        {"sid": sid},
    )
    return [dict(r._mapping) for r in rows]
