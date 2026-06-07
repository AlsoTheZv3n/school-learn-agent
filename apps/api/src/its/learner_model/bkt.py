"""Bayesian Knowledge Tracing (LM-1): pure, tested functions.

Per skill, four probabilities (prior/learn/slip/guess). Interpretable (P5), works
with sparse data, needs no training corpus. These are pure functions with no DB or
side effects — the tracing service (tracing.py) applies them to learner_state.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class BKTParams:
    p_init: float = 0.2  # P(skill known a priori)
    p_learn: float = 0.15  # P(learning per opportunity)
    p_slip: float = 0.10  # P(wrong despite knowing)
    p_guess: float = 0.20  # P(right despite not knowing)


def posterior(p_known: float, correct: bool, p: BKTParams) -> float:
    """P(known | observation) via Bayes."""
    if correct:
        num = p_known * (1 - p.p_slip)
        den = num + (1 - p_known) * p.p_guess
    else:
        num = p_known * p.p_slip
        den = num + (1 - p_known) * (1 - p.p_guess)
    return num / den if den > 0 else p_known


def update(p_known: float, correct: bool, p: BKTParams) -> float:
    """One learning step: posterior, then the learn transition."""
    post = posterior(p_known, correct, p)
    return post + (1 - post) * p.p_learn


def mastery_after(sequence: list[bool], p: BKTParams) -> float:
    pk = p.p_init
    for correct in sequence:
        pk = update(pk, correct, p)
    return pk
