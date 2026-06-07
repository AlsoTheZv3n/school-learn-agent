from dataclasses import dataclass

from fastapi import Header, HTTPException

from its.auth.roles import Role


@dataclass(frozen=True)
class Principal:
    user_id: str
    role: Role
    student_id: str | None = None  # gesetzt, wenn role == STUDENT


def current_principal(authorization: str | None = Header(default=None)) -> Principal:
    """FastAPI-Dependency: liefert das authentifizierte Principal.

    TODO (FND-5): echtes JWT-Decoding gegen settings.jwt_public_key implementieren.
    Vorerst ein bewusster Stub für die lokale Entwicklung — MUSS vor Produktion
    ersetzt werden. Das Claims-Mapping (welcher Claim trägt role / student_id) und
    die IdP-Wahl sind offen, siehe docs/planning/open-questions-and-risks.md (E1).
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="missing auth")
    raise NotImplementedError("JWT decoding to be implemented in FND-5")
