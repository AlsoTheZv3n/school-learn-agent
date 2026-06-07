"""The isolation gate (build first, M1).

- rls.sql: Postgres Row-Level Security — a student sees only their own rows;
  a teacher only rows of students in their classes. Enforced by the database,
  not by application `if` checks (P1).
- scoping.py: fail-closed resolver — no individual query runs without a scope.
- cohort.py: min-cohort threshold — aggregates over groups smaller than k are refused.
"""
