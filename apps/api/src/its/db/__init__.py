"""Database layer: ORM models, engine/session, migrations.

The role-aware `scoped_session` (session.py) is the bridge to Row-Level Security
(see docs/04-safety.md): it switches the Postgres role and sets the per-request
student/teacher context the RLS policies read.
"""
