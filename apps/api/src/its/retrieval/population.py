"""Population mode (RET-4, safety-critical): GROUP BY aggregates, gated by min-cohort.

Every aggregate result passes through enforce_min_cohort before leaving the system,
so a "class average" over a group of one cannot become a de-anonymized disclosure.
"""

from sqlalchemy import text
from sqlalchemy.orm import Session

from its.safety.cohort import CohortResult, enforce_min_cohort


def skill_mastery_distribution(
    session: Session, class_id: str, skill_id: str
) -> CohortResult:
    row = session.execute(
        text(
            """
            SELECT count(*) AS n, avg(ls.mastery) AS avg_mastery
            FROM learner_state ls
            JOIN enrollments e ON e.student_id = ls.student_id
            WHERE e.class_id = :cid AND ls.skill_id = :skid
            """
        ),
        {"cid": class_id, "skid": skill_id},
    ).one()
    return enforce_min_cohort(
        n=int(row.n),
        payload={"avg_mastery": round(float(row.avg_mastery or 0.0), 3)},
    )
