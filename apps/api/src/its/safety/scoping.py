"""Scoping resolver (SAF-2). Fail-closed: no individual query without a scope.

This is the application-side complement to RLS: even before a query is built, an
individual lookup must resolve to exactly one student_id, or it raises. RLS is the
second, independent line of defense (a missing filter still returns no foreign rows).
"""

from its.auth.deps import Principal
from its.auth.roles import Role


class ScopeError(PermissionError):
    pass


def require_student_scope(principal: Principal) -> str:
    """Return the student_id an individual query MUST be scoped to.

    Fail-closed: no scope -> ScopeError, never 'all students'.
    """
    if principal.role == Role.STUDENT:
        if not principal.student_id:
            raise ScopeError("student without student_id")
        return principal.student_id
    raise ScopeError("individual query requires a student-scoped principal")


def teacher_id_of(principal: Principal) -> str:
    if principal.role != Role.TEACHER:
        raise ScopeError("not a teacher principal")
    return principal.user_id
