"""LLM client (AG-3, safety-critical). Scrubs PII before anything leaves the box (P4).

Backend is switchable via settings.llm_backend (local | frontier). The frontier path
is not wired yet — a real model (local Qwen2.5 or a frontier API with a DPA + a
no-training setting) is configured in a follow-up. The local path is a deterministic
stub so the explain path works end-to-end in development and tests.
"""

from its.config import settings
from its.llm.anonymize import scrub


def complete(system: str, user: str) -> str:
    user = scrub(user)  # P4: PII out before anything leaves the machine
    if settings.llm_backend == "frontier":
        return _complete_frontier(system, user)
    return _complete_local(system, user)


def _complete_local(system: str, user: str) -> str:
    # STUB (M3): no model wired yet. Deterministic, age-appropriate placeholder so the
    # generative path is exercisable. Replace with local Qwen2.5 inference in AG-3 follow-up.
    return f"Lass es uns anders angehen. {user}"


def _complete_frontier(system: str, user: str) -> str:
    if not settings.llm_api_key:
        raise RuntimeError("LLM_BACKEND=frontier requires LLM_API_KEY (and a DPA + no-training).")
    raise NotImplementedError("frontier backend wiring is an AG-3 follow-up (keep PII scrubbed).")
