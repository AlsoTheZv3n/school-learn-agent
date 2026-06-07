"""E2E HTTP smoke (TST-4): one flow across student + teacher over the same data.

Student answers -> sees their mastery (no uncertainty) -> teacher views the SAME
student's state (with uncertainty), consistent values. The browser/Playwright variant
is deferred (needs a running frontend); this HTTP smoke is the fast, CI-friendly gate.
"""

from fastapi.testclient import TestClient

from its.auth.deps import Principal, current_principal
from its.auth.roles import Role
from its.main import create_app


def _client(principal: Principal) -> TestClient:
    app = create_app()
    app.dependency_overrides[current_principal] = lambda: principal
    return TestClient(app)


def test_smoke_student_answers_then_teacher_sees_state(seeded_rls) -> None:
    student_id, teacher_id = seeded_rls["a"], seeded_rls["teacher"]

    # 1) Student answers a question (curated grading + model update).
    student = _client(Principal(user_id=str(student_id), role=Role.STUDENT, student_id=str(student_id)))
    turn = student.post(
        "/student/turn",
        json={
            "subject_key": "math",
            "skill_key": "complete-the-square",
            "intent": "answer",
            "answer": "x^2 + 2*x + 1",
            "item_ref": "expand-x-plus-1-squared",
        },
    )
    assert turn.status_code == 200
    assert turn.json()["grade"]["correct"] is True

    # 2) Student sees their mastery — gentle view, never uncertainty (P5).
    mine = student.get("/student/mastery")
    assert mine.status_code == 200
    student_rows = mine.json()
    assert len(student_rows) >= 1
    assert all("uncertainty" not in r for r in student_rows)

    # 3) Teacher views the SAME student's state — with uncertainty (open learner model).
    teacher = _client(Principal(user_id=str(teacher_id), role=Role.TEACHER))
    seen = teacher.get(f"/teacher/student/{student_id}/mastery")
    assert seen.status_code == 200
    teacher_rows = seen.json()
    assert len(teacher_rows) >= 1
    assert "uncertainty" in teacher_rows[0]

    # 4) Consistency: the mastery the student sees matches what the teacher sees.
    student_by_skill = {r["skill_id"]: round(r["mastery"], 6) for r in student_rows}
    for r in teacher_rows:
        if r["skill_id"] in student_by_skill:
            assert round(r["mastery"], 6) == student_by_skill[r["skill_id"]]
