"""Hardening meta-tests: guard the safety invariants against future regressions.

A later migration accidentally disabling RLS, or granting the admin role a blanket
bypass, would silently re-open the leak surface. These tests fail loudly if so.
"""

from sqlalchemy import text

_RLS_TABLES = {"attempts", "learner_state", "teacher_notes", "enrollments"}


def test_rls_enabled_on_all_person_tables(engine) -> None:
    with engine.connect() as c:
        enabled = set(
            c.execute(
                text("SELECT relname FROM pg_class WHERE relrowsecurity AND relkind = 'r'")
            ).scalars().all()
        )
    missing = _RLS_TABLES - enabled
    assert not missing, f"RLS is not enabled on: {sorted(missing)}"


def test_admin_role_has_no_blanket_bypassrls(engine) -> None:
    with engine.connect() as c:
        bypass = c.execute(
            text("SELECT rolbypassrls FROM pg_roles WHERE rolname = 'its_admin'")
        ).scalar()
    assert bypass is False  # admin functions run through dedicated, audited paths


def test_person_tables_have_policies(engine) -> None:
    with engine.connect() as c:
        counts = dict(
            c.execute(
                text(
                    "SELECT tablename, count(*) FROM pg_policies "
                    "WHERE tablename = ANY(:t) GROUP BY tablename"
                ),
                {"t": list(_RLS_TABLES)},
            ).all()
        )
    for table in _RLS_TABLES:
        assert counts.get(table, 0) >= 1, f"{table} has RLS enabled but no policy (deny-all)"
