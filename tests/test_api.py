"""HTTP tests for the API (API-1..3) against the test DB.

Auth is still a stub (FND-5), so tests inject the principal via FastAPI's
dependency_overrides. Proves: a student sees only themselves and never uncertainty;
a teacher sees only their own class; a small cohort is refused with 403.
"""

from fastapi.testclient import TestClient

from its.auth.deps import Principal, current_principal
from its.auth.roles import Role
from its.main import create_app


def _client(principal: Principal) -> TestClient:
    app = create_app()
    app.dependency_overrides[current_principal] = lambda: principal
    return TestClient(app)


def _student(sid) -> Principal:
    return Principal(user_id=str(sid), role=Role.STUDENT, student_id=str(sid))


def _teacher(tid) -> Principal:
    return Principal(user_id=str(tid), role=Role.TEACHER)


def test_student_turn_grades_and_updates(seeded_rls) -> None:
    c = _client(_student(seeded_rls["a"]))
    r = c.post(
        "/student/turn",
        json={
            "subject_key": "math",
            "skill_key": "complete-the-square",
            "intent": "answer",
            "answer": "x^2 + 2*x + 1",
            "item_ref": "expand-x-plus-1-squared",
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["grade"]["confidence"] == 1.0
    assert body["grade"]["correct"] is True
    assert body["mastery"] is not None


def test_student_mastery_hides_uncertainty(seeded_rls) -> None:
    c = _client(_student(seeded_rls["a"]))
    r = c.get("/student/mastery")
    assert r.status_code == 200
    items = r.json()
    assert len(items) >= 1
    assert all("uncertainty" not in it for it in items)  # P5: never exposed to the student


def test_teacher_sees_own_class_student_with_uncertainty(seeded_rls) -> None:
    c = _client(_teacher(seeded_rls["teacher"]))
    r = c.get(f"/teacher/student/{seeded_rls['a']}/mastery")
    assert r.status_code == 200
    items = r.json()
    assert len(items) >= 1
    assert "uncertainty" in items[0]  # open learner model


def test_teacher_cannot_see_outsider(seeded_rls) -> None:
    c = _client(_teacher(seeded_rls["teacher"]))
    r = c.get(f"/teacher/student/{seeded_rls['b']}/mastery")
    assert r.status_code == 200
    assert r.json() == []  # B is not in the teacher's class -> RLS hides everything


def test_small_cohort_distribution_is_403(seeded_rls) -> None:
    c = _client(_teacher(seeded_rls["teacher"]))
    r = c.get(
        f"/teacher/class/{seeded_rls['klass']}/skill/{seeded_rls['skill']}/distribution"
    )
    assert r.status_code == 403


def test_teacher_note_written(seeded_rls) -> None:
    c = _client(_teacher(seeded_rls["teacher"]))
    r = c.post(
        f"/teacher/student/{seeded_rls['a']}/note",
        json={"body": "Gut gemacht!", "skill_id": str(seeded_rls["skill"])},
    )
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_content_items_never_expose_answer_key(seeded_rls) -> None:
    c = _client(_student(seeded_rls["a"]))
    r = c.get("/content/items")
    assert r.status_code == 200
    items = r.json()
    assert len(items) >= 1
    assert all("answer_key" not in it for it in items)  # P2: the key never leaves the server
    assert all({"item_ref", "prompt", "skill_key"} <= set(it) for it in items)


def test_student_overview_shape_no_uncertainty(seeded_rls) -> None:
    c = _client(_student(seeded_rls["a"]))
    r = c.get("/student/overview")
    assert r.status_code == 200
    body = r.json()
    assert {"subjects", "current", "recommendations", "note"} <= set(body)
    for s in body["subjects"]:
        assert "uncertainty" not in s  # gentle view (P5)


def test_teacher_overview_resolves_own_class(seeded_rls) -> None:
    c = _client(_teacher(seeded_rls["teacher"]))
    r = c.get(f"/teacher/overview?class_id={seeded_rls['klass']}")
    assert r.status_code == 200
    body = r.json()
    assert body["class_name"] == "C"
    # roster/attention names were resolved (RLS authorized the ids first)
    assert all(m["name"] != "?" for m in body["roster"])


def test_teacher_attempts_outsider_is_empty(seeded_rls) -> None:
    c = _client(_teacher(seeded_rls["teacher"]))
    own = c.get(f"/teacher/student/{seeded_rls['a']}/attempts")
    outsider = c.get(f"/teacher/student/{seeded_rls['b']}/attempts")
    assert own.status_code == 200 and len(own.json()) >= 1
    assert outsider.status_code == 200 and outsider.json() == []  # B not in class -> RLS hides
