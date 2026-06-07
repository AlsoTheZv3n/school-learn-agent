## Ziel

Ein kleiner, **idempotenter** Demo-Skill-Graph für das Fach **Mathematik**: das Fach `math`, ein paar Skills und die zugehörigen `skill_edges` (Voraussetzungskanten). So ist nach der Migration ein lauffähiger Graph vorhanden, an dem Retrieval-Graph-Traversal (RET-5) und das Lernmodell demonstriert werden können — ohne echte Personendaten.

## Kontext & Prinzipien

- **P1 (Schema in versionierten Migrationen):** Stammdaten (Fach/Skills/Kanten) gehören in eine versionierte Daten-Migration, damit sie reproduzierbar mit dem Schema wandern.
- **P4 (PII-Minimierung):** Dieser Seed legt **keine** Personendaten an — nur Stammdaten. Mock-Schüler:innen und Lernkurven kommen separat über den Seeder (docs/11, E13), nie vermischt.
- **P3 (Learner-Modell):** Der Skill-Graph ist die Domäne, gegen die später Mastery pro Skill getract wird; ein sauberer Prerequisite-Graph ist Voraussetzung für sinnvolle Nächster-Schritt-Wahl.

## Zu erstellende/aendernde Dateien

- `apps/api/migrations/versions/0002_seed_math_skills.py` — Daten-Migration mit `down_revision = "0001_core_schema"`.

> Hinweis: zu entscheiden — DB-4 als **Daten-Migration** (empfohlen für Stammdaten, idempotent, mit `downgrade`) **oder** als separates idempotentes Seed-Skript. `docs/03` §6 spricht von „Daten-Migration/Seed". Empfehlung: Migration, damit der Demo-Graph ohne Zusatzschritt nach `upgrade head` existiert. Personendaten bleiben dem Seeder (docs/11) vorbehalten.

## Schnittstellen & Signaturen

Referenz aus `docs/03-database.md` §6:

> **DB-4:** Daten-Migration/Seed legt Fach `math`, ein paar Skills und `skill_edges` an (z. B. `linear-equations → complete-the-square → quadratic-formula`). Klein halten; echte Mengen kommen über den Seeder (docs/11).

Relevante Tabellenstruktur (aus DB-1):

```sql
subjects(id, key UNIQUE, name)
skills(id, subject_id, key, name, grade_level, UNIQUE(subject_id, key))
skill_edges(from_skill, to_skill, kind DEFAULT 'prerequisite', PRIMARY KEY(from_skill, to_skill, kind))
```

Migrationsskizze (idempotent via `ON CONFLICT`):

```python
# 0002_seed_math_skills.py (Auszug)
from alembic import op
import sqlalchemy as sa

def upgrade() -> None:
    conn = op.get_bind()
    # Fach (idempotent)
    conn.execute(sa.text(
        "INSERT INTO subjects (key, name) VALUES ('math', 'Mathematik') "
        "ON CONFLICT (key) DO NOTHING"
    ))
    subj = conn.execute(sa.text("SELECT id FROM subjects WHERE key='math'")).scalar()
    skills = [
        ("linear-equations",    "Lineare Gleichungen",      8),
        ("complete-the-square", "Quadratische Ergänzung",   9),
        ("quadratic-formula",   "Quadratische Formel",      9),
    ]
    for key, name, grade in skills:
        conn.execute(sa.text(
            "INSERT INTO skills (subject_id, key, name, grade_level) "
            "VALUES (:s, :k, :n, :g) ON CONFLICT (subject_id, key) DO NOTHING"
        ), {"s": subj, "k": key, "n": name, "g": grade})
    def sid(k):
        return conn.execute(sa.text(
            "SELECT id FROM skills WHERE subject_id=:s AND key=:k"
        ), {"s": subj, "k": k}).scalar()
    edges = [("linear-equations", "complete-the-square"),
             ("complete-the-square", "quadratic-formula")]
    for frm, to in edges:
        conn.execute(sa.text(
            "INSERT INTO skill_edges (from_skill, to_skill, kind) "
            "VALUES (:f, :t, 'prerequisite') "
            "ON CONFLICT (from_skill, to_skill, kind) DO NOTHING"
        ), {"f": sid(frm), "t": sid(to)})

def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text(
        "DELETE FROM skill_edges WHERE from_skill IN "
        "(SELECT id FROM skills WHERE subject_id=(SELECT id FROM subjects WHERE key='math'))"
    ))
    conn.execute(sa.text(
        "DELETE FROM skills WHERE subject_id=(SELECT id FROM subjects WHERE key='math')"
    ))
    conn.execute(sa.text("DELETE FROM subjects WHERE key='math'"))
```

## Umsetzungsschritte

- [ ] Daten-Migration `0002_seed_math_skills` mit `down_revision = "0001_core_schema"` anlegen.
- [ ] Fach `math` (`name='Mathematik'`) idempotent einfügen (`ON CONFLICT (key) DO NOTHING`).
- [ ] Skills `linear-equations`, `complete-the-square`, `quadratic-formula` mit `grade_level` idempotent einfügen (`ON CONFLICT (subject_id, key) DO NOTHING`).
- [ ] Prerequisite-Kanten `linear-equations → complete-the-square` und `complete-the-square → quadratic-formula` mit `kind='prerequisite'` idempotent einfügen.
- [ ] `downgrade()` entfernt genau diese Seed-Zeilen (Kanten vor Skills vor Subject).
- [ ] Klein halten — keine Personendaten, keine `attempts`/`learner_state` (das ist E13).

## Akzeptanzkriterien

- [ ] Nach `upgrade head` existiert das Fach `math`.
- [ ] Drei Mathe-Skills (`linear-equations`, `complete-the-square`, `quadratic-formula`) sind vorhanden.
- [ ] Zwei Prerequisite-Kanten bilden den Pfad `linear-equations → complete-the-square → quadratic-formula`.
- [ ] Die Migration ist idempotent (erneutes Ausführen erzeugt keine Duplikate/Fehler); `downgrade` entfernt den Seed restlos.
- [ ] Es werden **keine** Personendaten angelegt.

## Tests / Verifikation

```bash
cd apps/api
uv run alembic upgrade head

# Fach + Skills + Kanten vorhanden:
uv run python -c "
from sqlalchemy import create_engine, text
from its.config import settings
e=create_engine(settings.database_url)
with e.connect() as c:
    print('subject:', c.execute(text(\"select name from subjects where key='math'\")).scalar())
    print('skills:', [r[0] for r in c.execute(text(\"select key from skills order by grade_level, key\"))])
    print('edges:', c.execute(text(\"select count(*) from skill_edges\")).scalar())
"
# Erwartung: subject: Mathematik | skills: [...3 keys...] | edges: 2

# Graph-Pfad via rekursiver CTE (Vorschau auf RET-5):
uv run python -c "
from sqlalchemy import create_engine, text
from its.config import settings
e=create_engine(settings.database_url)
q=text('''
WITH RECURSIVE path AS (
  SELECT from_skill, to_skill, 1 AS depth FROM skill_edges
  WHERE from_skill=(SELECT id FROM skills WHERE key='linear-equations')
  UNION ALL
  SELECT e.from_skill, e.to_skill, p.depth+1
  FROM skill_edges e JOIN path p ON e.from_skill=p.to_skill
)
SELECT depth FROM path ORDER BY depth''')
with e.connect() as c:
    print('max-depth:', max(r[0] for r in c.execute(q)))
"
# Erwartung: max-depth: 2
```

## Abhaengigkeiten

- **DB-1** (Voraussetzung): liefert die Tabellen `subjects`, `skills`, `skill_edges`, in die der Seed schreibt.
- (Empfohlen) **DB-2**: erleichtert das Schreiben des Seeds über ORM-Modelle, falls als Skript statt roher SQL-Migration umgesetzt.
- **Nachgelagert:** **RET-5 (Graph-Traversal)** und das **Lernmodell/Agent**-Demo nutzen diesen Graphen; der vollständige **Seeder (E13/MOCK-1)** legt darauf aufbauend Mock-Personen + Lernkurven an.

## Definition of Done

- [ ] Akzeptanzkriterium aus `docs/03` §7 (DB-4: „Demo-Skill-Graph vorhanden") erfüllt.
- [ ] Verifikation grün: Fach/Skills/Kanten vorhanden, rekursive CTE liefert den erwarteten Pfad; Migration idempotent.
- [ ] `uv`-only — keine `pip`-Aufrufe.
- [ ] Keine PII/Personendaten angelegt (P4); Trennung zum Mock-Seeder (docs/11) eingehalten.
- [ ] GitHub-Issue DB-4 geschlossen, E2-Epic-Checkliste aktualisiert.
