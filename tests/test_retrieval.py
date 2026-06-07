"""Retrieval tests (RET-1..5) + ingestion (CON-2): router, graph, population,
individual, semantic. DB tests run against real Postgres (engine fixture)."""

from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker

from its.auth.deps import Principal
from its.auth.roles import Role
from its.content.ingest import ingest_vault
from its.retrieval.graph import prerequisites
from its.retrieval.individual import mastery_overview
from its.retrieval.population import skill_mastery_distribution
from its.retrieval.router import Mode, route
from its.retrieval.semantic import semantic_search_text
from its.safety.cohort import CohortTooSmall
from its.safety.scoping import ScopeError, require_student_scope

VAULT = Path(__file__).parents[1] / "content" / "math"


# ── RET-1 router (no DB) ──────────────────────────────────────────────────────
def test_route_population_on_aggregate_cue() -> None:
    d = route("Wie steht die Klasse im Durchschnitt?", has_student_scope=False)
    assert d.mode == Mode.POPULATION
    assert d.reason


def test_route_individual_only_with_scope() -> None:
    assert route("Wo stehe ich gerade?", has_student_scope=True).mode == Mode.INDIVIDUAL
    # personal cue but no scope -> falls back to semantic (fail-safe)
    assert route("Wo stehe ich gerade?", has_student_scope=False).mode == Mode.SEMANTIC


def test_route_semantic_default_and_escalation() -> None:
    d = route("Was bedeutet quadratische Ergaenzung genau?", has_student_scope=True)
    assert d.mode == Mode.SEMANTIC
    assert d.escalate_to_query is True  # "genau" -> wants a precise number


# ── RET-5 graph (uses the 0003 demo skill seed) ───────────────────────────────
def test_prerequisites_chain(engine) -> None:
    with engine.connect() as c:
        qf = c.execute(text("SELECT id FROM skills WHERE key='quadratic-formula'")).scalar()
        deps = prerequisites(c, str(qf))
    depths = {d["depth"] for d in deps}
    assert len(deps) >= 2  # complete-the-square (depth 1) + linear-equations (depth 2)
    assert 1 in depths and 2 in depths


# ── RET-4 population (uses seeded_rls; n=1 < k) ───────────────────────────────
def test_population_refuses_small_cohort(engine, seeded_rls) -> None:
    with engine.connect() as c, pytest.raises(CohortTooSmall):
        skill_mastery_distribution(c, str(seeded_rls["klass"]), str(seeded_rls["skill"]))


# ── RET-3 individual (scoped) ─────────────────────────────────────────────────
def test_mastery_overview_scoped_to_student(as_role, seeded_rls) -> None:
    a = seeded_rls["a"]
    principal = Principal(user_id=str(a), role=Role.STUDENT, student_id=str(a))
    with as_role("its_student", student_id=a) as c:
        rows = mastery_overview(c, principal)
    assert len(rows) >= 1
    assert all("mastery" in r for r in rows)


def test_individual_fail_closed_for_non_student() -> None:
    with pytest.raises(ScopeError):
        require_student_scope(Principal(user_id="t", role=Role.TEACHER))


# ── RET-2 semantic (after CON-2 ingest of the demo vault) ─────────────────────
@pytest.fixture
def ingested(engine):
    session_factory = sessionmaker(bind=engine)
    s = session_factory()
    try:
        n = ingest_vault(s, VAULT)
        s.commit()
        assert n >= 1
    finally:
        s.close()
    yield
    with engine.begin() as c:
        c.execute(text("DELETE FROM content_notes WHERE source_path LIKE '%quadratic-equations%'"))
        c.execute(text("DELETE FROM skill_edges WHERE kind = 'related'"))


def test_semantic_search_returns_prose_chunk(engine, ingested) -> None:
    with engine.connect() as c:
        results = semantic_search_text(c, "quadratische Ergaenzung erklaeren", k=3)
    assert len(results) >= 1
    assert any("quadrat" in r["chunk"].lower() for r in results)
    # the embedded prose must NOT contain the sidecar SQL (it is kept separate)
    assert all("SELECT" not in r["chunk"] for r in results)
