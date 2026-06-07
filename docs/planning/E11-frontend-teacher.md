# E11 — Frontend: Lehrer-Dashboard — Detailplanung

> Quelle: `docs/09-frontend.md` (Abschnitte 1, 3, 4, 5, 6) sowie die nicht verhandelbaren Prinzipien P1–P9 und das Repository-Layout aus `docs/00-architecture.md` (Section 6). Schnittstellen-Vertrag gegen `docs/08-backend-api.md` (API-2, Teacher-Endpoints) und `docs/02-foundations.md` (Auth-Gerüst, Principal). Milestone: **M4 API & Frontend**.

## 1. Scope & Zielbild

Das Lehrer-Dashboard ist die **dichte, transparente** Gegen-Sicht zur ruhigen Schülerseite (E10) — über **dieselben Daten** (`learner_state`), aber mit anderer Präsentation. Es realisiert drei der nicht verhandelbaren Prinzipien sichtbar im UI:

- **Open Learner Model (P5):** Die Lehrperson sieht pro Skill nicht nur `mastery`, sondern auch `uncertainty` und `attempts_count` — also *wie verlässlich* die Einschätzung ist und *warum* das System ein Kind als „(noch) nicht gemeistert" einstuft.
- **Mensch im Loop als Sicherheitsarchitektur (P6):** Die Lehrperson kann eingreifen (Notiz, optionaler Mastery-Override). Die Notiz erscheint anschliessend auf der Schülerseite.
- **Safety in der DB (P1):** Die UI filtert **nicht** selbst nach „eigenen Klassen". RLS auf dem Backend erzwingt, dass `GET /teacher/...` nur Schüler:innen der eigenen Klassen zurückgibt. Bei zu kleiner Kohorte liefert das Backend `403`; die UI macht daraus einen menschenlesbaren Datenschutz-Hinweis statt Zahlen.

Konkretes Zielbild am Epic-Ende:
- `Dashboard.tsx` (FE-T1): Lehrperson loggt sich ein, sieht ihre Klassen → Schülerliste → kann eine:n Schüler:in zur Detailsicht öffnen. Es erscheinen ausschliesslich eigene Klassen (RLS, nicht UI-Logik).
- `LearnerModelPanel.tsx` (FE-T2): Für die:den ausgewählte:n Schüler:in werden alle Skills mit Mastery **und** Unsicherheit (Unsicherheitsband / „n Versuche"-Indikator) gerendert. Eine Kohorten-/Verteilungsansicht ruft `distribution(class_id, skill_id)` und zeigt bei `403` den Min-Cohort-Hinweis.
- `InterventionControls.tsx` (FE-T3): Notiz-Formular (`addNote`) plus optionaler `override_mastery`; nach dem Absenden ist die Notiz persistiert und auf der Schülerseite sichtbar.

Out of Scope für E11: Schülerseite (E10), Backend-Endpoints (E9/API-2 — Voraussetzung), echter JWT-Flow (FND-5/Auth-Paket — siehe offene Frage zur Token-Herkunft), Playwright-Browser-E2E (das ist TST-4 in E12, hier nur ein leichter Smoke).

## 2. Task-Reihenfolge & Abhängigkeiten

```
FE-S1 (Projekt-Setup: Vite+React+TS, api/client.ts, Routing) ─┐
API-2 (Teacher-Endpoints, RLS-gefiltert)                       ├─▶ FE-T1 (Dashboard-Shell)
                                                               │       │
                                                               │       ▼
                                                       API-2 ──┴─▶ FE-T2 (LearnerModelPanel)
                                                                       │
                                                                       ▼
                                                                   FE-T3 (InterventionControls)
                                                                       │
                                                                       ▼
                                                          (nachgelagert) TST-4 E2E-Smoke
```

- **FE-T1** braucht FE-S1 (das `apps/web`-Gerüst, `api/client.ts`, Routing) und API-2 (Klassen-/Schülerdaten-Quelle).
- **FE-T2** braucht FE-T1 (die Shell + die Auswahl einer:s Schüler:in liefert die `student_id`) und API-2 (`GET /teacher/student/{id}/mastery` inkl. `uncertainty`).
- **FE-T3** braucht FE-T2 (es greift auf die im Panel ausgewählte:n Schüler:in/Skill zu) und schreibt über `POST /teacher/student/{id}/note`.
- **Nachgelagert:** TST-4 (E12) hängt explizit von FE-T2 + API-2 ab und prüft „Lehrer sieht Stand inkl. Unsicherheit".

## 3. Feinere Sub-Task-Zerlegung (über die Issues hinaus)

**FE-T1 — Dashboard-Shell**
- Routing-Eintrag `/teacher` (und `/teacher/student/:studentId`) im Router aus FE-S1; Rollenweiche `teacher` aus dem Auth-Token.
- `api/client.ts` um Teacher-Calls erweitern: `studentMastery()`, `distribution()`, `addNote()` (typisiert gegen die API-2-Schemas) — sofern FE-S1 sie nur stub-weise enthielt.
- Klassen-/Schülerlisten-Datenquelle klären (offene Frage: es gibt in API-2 noch keinen `GET /teacher/classes`-Endpoint). Bis dahin Schülerauswahl per `student_id`-Eingabe/Navigation als Übergangslösung kapseln.
- Loading-/Error-/Empty-States (keine Klassen) als wiederverwendbare Komponenten.

**FE-T2 — LearnerModelPanel**
- TypeScript-Typ `SkillMastery` (mit `uncertainty`, `attempts_count`) gegen das API-2-Schema spiegeln.
- Visualisierung: Mastery-Balken + Unsicherheitsband (z. B. `mastery ± uncertainty` als helleres Band) und „n Versuche"-Badge aus `attempts_count`.
- Sortier-/Filtersicht (z. B. „niedrigste Mastery zuerst") für Dichte.
- Verteilungsansicht: `distribution(class_id, skill_id)` → `CohortStat {n, avg_mastery}`; `403`-Pfad → Datenschutz-Hinweis-Komponente.
- Klar markieren, dass `uncertainty` **nur** hier (Lehrerseite) sichtbar ist — nie an eine Schüler-Komponente weiterreichen (P5).

**FE-T3 — InterventionControls**
- Notiz-Formular: Pflichtfeld `body`, optional `skill_id` (aus dem im Panel gewählten Skill vorbefüllbar), optional `override_mastery` (0–1, validiert).
- Submit → `addNote(student_id, {body, skill_id?, override_mastery?})`; Erfolgs-/Fehler-Feedback.
- Hinweistext im UI: „Diese Notiz wird der:dem Schüler:in angezeigt" (Transparenz, P6).
- Optionales Re-Fetch des LearnerModelPanel nach Override, damit der überschriebene Wert sofort sichtbar ist (Datenfluss-Entscheidung, siehe §4).

## 4. Zentrale Designentscheidungen mit Begründung

1. **Zwei Sichten, eine Wahrheit (docs/09 §4).** Schüler- und Lehrerkomponenten teilen die `learner_state`-Daten, aber `uncertainty` wird ausschliesslich in `teacher/`-Komponenten gerendert. Begründung: P5 ist ein Präsentations-Scoping, kein Daten-Scoping — Datentrennung allein reicht nicht; ein Prozentwert mit Unsicherheit demotiviert/verwirrt Kinder.
2. **UI filtert nicht — RLS filtert (P1).** Der Dashboard-Code enthält bewusst **keine** „nur eigene Klassen"-Logik. Begründung: Sicherheit als Schema-Eigenschaft; eine fehlerhafte UI darf keine fremden Schüler:innen zeigen, weil das Backend sie gar nicht erst liefert.
3. **`403` = Feature, nicht Fehler.** Der Min-Cohort-`403` der Verteilungsansicht wird gezielt abgefangen und als „zu wenige Lernende für eine anonyme Auswertung" gerendert. Begründung: Min-Cohort sichtbar gemacht (docs/09 §3); ein generischer Error-Toast würde die Datenschutzgarantie verschleiern.
4. **Typisierter `api/client.ts` als einzige Backend-Naht.** Alle HTTP-Aufrufe gehen über `client.ts`; Komponenten kennen kein `fetch`. Begründung: ein Ort für Auth-Header und Statuscode-Behandlung (`403`/`404`), konsistente Typen aus den API-2-Pydantic-Schemas.
5. **Refetch statt optimistischem Override.** Nach `addNote`/Override wird das Panel neu geladen statt lokal zu mutieren. Begründung: Das Backend ist die Wahrheit (P3 — das Modell ändert sich, nicht das UI); ein optimistisches Update könnte einen Wert zeigen, den RLS/Backend gar nicht so geschrieben hat.

## 5. Risiken & Gegenmassnahmen

| Risiko | Gegenmassnahme |
|---|---|
| Kein `GET /teacher/classes`-Endpoint in API-2 → Dashboard-Klassenliste hat keine Datenquelle | Als offene Frage eskalieren; Übergangslösung: Navigation per `student_id`; Endpoint in API-2 nachfordern. |
| `uncertainty` versehentlich in eine geteilte/Schüler-Komponente durchgereicht → P5-Bruch | `uncertainty` nur im `teacher/`-Verzeichnis verwenden; Lint-/Review-Regel; Smoke-Test prüft, dass die Schülerantwort keine `uncertainty` enthält. |
| `403` (Min-Cohort) als generischer Fehler behandelt → Zahlen geleakt oder verwirrender Toast | Statuscode-spezifische Behandlung in `client.ts`/Panel; expliziter Test für den `403`-Pfad. |
| Token-Herkunft/Claims-Mapping ungeklärt (FND-5-Stub wirft `NotImplementedError`) | Auth-Flow als offene Frage; `client.ts` nimmt Token als Parameter, Quelle abstrahiert (Übergangs-Devtoken). |
| PII (Schülernamen) im Frontend/Logs | Nur anzeigen, was API-2 liefert; keine Namen in Browser-Logs; Datenresidenz CH/EU bleibt Backend-Sache (P8). |
| Override ohne Audit-Spur | `teacher_notes` schreibt `teacher_id` + `skill_id` + `override_mastery` (Backend); UI macht den Override sichtbar als Notiz-Eintrag. |

## 6. Offene Fragen / zu treffende Entscheidungen

1. **Klassen-/Schülerlisten-Endpoint:** API-2 spezifiziert `student_mastery`, `distribution`, `add_note`, aber **keinen** `GET /teacher/classes` bzw. `GET /teacher/class/{id}/students`. Woher bezieht `Dashboard.tsx` die Klassen-/Schülerliste? (Empfehlung: Endpoint nachziehen.)
2. **Auth-/Token-Herkunft:** FND-5 ist ein Stub (`NotImplementedError`). Wie kommt das Lehrer-Token ins Frontend (IdP-Redirect, Login-Formular, Devtoken)? Welche Claims tragen die Rolle und `user_id`?
3. **`distribution`-Parameter `class_id`:** Die Verteilungsansicht braucht eine `class_id` — die ist ohne Klassenliste (Frage 1) nicht verfügbar.
4. **Override-Semantik:** Verdrängt `override_mastery` den BKT-Wert dauerhaft, oder ist es ein paralleler, angezeigter Hinweis? Spiegelt `GET /teacher/student/{id}/mastery` den Override danach wider?
5. **`addNote`-Request-Form:** Die Backend-Signatur nutzt Query/Body-Parameter (`body: str`, `skill_id`, `override_mastery`); der Frontend-Doc-Auszug suggeriert `addNote(student_id, body)`. Verbindlicher Request-Body (JSON vs. Query) festlegen.

## 7. Test-/Verifikationsstrategie für das Epic

- **Build/Typecheck:** `npm run build` bzw. `tsc --noEmit` in `apps/web` muss fehlerfrei sein; die TypeScript-Typen (`SkillMastery`, `CohortStat`, `TurnResponse`) müssen mit den API-2-Schemas übereinstimmen.
- **Lint:** `npm run lint` grün.
- **Komponenten-/Verhaltenstest (sofern Test-Runner aus FE-S1 vorhanden):** Panel rendert `uncertainty` (Lehrerseite); `403` der Verteilung erzeugt den Min-Cohort-Hinweis statt Zahlen; `addNote` ruft den korrekten Pfad.
- **Manueller Smoke gegen laufende API:** Teacher-Token → Dashboard zeigt nur eigene Klassen; Panel zeigt Mastery + Unsicherheit; kleine Kohorte → Hinweis; Notiz absenden → erscheint auf der Schülerseite.
- **Nachgelagert (E12/TST-4):** HTTP-/Browser-E2E „Login → Lehrer sieht Stand inkl. Unsicherheit".
- **DoD-Querschnitt (docs/00 §8):** AK aus docs/09 §6 erfüllt; Safety-Tests betroffen nur indirekt (RLS bleibt Backend); keine PII in externen LLM-Prompts (hier nicht betroffen); `uv`-only betrifft nur den Python-Teil — im Frontend gilt analog kein `pip`; Issue geschlossen + Epic-Checkliste aktualisiert.
