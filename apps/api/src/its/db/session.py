"""Engine + role-aware session. This is the bridge to RLS (docs/04-safety.md).

Per request we switch the Postgres role and set the student/teacher context the
RLS policies read. Fail-closed: a student principal without a student_id raises.

Implementation note: PostgreSQL's `SET ROLE` / `SET <var>` do NOT accept bind
parameters, so we use the `set_config(name, value, is_local)` function with
is_local=true. Transaction-local config auto-clears on COMMIT/ROLLBACK, so a
pooled connection never carries another request's scope (defense in depth).
"""

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from its.auth.deps import Principal
from its.auth.roles import PG_ROLE, Role
from its.config import settings

engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)

_SET_CONFIG = text("SELECT set_config(:k, :v, true)")


@contextmanager
def scoped_session(principal: Principal) -> Iterator[Session]:
    """Open a session, switch role and set per-request scope (transaction-local).

    The variables `app.current_student_id` / `app.current_teacher_id` are read by
    the RLS policies in safety/rls.sql. Without them the policies match no rows
    (fail-closed).
    """
    session = SessionLocal()
    try:
        pg_role = PG_ROLE[principal.role]
        # transaction-local role + scope; cleared automatically on commit/rollback
        session.execute(_SET_CONFIG, {"k": "role", "v": pg_role})

        if principal.role == Role.STUDENT:
            if not principal.student_id:
                raise PermissionError("student principal without student_id (fail-closed)")
            session.execute(
                _SET_CONFIG, {"k": "app.current_student_id", "v": str(principal.student_id)}
            )
        elif principal.role == Role.TEACHER:
            session.execute(
                _SET_CONFIG, {"k": "app.current_teacher_id", "v": str(principal.user_id)}
            )

        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
