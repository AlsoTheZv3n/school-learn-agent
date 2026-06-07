"""SAF-4 — min-cohort threshold proof (CI-blocking).

A pure-logic test: aggregates over a group smaller than k are refused; a
sufficiently large group passes its payload through unchanged.
"""

import pytest

from its.safety.cohort import CohortResult, CohortTooSmall, enforce_min_cohort


def test_small_cohort_refused() -> None:
    with pytest.raises(CohortTooSmall):
        enforce_min_cohort(n=3, payload={"avg": 0.7}, k=10)


def test_cohort_at_threshold_passes() -> None:
    res = enforce_min_cohort(n=10, payload={"avg": 0.5}, k=10)
    assert isinstance(res, CohortResult)
    assert res.n == 10


def test_sufficient_cohort_ok() -> None:
    res = enforce_min_cohort(n=25, payload={"avg": 0.7}, k=10)
    assert res.n == 25
    assert res.payload["avg"] == 0.7


def test_default_threshold_from_settings() -> None:
    # Default k comes from settings.min_cohort_k (10); n=9 must be refused.
    with pytest.raises(CohortTooSmall):
        enforce_min_cohort(n=9, payload={"avg": 0.4})
