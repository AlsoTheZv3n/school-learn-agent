"""The pedagogical agent as a LangGraph state machine.

route -> retrieve -> (assess -> update_model | explain) -> END. assess uses the
curated grader (P2); update_model writes through the tracing service so the learner
model updates, not the agent (P3); explain is the generative, error-tolerant path.
"""
