"""Unit tests for BKT (LM-1) — pure functions, no DB."""

from its.learner_model.bkt import BKTParams, mastery_after, posterior, update


def test_posterior_in_range() -> None:
    p = BKTParams()
    assert 0.0 <= posterior(0.3, True, p) <= 1.0
    assert 0.0 <= posterior(0.3, False, p) <= 1.0


def test_correct_raises_posterior_more_than_wrong() -> None:
    p = BKTParams()
    assert posterior(0.3, True, p) > posterior(0.3, False, p)


def test_correct_increases_mastery() -> None:
    p = BKTParams()
    assert mastery_after([True, True, True], p) > mastery_after([True], p)


def test_wrong_does_not_exceed_correct() -> None:
    p = BKTParams()
    assert mastery_after([False, False], p) < mastery_after([True, True], p)


def test_update_stays_in_unit_interval() -> None:
    p = BKTParams()
    pk = p.p_init
    for correct in [True, False, True, True, False]:
        pk = update(pk, correct, p)
        assert 0.0 <= pk <= 1.0
