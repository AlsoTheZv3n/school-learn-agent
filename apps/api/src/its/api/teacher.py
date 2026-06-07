"""Teacher endpoints (API-2, safety-critical).

RLS (teacher_*_in_class) ensures a teacher sees only students in their own classes —
the UI/queries need no extra filtering. Aggregates go through the min-cohort gate.
"""

from fastapi import APIRouter, Depends
from sqlalchemy import text

from its.api.schemas import CohortStat, NoteRequest, SkillMastery
from its.auth.deps import Principal, current_principal
from its.db.session import SessionLocal, scoped_session
from its.retrieval.population import skill_mastery_distribution
from its.safety.cohort import CohortTooSmall, enforce_min_cohort

router = APIRouter(prefix="/teacher", tags=["teacher"])


def _names_for(ids: list[str]) -> dict[str, str]:
    """Resolve student_id -> display_name (owner read). Only ever called with ids that
    RLS already authorized for this teacher, so RLS stays the authorization boundary."""
    if not ids:
        return {}
    with SessionLocal() as s:
        rows = s.execute(
            text("SELECT id::text AS id, display_name FROM students WHERE id::text = ANY(:ids)"),
            {"ids": ids},
        ).mappings().all()
    return {r["id"]: r["display_name"] for r in rows}


def _initials(name: str) -> str:
    parts = [p for p in name.replace(":", " ").split() if p]
    return ("".join(p[0] for p in parts[:2]) or "?").upper()


@router.get("/student/{student_id}/mastery", response_model=list[SkillMastery])
def student_mastery(
    student_id: str, principal: Principal = Depends(current_principal)
) -> list[SkillMastery]:
    with scoped_session(principal) as session:
        rows = (
            session.execute(
                text(
                    """
                    SELECT ls.skill_id::text AS skill_id, sk.name, ls.mastery,
                           ls.uncertainty, ls.attempts_count
                    FROM learner_state ls JOIN skills sk ON sk.id = ls.skill_id
                    WHERE ls.student_id = :sid
                    """
                ),
                {"sid": student_id},
            )
            .mappings()
            .all()
        )
    return [SkillMastery(**r) for r in rows]  # incl. uncertainty (open learner model)


@router.get(
    "/class/{class_id}/skill/{skill_id}/distribution", response_model=CohortStat
)
def class_distribution(
    class_id: str, skill_id: str, principal: Principal = Depends(current_principal)
) -> CohortStat:
    with scoped_session(principal) as session:
        res = skill_mastery_distribution(session, class_id, skill_id)  # via enforce_min_cohort
    return CohortStat(n=res.n, avg_mastery=res.payload["avg_mastery"])


@router.post("/student/{student_id}/note")
def add_note(
    student_id: str, note: NoteRequest, principal: Principal = Depends(current_principal)
) -> dict:
    with scoped_session(principal) as session:
        session.execute(
            text(
                """
                INSERT INTO teacher_notes (student_id, teacher_id, skill_id, body, override_mastery)
                VALUES (:sid, :tid, :skid, :body, :ov)
                """
            ),
            {
                "sid": student_id,
                "tid": principal.user_id,
                "skid": note.skill_id,
                "body": note.body,
                "ov": note.override_mastery,
            },
        )
    return {"status": "ok"}


@router.get("/classes")
def classes(principal: Principal = Depends(current_principal)) -> list[dict]:
    with scoped_session(principal) as session:
        rows = (
            session.execute(
                text(
                    "SELECT c.id::text AS class_id, c.name, "
                    "(SELECT count(*) FROM enrollments e WHERE e.class_id = c.id) AS student_count "
                    "FROM classes c WHERE c.teacher_id = :tid ORDER BY c.name"
                ),
                {"tid": principal.user_id},
            )
            .mappings()
            .all()
        )
    return [dict(r) for r in rows]


@router.get("/overview")
def overview(
    class_id: str | None = None, principal: Principal = Depends(current_principal)
) -> dict:
    """Composed teacher dashboard for one class. avg_mastery is min-cohort gated."""
    with scoped_session(principal) as session:
        if class_id:
            klass = session.execute(
                text("SELECT id::text AS id, name FROM classes "
                     "WHERE teacher_id = :tid AND id::text = :cid LIMIT 1"),
                {"tid": principal.user_id, "cid": class_id},
            ).mappings().first()
        else:
            klass = session.execute(
                text("SELECT id::text AS id, name FROM classes "
                     "WHERE teacher_id = :tid ORDER BY name LIMIT 1"),
                {"tid": principal.user_id},
            ).mappings().first()
        if not klass:
            return {"class_name": None, "kpis": {}, "attention": [], "activity": [], "roster": []}
        cid = klass["id"]
        agg = session.execute(
            text(
                "SELECT count(DISTINCT ls.student_id) AS n, avg(ls.mastery) AS avg "
                "FROM learner_state ls JOIN enrollments e ON e.student_id = ls.student_id "
                "WHERE e.class_id = :cid"
            ),
            {"cid": cid},
        ).mappings().one()
        roster = session.execute(
            text(
                "SELECT ls.student_id::text AS sid, round(avg(ls.mastery)::numeric, 3) AS avg_m, "
                "count(*) AS skills FROM learner_state ls JOIN enrollments e ON e.student_id = ls.student_id "
                "WHERE e.class_id = :cid GROUP BY ls.student_id ORDER BY avg_m DESC"
            ),
            {"cid": cid},
        ).mappings().all()
        attention = session.execute(
            text(
                "SELECT DISTINCT ON (ls.student_id) ls.student_id::text AS sid, sk.name AS topic, "
                "round(ls.mastery::numeric, 3) AS mastery FROM learner_state ls "
                "JOIN enrollments e ON e.student_id = ls.student_id JOIN skills sk ON sk.id = ls.skill_id "
                "WHERE e.class_id = :cid AND ls.mastery < 0.4 ORDER BY ls.student_id, ls.mastery ASC"
            ),
            {"cid": cid},
        ).mappings().all()

    n = int(agg["n"])
    avg_mastery: float | None
    try:
        enforce_min_cohort(n, {})  # gate the class average behind the privacy threshold
        avg_mastery = round(float(agg["avg"] or 0.0), 3)
    except CohortTooSmall:
        avg_mastery = None

    ids = list({r["sid"] for r in roster} | {a["sid"] for a in attention})
    names = _names_for(ids)
    attention_sorted = sorted(attention, key=lambda a: a["mastery"])[:5]
    return {
        "class_name": klass["name"],
        "kpis": {
            "active": n,
            "total": n,
            "avg_mastery": avg_mastery,
            "open_reviews": 0,  # no review-queue persistence yet (honest placeholder)
            "alerts": len(attention),
        },
        "attention": [
            {
                "student_id": a["sid"],
                "name": names.get(a["sid"], "?"),
                "initials": _initials(names.get(a["sid"], "?")),
                "topic": a["topic"],
                "mastery": float(a["mastery"]),
            }
            for a in attention_sorted
        ],
        "roster": [
            {
                "student_id": r["sid"],
                "name": names.get(r["sid"], "?"),
                "initials": _initials(names.get(r["sid"], "?")),
                "avg_mastery": float(r["avg_m"]),
                "skills": int(r["skills"]),
            }
            for r in roster
        ],
        "activity": [],  # event feed not tracked yet
    }


@router.get("/student/{student_id}/attempts")
def student_attempts(
    student_id: str, principal: Principal = Depends(current_principal)
) -> list[dict]:
    """Recent attempts timeline for a student (RLS: only own-class students are visible)."""
    with scoped_session(principal) as session:
        rows = (
            session.execute(
                text(
                    "SELECT a.item_ref, sk.name AS skill_name, a.is_correct, a.created_at "
                    "FROM attempts a JOIN skills sk ON sk.id = a.skill_id "
                    "WHERE a.student_id = :sid ORDER BY a.created_at DESC LIMIT 50"
                ),
                {"sid": student_id},
            )
            .mappings()
            .all()
        )
    return [
        {
            "item_ref": r["item_ref"],
            "skill_name": r["skill_name"],
            "is_correct": r["is_correct"],
            "created_at": str(r["created_at"]),
        }
        for r in rows
    ]
