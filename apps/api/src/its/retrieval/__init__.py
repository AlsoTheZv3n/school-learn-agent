"""Three retrieval modes out of one database, behind a router:

- semantic: pgvector similarity over shared study material (no person scope).
- individual: exactly one student_id, fail-closed scope + RLS (safety-critical).
- population: GROUP BY aggregates, only ever via the min-cohort gate (safety-critical).

Plus graph traversal (recursive CTE over skill_edges). The router's decision is
logged so routing stays auditable (P6).
"""
