"""Deep Knowledge Tracing placeholder (LM-3).

Interface-compatible stub. Activate ONLY once there is enough interaction history
AND BKT is measurably limiting (P2/P5) — a neural (LSTM) model is a data-driven swap
for bkt.update, not a default. Until then this raises to prevent accidental use.
"""

from its.learner_model.bkt import BKTParams


def update(p_known: float, correct: bool, params: BKTParams | None = None) -> float:
    """Interface-compatible with bkt.update. Not implemented on purpose."""
    raise NotImplementedError(
        "DKT is a deliberate later swap; activate only with sufficient interaction "
        "history and a measured BKT limitation. Use learner_model.bkt for now."
    )
