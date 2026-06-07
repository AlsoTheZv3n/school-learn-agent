"""Min-cohort threshold (SAF-3). Guards against de-anonymization via aggregates.

Every population/aggregate query MUST pass through enforce_min_cohort before its
result leaves the system. A "class average" over a group that happens to contain
one student is a de-anonymized individual disclosure — so groups smaller than k
are refused (default k=10, from settings).
"""

from dataclasses import dataclass

from its.config import settings


class CohortTooSmall(PermissionError):
    pass


@dataclass(frozen=True)
class CohortResult:
    n: int
    payload: dict


def enforce_min_cohort(n: int, payload: dict, k: int | None = None) -> CohortResult:
    """Refuse aggregates whose group is smaller than k (default settings.min_cohort_k)."""
    threshold = k if k is not None else settings.min_cohort_k
    if n < threshold:
        raise CohortTooSmall(f"cohort n={n} below threshold k={threshold}")
    return CohortResult(n=n, payload=payload)
