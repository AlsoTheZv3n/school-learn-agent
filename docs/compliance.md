# Datenresidenz, Retention & Auftragsverarbeitung (PROD-3)

> **Status: Architektur-Leitplanken, KEIN Rechtsrat.** Diese Plattform verarbeitet
> identifizierbare Daten über **Minderjährige**. revDSG (CH), DSGVO (EU) sowie
> kantonale/schulische Ed-Tech-Vorgaben ändern sich laufend. **Vor dem
> Produktivbetrieb mit echten Schülerdaten ist eine fachliche/rechtliche Prüfung
> gegen aktuelle Quellen einzuholen.** Die folgenden Punkte sind Voraussetzung, kein
> Anhang (P8).

## 1. Datenresidenz (CH/EU)

- **Datenbank** und – falls extern – **LLM-Inferenz** laufen in einer **CH/EU-Region**
  (z. B. Azure Switzerland, Exoscale, Infomaniak). Prototyp-Hosting (Railway o. Ä.) ist
  **nicht** für Echtdaten zugelassen.
- Getrennte `DATABASE_URL` für Dev/Mock und Prod — **kein** gemeinsamer Cluster für
  Mock- und Echtdaten (durchgesetzt über `DATA_MODE`, siehe §4).

## 2. PII-Minimierung (P4)

- Das Schema hält bereits wenig PII (`students`: nur `display_name`, `grade_level`;
  kein Freitext-Profil — siehe `docs/03-database.md`).
- Der LLM-Pfad ist **anonymisiert**: `its/llm/anonymize.py` (`scrub`) entfernt
  Name/Datum/E-Mail vor jedem externen Call; dem Modell werden ohnehin nur IDs und
  Skill-Keys übergeben. Alternativ läuft alles Identifizierende auf einem lokalen Modell.

## 3. Retention & Löschung

- **Aufbewahrungsfenster** pro Datenkategorie definieren (z. B. Lernspuren X Schuljahre,
  danach Anonymisierung/Löschung). *(Konkrete Fristen: rechtlich zu klären.)*
- **Löschpfad pro Schüler:in**: das Schema ist mit `ON DELETE CASCADE` vorbereitet
  (`attempts`, `learner_state`, `teacher_notes`, `enrollments` hängen an `students.id`).
  Ein einzelnes `DELETE FROM students WHERE id = …` entfernt damit alle personenbezogenen
  Spuren. Ein produktiver Lösch-/Export-Workflow (Betroffenenrechte) ist zu ergänzen.

## 4. Mock/Prod-Trennung & Guards (PROD-2)

Eine Umgebungsvariable steuert den Modus; die Guards greifen **im Code**, nicht nur in der Doku:

| | Dev/Mock | Prod |
|---|---|---|
| `DATA_MODE` | `mock` | `prod` |
| `DATABASE_URL` | lokal (z. B. `127.0.0.1:5433`) | CH/EU-Region, eigene DB |
| Seeder (`scripts/seed.py`, `--reset`) | erlaubt | **gesperrt** (`guard_mock`) |
| `scripts/import_production.py` | gesperrt | **erforderlich** (`require_prod`) |

- `its/data/seed.py` → `guard_mock()`: Seeden/Reset bricht ab, wenn `DATA_MODE != mock`.
- `its/data/production.py` → `require_prod()`: Import bricht ab, wenn `DATA_MODE != prod`.
- Personen-Import ist **idempotent** über stabile externe Schlüssel (`students.external_id`,
  `classes.external_id`, Migration 0004) — Upsert statt blindem Insert.

## 5. Auftragsverarbeitung (AVV/DPA)

- Wird eine **externe LLM-API** genutzt, sind ein **Auftragsverarbeitungsvertrag (AVV/DPA)**
  und ein **No-Training-Setting** erforderlich. Andernfalls ist ein **lokales Modell** zu
  betreiben (`LLM_BACKEND=local`).
- Jede externe Datenweitergabe ist im Verarbeitungsverzeichnis zu dokumentieren.

## 6. Checkliste vor Produktivbetrieb

- [ ] DB + LLM-Inferenz in CH/EU-Region, getrennte Prod-`DATABASE_URL`
- [ ] Echtes Auth/IdP statt FND-5-Stub (JWT-Verifikation, Rollen→RLS)
- [ ] Retention-Fristen je Datenkategorie festgelegt; Lösch-/Exportworkflow implementiert
- [ ] AVV/DPA + No-Training bei externer LLM-Nutzung **oder** lokales Modell
- [ ] RLS- und Min-Cohort-Garantien in Prod verifiziert (Safety-Tests CI-blockierend)
- [ ] Rechtliche Prüfung (revDSG/DSGVO, kantonal/schulisch) **abgeschlossen**
