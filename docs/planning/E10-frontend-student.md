# E10 — Frontend: Schüler-Session — Detailplanung

> Vertiefendes Planungsdokument ausschliesslich für Epic E10 (Milestone **M4 — API & Frontend**).
> Quelle: `docs/09-frontend.md` (Abschnitte 1, 2, 4, 5, 6) sowie die Querschnittsprinzipien aus
> `docs/00-architecture.md` (P1–P9, Section 6 Repo-Layout, Section 8 DoD).

## 1. Scope & Zielbild

E10 liefert die **ruhige Schüler-Session** des ITS: eine Single-Page-React/TypeScript-Anwendung
unter `apps/web`, die ein einziges Konzept zur Zeit präsentiert, dem Kind ermutigendes Feedback
gibt und den Lernstand **schonend** (gerundetes Prozent, ohne Unsicherheit) anzeigt. E10 umfasst
genau drei Tasks:

- **FE-S1** — Projekt-Setup (Vite + React + TS, getrenntes Routing `/student` und `/teacher`,
  typisierter `api/client.ts`). Dies ist das gemeinsame Fundament für E10 **und** E11; nur die
  Schüler-Teile werden in E10 mit Leben gefüllt.
- **FE-S2** — Session-Screen: `SessionScreen.tsx`, `TutorThread.tsx` (Erklärung + Frage +
  Antwortfeld + Feedback), `MasteryBar.tsx` (gerundetes %, kein `uncertainty`), Anzeige einer
  Lehrernotiz, plus Unterstufen-Konfigurationsfall.
- **FE-S3** — Helfer-Aktionen: drei Buttons („Anders erklären", „Hinweis", „Wozu?"), die den
  **generativen** `explain`/`hint`/`why`-Pfad aufrufen — strikt getrennt vom Bewertungspfad
  (`answer`).

**Nicht in E10:** Lehrer-Dashboard (E11), Backend-Endpoints (E9/API-1..3), echter Auth-/IdP-Flow
(FND-5 ist nur Stub), E2E-Smoke-Test inkl. Lehrersicht (TST-4, gehört zu E12). E10 konsumiert die
in `docs/08-backend-api.md` definierten Endpoints `POST /student/turn` und `GET /student/mastery`.

**Designkern (docs/09 Abschnitt 4):** „Zwei Sichten, eine Wahrheit." Dieselbe `learner_state`-Zeile
wird auf der Schülerseite als ermutigendes Prozent **ohne** Unsicherheit gezeigt, auf der
Lehrerseite mit Unsicherheit. E10 implementiert ausschliesslich die Schülerpräsentation — die
Scoping-Idee aus P1/P5 angewandt auf **Präsentation**, nicht nur auf Daten.

## 2. Task-Reihenfolge & Abhängigkeiten

```
FND-1 (Monorepo, M0) ─► FE-S1 (Setup) ─┬─► FE-S2 (Session-Screen) ─► FE-S3 (Helfer-Aktionen)
                                        │
API-1 (POST /student/turn, GET /student/mastery, M4) ───────────────┘ (FE-S2 braucht laufende API)
```

- **FE-S1** hängt nur an **FND-1** (Monorepo-Grundgerüst mit `apps/web`-Verzeichnis).
- **FE-S2** hängt an **FE-S1** (Projektgerüst + `api/client.ts`) **und** an **API-1** (der
  `/student/turn`- und `/student/mastery`-Endpoint muss erreichbar sein, sonst nur Mock-Stub).
- **FE-S3** hängt an **FE-S2** (erweitert `TutorThread` um die drei Helfer-Buttons).
- Nachgelagert: **FE-T1** (E11) hängt ebenfalls an FE-S1 (gemeinsames Gerüst/Routing).
  **TST-4** (E2E-Smoke, E12) hängt indirekt an FE-S2/FE-S3 (Schüler-Flow) und FE-T2.

Empfohlene Bearbeitungsreihenfolge: FE-S1 → FE-S2 → FE-S3 (linear; FE-S1 kann parallel zu API-1
laufen, FE-S2 erst wenn API-1 mergebar ist oder ein klar markierter Mock genutzt wird).

## 3. Feinere Sub-Task-Zerlegung (über die Issues hinaus)

**FE-S1**
- S1.1 Vite-Scaffold (`npm create vite@latest -- --template react-ts`) in `apps/web`.
- S1.2 `.gitignore`-Ergänzung (node_modules/, dist/) ist bereits durch FND-1 abgedeckt — prüfen.
- S1.3 `src/main.tsx` + Router-Setup (`react-router-dom`) mit Routen `/student` und `/teacher`.
- S1.4 `src/api/client.ts` exakt nach docs/09 Abschnitt 1 (typisierter `post<T>`, `Intent`,
  `TurnResponse`, `turn()`); zusätzlich `myMastery()` (GET /student/mastery, schonende Sicht).
- S1.5 `VITE_API_BASE` über `.env`/`import.meta.env` lesbar machen; `.env.example` für `apps/web`.
- S1.6 Auth-Token-Herkunft: provisorischer Bezug (z. B. `localStorage`/Stub) — als TODO markieren,
  bis FND-5/echter IdP steht. **Offene Frage (siehe §6).**
- S1.7 Skripte: `dev`, `build`, `typecheck` (`tsc --noEmit`), `lint` (falls eslint gewünscht).

**FE-S2**
- S2.1 `MasteryBar.tsx`: Props `{ mastery: number; hidden?: boolean }`; rendert
  `Math.round(mastery*100)%` + Balken; bei `hidden` (Unterstufe) keine Zahl. Niemals `uncertainty`.
- S2.2 `TutorThread.tsx`: zeigt `explanation`, aktuelle Frage, Antwortfeld; „Antwort absenden" ruft
  `turn({intent:"answer", answer, item_ref})`, zeigt `grade.feedback`, hebt `mastery` an MasteryBar.
- S2.3 `SessionScreen.tsx`: Session-Hülle, hält React-State (aktuelles `mastery`, letzter
  `grade.feedback`, `explanation`, aktueller `skill_key`/`subject_key`/`item_ref`).
- S2.4 Lehrernotiz-Anzeige: rendert dezenten Hinweis, falls eine `teacher_note` vom Backend
  mitgeliefert wird. **Lieferweg ist im Plan offen** (siehe §6) → als TODO/Notiz behandeln.
- S2.5 Unterstufen-Konfigurationsfall: ein Prop/Config-Schalter (z. B. `ageBand: "primary"|"secondary"`)
  steuert reduzierten Text + verborgene Mastery — **eine** Codebasis, kein zweiter Screen.
- S2.6 Lade-/Fehlerzustände (Spinner, neutrale Fehlermeldung bei `!r.ok`).
- S2.7 Reaktivität: kein Browser-Storage als Quelle der Wahrheit; Stand kommt vom Backend.

**FE-S3**
- S3.1 Drei Buttons in `TutorThread`: „Anders erklären" → `turn({intent:"explain"})`, „Hinweis" →
  `turn({intent:"hint"})`, „Wozu?" → `turn({intent:"why"})`.
- S3.2 Antwort: `TurnResponse.explanation` wird angezeigt; **kein** `grade`-Pfad berührt, MasteryBar
  bleibt unverändert (generativer Pfad ist P2-getrennt).
- S3.3 UI-Trennung sichtbar machen: Helfer-Buttons optisch von „Antwort absenden" abgesetzt.
- S3.4 Doppelklick-/Race-Schutz (Buttons während laufendem Request deaktivieren).

## 4. Zentrale Designentscheidungen (mit Begründung)

1. **Vite + React + TS** (docs/00 Section 5, docs/09 Abschnitt 1): eine Skill, zwei sehr
   unterschiedliche Sichten (Schüler ruhig, Lehrer dicht). TS gibt typsichere API-Verträge.
2. **Eine Naht für API-Calls (`api/client.ts`)**: alle `fetch`-Aufrufe inkl. Auth-Header und
   Typisierung an genau einer Stelle. Das spiegelt P7 auf Frontend-Ebene (keine wuchernden Adapter)
   und macht den Auth-Token-Übergang (Stub → echter IdP) zu einer Einzeländerung.
3. **MasteryBar zeigt nie `uncertainty`** (P5): Unsicherheit ist Lehrerseite. Der Schüler-Mastery-
   Endpoint `GET /student/mastery` liefert laut docs/08 ohnehin die schonende Sicht; die UI darf
   selbst dann keine Rohschätzung darstellen, wenn das Feld versehentlich ankäme.
4. **Bewertungspfad vs. generativer Pfad strikt getrennt** (P2): `answer` läuft über den
   kuratierten `assess`-Pfad (Backend), `explain`/`hint`/`why` über den generativen `explain`-Pfad.
   Im Frontend bedeutet das: Helfer-Aktionen aktualisieren **nie** die MasteryBar und zeigen nie
   `grade`.
5. **Unterstufe als Konfigurationsfall, nicht als zweite Codebasis** (docs/09 Abschnitt 5):
   ein `ageBand`-Schalter in `MasteryBar`/`SessionScreen`, kein paralleler Screen.
6. **Mensch-im-Loop sichtbar** (P6): die Lehrernotiz erscheint als dezenter Hinweis auf der
   Schülerseite — die KI ist nicht die alleinige Instanz.
7. **Kein Browser-Storage als Quelle der Wahrheit** (docs/09 Zustands-Hinweis): Feedback und
   Mastery sind reaktiver React-State; der Stand kommt vom Backend.

## 5. Risiken & Gegenmassnahmen

| Risiko | Gegenmassnahme |
|---|---|
| **Leak von `uncertainty` auf Schülerseite** (P5-Bruch) | `MasteryBar`-Props nehmen `uncertainty` gar nicht erst entgegen; `myMastery()` mappt nur `mastery` durch; Code-Review + ggf. Unit-Test, der prüft, dass kein Unsicherheits-Text gerendert wird. |
| **Vermischung Bewertungs-/generativer Pfad** (P2-Bruch) | Helfer-Buttons rufen ausschliesslich `intent: explain/hint/why`; ein Test/Assertion stellt sicher, dass nach einem Helfer-Aufruf MasteryBar und `grade` unverändert bleiben. |
| **API-1 noch nicht fertig** (FE-S2 blockiert) | FE-S1 vorziehen; klar markierten Mock-Adapter hinter `api/client.ts` nur temporär; vor Merge auf echten Endpoint umstellen. |
| **Auth-Token-Herkunft unklar** (FND-5 ist Stub) | Token-Bezug an einer Stelle kapseln; als TODO markieren; nicht erfinden. |
| **Lieferweg der `teacher_note` unspezifiziert** | UI defensiv bauen (Notiz nur rendern, wenn vorhanden); Backend-Feld als offene Frage eskalieren, statt ein Schema zu erfinden. |
| **PII im Frontend** (P4) | Frontend ruft keine externen LLMs direkt; alle generativen Calls laufen serverseitig über `/student/turn` (Anonymisierung passiert im Backend). Keine PII in Query-Strings/Logs. |
| **Hosting/Datenresidenz** (P8) | Statische Web-Assets ebenfalls in CH/EU-Region ausliefern; in Deploy-Doku festhalten (Verweis E14/PROD-3). |

## 6. Offene Fragen / zu treffende Entscheidungen

1. **Auth-Token-Herkunft im Frontend.** `api/client.ts` erwartet einen `token: string`, aber woher
   stammt er? FND-5 ist nur ein JWT-Stub. Bis IdP-Wahl (Keycloak/Authentik/Entra) feststeht, ist der
   Token-Bezug provisorisch. → *Empfehlung:* dünner `auth/token.ts`-Provider mit Stub, hinter einem
   Interface, das später den echten OIDC-Flow liefert.
2. **Lieferweg der Lehrernotiz auf die Schülerseite.** docs/09 sagt „vom Backend mitgeliefert", aber
   weder `TurnResponse` noch `GET /student/mastery` enthalten ein `teacher_note`-Feld (docs/08). →
   *Empfehlung:* `TurnResponse` um optionales `teacher_note?: { author: string; body: string }`
   erweitern (API-Änderung in E9 anstossen), nicht im Frontend erfinden.
3. **`item_ref`/Fragenbezug.** Woher bekommt das Frontend die aktuelle Frage und ihr `item_ref`?
   docs/09/08 zeigen `item_ref` nur als Request-Feld. → *Empfehlung:* `TurnResponse` um die nächste
   Frage + `item_ref` ergänzen (oder ein eigener `/student/next`-Aufruf via `intent:"next"`).
4. **Unterstufen-Schalter — Herkunft.** Kommt `ageBand` aus dem Auth-Token-Claim, aus einem
   Profil-Endpoint oder aus Routing? → *Empfehlung:* als Prop/Config in `SessionScreen` durchreichen,
   Quelle vorerst Token-Claim (Stub), als TODO markieren.
5. **`VITE_API_BASE` für Dev/Prod.** Default ist `""` (gleicher Origin). Bei getrenntem API-Host
   (CH/EU) muss er gesetzt + CORS am Backend erlaubt werden. → *Empfehlung:* `.env.example` mit
   dokumentiertem Default; CORS-Bedarf an E9 melden.
6. **Lint/Test-Toolchain für `apps/web`.** docs nennen für Frontend keine konkreten Test-Tools
   (Vitest? Playwright erst in TST-4). → *Empfehlung:* `tsc --noEmit` als Pflicht-Gate; Vitest für
   `MasteryBar`/Pfadtrennung optional, Playwright-E2E in E12/TST-4 belassen.

## 7. Test-/Verifikationsstrategie für das Epic

- **Typecheck als Pflicht-Gate:** `npm run typecheck` (`tsc --noEmit`) muss in `apps/web` fehlerfrei
  sein — der typisierte `api/client.ts` ist die Hauptabsicherung des API-Vertrags.
- **Build:** `npm run build` (Vite) erzeugt `dist/` ohne Fehler.
- **Manuell/Smoke (FE-S2):** `npm run dev`, gegen laufende API (`uv run uvicorn its.main:app` +
  `docker compose -f infra/docker-compose.yml up -d`); eine Antwort absenden → `grade.feedback`
  erscheint, MasteryBar bewegt sich.
- **Pfadtrennung (FE-S3):** Helfer-Buttons klicken → `explanation` erscheint, MasteryBar und
  `grade`-Anzeige bleiben unverändert (optional als Vitest-Komponententest).
- **P5-Check:** sicherstellen, dass weder `uncertainty` noch eine Rohschätzung im Schüler-DOM
  auftaucht (Code-Review + optionaler Test).
- **E2E (nachgelagert, TST-4/E12):** Playwright-Smoke Login → Session → Antwort → Mastery sichtbar;
  in E10 nur vorbereitet, nicht abgeschlossen.

