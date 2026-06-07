import pytest
from fastapi import HTTPException

from its.auth.deps import current_principal
from its.auth.roles import PG_ROLE, Role


def test_missing_auth_raises_401() -> None:
    with pytest.raises(HTTPException) as exc:
        current_principal(authorization=None)
    assert exc.value.status_code == 401


def test_stub_not_implemented_when_token_present() -> None:
    # Documents the FND-5 contract: a present token currently hits the JWT stub.
    with pytest.raises(NotImplementedError):
        current_principal(authorization="Bearer dummy")


def test_pg_role_mapping_matches_rls_roles() -> None:
    assert PG_ROLE[Role.STUDENT] == "its_student"
    assert PG_ROLE[Role.TEACHER] == "its_teacher"
    assert PG_ROLE[Role.ADMIN] == "its_admin"
