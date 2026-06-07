from enum import StrEnum


class Role(StrEnum):
    STUDENT = "student"
    TEACHER = "teacher"
    ADMIN = "admin"


# Mapping App-Rolle -> Postgres-Rolle (für RLS, siehe docs/04-safety.md).
# Diese Postgres-Rollennamen sind exakt die, auf die die RLS-Policies keyen.
PG_ROLE: dict[Role, str] = {
    Role.STUDENT: "its_student",
    Role.TEACHER: "its_teacher",
    Role.ADMIN: "its_admin",
}
