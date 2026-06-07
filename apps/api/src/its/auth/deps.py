from dataclasses import dataclass

from fastapi import Header, HTTPException

from its.auth.roles import Role
from its.config import settings


@dataclass(frozen=True)
class Principal:
    user_id: str
    role: Role
    student_id: str | None = None  # gesetzt, wenn role == STUDENT


def _parse_dev_token(token: str) -> Principal:
    """DEV ONLY. Format: 'dev:<role>:<user_id>[:<student_id>]'."""
    parts = token.split(":")
    if len(parts) < 3:
        raise HTTPException(status_code=401, detail="invalid dev token")
    try:
        role = Role(parts[1])
    except ValueError as e:
        raise HTTPException(status_code=401, detail="invalid dev role") from e
    student_id = parts[3] if len(parts) > 3 and parts[3] else None
    return Principal(user_id=parts[2], role=role, student_id=student_id)


def current_principal(authorization: str | None = Header(default=None)) -> Principal:
    """FastAPI-Dependency: liefert das authentifizierte Principal.

    TODO (FND-5): echtes JWT-Decoding gegen settings.jwt_public_key implementieren.
    Bis dahin ein bewusster Stub. Für lokales Testen kann AUTH_DEV_MODE=1 gesetzt
    werden — dann werden 'dev:<role>:<user_id>[:<student_id>]'-Tokens akzeptiert.
    Das ist ausschliesslich Entwicklungs-Hilfe und MUSS vor Produktion entfernt/ersetzt
    werden (siehe docs/security-audit.md §Gates).
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="missing auth")
    token = authorization.removeprefix("Bearer ").strip()
    if settings.auth_dev_mode and token.startswith("dev:"):
        return _parse_dev_token(token)
    raise NotImplementedError("JWT decoding to be implemented in FND-5")
