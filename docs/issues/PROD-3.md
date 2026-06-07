## Ziel

Datenresidenz, Retention und Löschung für ein System mit Daten Minderjähriger sind dokumentiert und konfiguriert: DB und (falls extern genutzte) LLM-Inferenz liegen in einer CH/EU-Region, es gibt ein definiertes Aufbewahrungs-/Löschkonzept pro Datenkategorie, und bei externer LLM-Nutzung ist ein AVV/DPA mit No-Training-Setting Voraussetzung. Rechtliche Angaben sind explizit als gegen aktuelle Quellen zu prüfen markiert.

## Kontext & Prinzipien

- **P8 (CH/EU-Residenz):** Kernprinzip dieses Tasks. Schülerdaten Minderjähriger erfordern CH/EU-Residenz (revDSG/DSGVO). Prototyp-Hosting (Railway o. Ä.) ist nicht für Echtdaten. Dieser Task ist `priority:critical`.
- **P4 (PII raus / Anonymisierung):** Bei externer LLM-Nutzung verlässt PII die Maschine nicht im Klartext (`scrub` in `llm/anonymize.py`); zusätzlich braucht es AVV + No-Training. Für Echtdaten ist das lokale Modell (`LLM_BACKEND=local`) der sichere Default.
- **P1/Schema:** Der Löschpfad nutzt das bereits im Schema vorhandene `ON DELETE CASCADE` statt eines fehleranfälligen manuellen Sweeps.

## Zu erstellende/ändernde Dateien

- `docs/compliance.md` (neu) — Residenz/Retention/Löschung/AVV + Disclaimer. (Alternativ `infra/COMPLIANCE.md`; Pfad gemäss Repo-Layout-Konvention.)
- `infra/` (bestehend) — Deploy-Konfiguration hält die CH/EU-Region fest (z. B. docker-compose/Deploy-Manifest-Kommentar oder Region-Variable).
- `.env.example` (bestehend) — `LLM_BACKEND=local` als Default für Echtdaten dokumentiert.
- optional `scripts/delete_student.py` (neu) — ausführbarer Löschpfad pro Schüler:in (siehe Hinweis).

## Schnittstellen & Signaturen

LLM-Client mit Backend-Umschaltung und Scrub vor externem Call (docs/07), den die AVV-Anforderung absichert:

```python
# apps/api/src/its/llm/client.py
from its.config import settings
from its.llm.anonymize import scrub

def complete(system: str, user: str) -> str:
    user = scrub(user)               # P4: PII raus, bevor etwas die Maschine verlaesst
    if settings.llm_backend == "frontier":
        return _complete_frontier(system, user)   # API-Call; user ist bereits gescrubbt
    return _complete_local(system, user)           # lokales Modell (Qwen2.5 o. AE.)
```

Schema-Eigenschaft, auf der der Löschpfad beruht — `ON DELETE CASCADE` auf den schülerbezogenen FKs (docs/03):

```sql
CREATE TABLE enrollments (
  student_id uuid REFERENCES students(id) ON DELETE CASCADE,
  class_id   uuid REFERENCES classes(id)  ON DELETE CASCADE,
  PRIMARY KEY (student_id, class_id)
);
CREATE TABLE attempts (
  ... student_id uuid NOT NULL REFERENCES students(id) ON DELETE CASCADE, ...
);
CREATE TABLE learner_state (
  student_id uuid NOT NULL REFERENCES students(id) ON DELETE CASCADE, ...
);
CREATE TABLE teacher_notes (
  ... student_id uuid NOT NULL REFERENCES students(id) ON DELETE CASCADE, ...
);
```

Löschpfad pro Schüler:in (nutzt CASCADE, ein einziger DELETE):

```sql
-- loescht Schueler:in und kaskadiert auf enrollments, attempts, learner_state, teacher_notes
DELETE FROM students WHERE id = :student_id;
```

Relevante Env-Variablen (docs/02 §3):

```dotenv
LLM_BACKEND=local       # local | frontier  (Echtdaten-Default: local)
LLM_API_KEY=
```

## Umsetzungsschritte

- [ ] `docs/compliance.md` anlegen mit Abschnitt **Residenz**: DB und (externe) LLM-Inferenz in CH/EU-Region (z. B. Azure Switzerland, Exoscale, Infomaniak); Railway o. Ä. explizit als nicht für Echtdaten markieren.
- [ ] Abschnitt **PII-Minimierung**: Verweis auf das PII-minimale Schema (docs/03) und den anonymisierten LLM-Pfad (P4, `scrub`).
- [ ] Abschnitt **Retention/Löschung**: Tabelle mit Aufbewahrungsfenster pro Datenkategorie (attempts, learner_state, teacher_notes, students/PII, content) — Fristen markieren, wo noch zu entscheiden.
- [ ] Löschpfad pro Schüler:in dokumentieren (`DELETE FROM students WHERE id=...`) und die CASCADE-Wirkung erläutern.
- [ ] Abschnitt **Auftragsverarbeitung**: bei externer LLM-API ist AVV/DPA + No-Training-Setting Pflicht; sonst lokales Modell. `LLM_BACKEND=local` als Echtdaten-Default festhalten.
- [ ] CH/EU-Region in der Deploy-Konfiguration (`infra/`) festhalten.
- [ ] Rechtlichen Disclaimer aufnehmen: revDSG/DSGVO und kantonale/schulische Vorgaben ändern sich; Angaben sind Architektur-Leitplanken, kein Rechtsrat; vor Produktivbetrieb fachliche/rechtliche Prüfung einholen.
- [ ] Optional: `scripts/delete_student.py` als ausführbaren, geguardeten Löschpfad (siehe Hinweis).

> Hinweis: zu entscheiden — (a) konkrete Aufbewahrungsfristen pro Kategorie (Zahlenwerte) fehlen im Plan; (b) ob Löschung nur als dokumentierter SQL-Pfad oder als ausführbares CLI bereitsteht; (c) konkrete CH/EU-Provider-Wahl. Diese Punkte sind im Body als offen markiert statt erfunden.

## Akzeptanzkriterien

- [ ] Residenz (CH/EU) ist dokumentiert **und** in der Deploy-Konfiguration festgehalten.
- [ ] Retention-/Löschkonzept pro Datenkategorie ist dokumentiert; Löschpfad pro Schüler:in (über CASCADE) ist beschrieben.
- [ ] AVV-Anforderung bei externer LLM-Nutzung (inkl. No-Training) ist dokumentiert; `LLM_BACKEND=local` als Echtdaten-Default.
- [ ] Rechtliche Angaben sind ausdrücklich als gegen aktuelle Quellen zu prüfen markiert (Disclaimer vorhanden).

## Tests / Verifikation

- [ ] Doku-Review-Checkliste: `docs/compliance.md` enthält Abschnitte Residenz, PII-Minimierung, Retention/Löschung, Auftragsverarbeitung und einen Disclaimer.
- [ ] CASCADE-Löschpfad belegen (Smoke gegen Test-DB): einen Schüler mit Attempts/State anlegen, `DELETE FROM students WHERE id=:id;`, danach `SELECT count(*) FROM attempts WHERE student_id=:id` → `0` und analog für `learner_state`, `enrollments`, `teacher_notes`.
- [ ] Config-Check: Echtdaten-Profil dokumentiert `LLM_BACKEND=local`; falls `frontier`, ist die AVV-Anforderung verlinkt.

## Abhängigkeiten

- Keine technische Abhängigkeit (kann parallel ab Tag 1 laufen).
- Setzt Leitplanken, auf die **PROD-1** (schreibt nur in CH/EU-Prod-DB) und **PROD-2** (getrennte `DATABASE_URL` zur CH/EU-DB) operativ aufbauen.
- Nutzt das `ON DELETE CASCADE` aus dem Schema (DB-1/DB-2) für den Löschpfad.

## Definition of Done

- [ ] Akzeptanzkriterien (oben, abgeleitet aus docs/11 B.3) erfüllt.
- [ ] Tests/Smoke grün, inkl. CASCADE-Löschnachweis (Safety-/Compliance-relevant).
- [ ] Keine PII in externen LLM-Prompts (Echtdaten-Default `LLM_BACKEND=local`; bei `frontier` greift `scrub` + AVV/No-Training).
- [ ] `uv`-only, keine `pip`-Aufrufe.
- [ ] Zugehöriges GitHub-Issue PROD-3 geschlossen, E14-Epic-Checkliste aktualisiert.
