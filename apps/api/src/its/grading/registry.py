"""Grader registry (GR-1): keyed on subject. The single Strategy/Adapter point (P7)."""

from its.grading.base import GraderStrategy

_REGISTRY: dict[str, GraderStrategy] = {}


def register(grader: GraderStrategy) -> None:
    _REGISTRY[grader.subject_key] = grader


def get_grader(subject_key: str) -> GraderStrategy:
    try:
        return _REGISTRY[subject_key]
    except KeyError as e:
        raise LookupError(f"no grader registered for subject '{subject_key}'") from e


def registered_subjects() -> list[str]:
    return sorted(_REGISTRY)
