## Ziel

Die Schüler-Session-Hülle: `SessionScreen.tsx` zeigt **ein Konzept zur Zeit** mit Erklärung, aktueller Frage und Antwortfeld (`TutorThread.tsx`); der Lernstand wird **schonend** als gerundetes Prozent ohne Unsicherheit dargestellt (`MasteryBar.tsx`). Eine ggf. vorhandene Lehrernotiz wird dezent angezeigt; ein Unterstufen-Konfigurationsfall ist vorgesehen.

## Kontext & Prinzipien

- **P5 (Open Learner Model):** `MasteryBar` zeigt **nur** `mastery` (gerundetes %), **nie** `uncertainty` — die Rohschätzung mit Unsicherheit ist der Lehrerseite vorbehalten (`docs/09` Abschnitt 2/4). Konkret: die MasteryBar-Props nehmen `uncertainty` gar nicht erst entgegen.
- **P2 (kuratierte Bewertung):** „Antwort absenden" ruft den kuratierten Bewertungspfad (`intent:"answer"`), dessen `grade` aus dem Backend-Answer-Key stammt — nicht aus freier LLM-Generierung. Das Frontend stellt `grade.feedback` dar und hebt `mastery` an, erfindet aber nie selbst eine Bewertung.
- **P6 (Mensch im Loop sichtbar):** Eine Lehrernotiz über die:den Schüler:in wird als dezenter Hinweis gezeigt — die KI ist nicht die alleinige Instanz über den Lernweg.
- **Altersabhängigkeit (`docs/09` Abschnitt 5):** Die Unterstufen-Variante (weniger Text, Mastery für das Kind verborgen) ist ein **Konfigurationsfall** in dieser Codebasis, keine zweite.

## Zu erstellende/ändernde Dateien

Gemäss Repository-Layout (`docs/00` Section 6) und `docs/09` Abschnitt 1:

```
apps/web/src/student/
├── SessionScreen.tsx   # neu: die Session-Hülle, hält React-State
├── TutorThread.tsx     # neu: Erklärung + Frage + Antwortfeld + Feedback (Helfer-Buttons in FE-S3)
└── MasteryBar.tsx      # neu: gerundetes %, KEIN uncertainty; Unterstufen-Schalter
```

Ggf. anzupassen: `apps/web/src/api/client.ts` (aus FE-S1) und das `/student`-Routing in `src/main.tsx`, um `SessionScreen` zu mounten.

## Schnittstellen & Signaturen

Client-Vertrag aus FE-S1 / `docs/09` Abschnitt 1:

```ts
export type Intent = "answer" | "explain" | "hint" | "why" | "next";
export interface TurnResponse {
  grade?: { correct: boolean; feedback: string; confidence: number };
  mastery?: number;
  explanation?: string;
  route_reason?: string;
}
export const turn = (body: {subject_key:string; skill_key:string; intent:Intent; answer?:string; item_ref?:string}, t:string) =>
  post<TurnResponse>("/student/turn", body, t);
```

Verhalten laut `docs/09` Abschnitt 2:
- „Antwort absenden" → `turn({intent:"answer", answer, item_ref})` → zeigt `grade.feedback` und aktualisiert die `MasteryBar` aus `mastery`.

Vorgeschlagene Props (aus dem Doc-Verhalten abgeleitet):

```ts
// MasteryBar: nimmt mastery (0..1) -> gerundetes % + Balken. KEIN uncertainty nach aussen (P5).
interface MasteryBarProps {
  mastery: number;        // 0..1
  hidden?: boolean;       // Unterstufe: Mastery fuer das Kind verborgen (docs/09 §5)
}
// Anzeige: `${Math.round(mastery * 100)}%` + Balkenbreite; bei hidden keine Zahl.
```

> Hinweis: zu entscheiden — Lieferweg der `teacher_note`. `docs/09` sagt „vom Backend mitgeliefert", aber weder `TurnResponse` noch `GET /student/mastery` (docs/08) enthalten ein `teacher_note`-Feld. Empfehlung: `TurnResponse` um optionales `teacher_note?: { author: string; body: string }` erweitern (API-Änderung in E9). Bis dahin defensiv rendern (nur wenn vorhanden).

> Hinweis: zu entscheiden — Herkunft der aktuellen Frage und ihres `item_ref`. In docs/08/09 ist `item_ref` nur Request-Feld. Empfehlung: `TurnResponse` um die nächste Frage + `item_ref` erweitern oder `intent:"next"` nutzen. Bis dahin als TODO behandeln.

> Hinweis: zu entscheiden — Herkunft des `ageBand` (Unterstufe/Sekundarstufe): Token-Claim, Profil-Endpoint oder Routing. Vorerst als Prop in `SessionScreen` durchreichen.

## Umsetzungsschritte

- [ ] `MasteryBar.tsx`: Props `{ mastery: number; hidden?: boolean }`; rendert `Math.round(mastery*100)%` + Balken; bei `hidden` keine Zahl. **Niemals** `uncertainty` als Prop oder Anzeige.
- [ ] `TutorThread.tsx`: zeigt `explanation` (Agent), die aktuelle Frage und ein Antwortfeld (`<textarea>`/`<input>`).
- [ ] „Antwort absenden"-Button: ruft `turn({subject_key, skill_key, intent:"answer", answer, item_ref})`.
- [ ] Nach erfolgreicher Antwort: `grade.feedback` anzeigen; `mastery` an `MasteryBar` durchreichen (React-State anheben).
- [ ] `SessionScreen.tsx`: hält State (aktuelles `mastery`, letzter `feedback`, aktuelle `explanation`, `subject_key`/`skill_key`/`item_ref`, `ageBand`); rendert `TutorThread` + `MasteryBar`.
- [ ] Lehrernotiz-Anzeige: dezenter Hinweis („Notiz von …"), nur wenn vom Backend eine `teacher_note` mitgeliefert wird (defensiv, da Feld-Lieferweg offen).
- [ ] Unterstufen-Konfigurationsfall: `ageBand:"primary"` → reduzierter Text + `MasteryBar hidden`; `ageBand:"secondary"` → volle Anzeige. Eine Codebasis, kein zweiter Screen.
- [ ] Lade-/Fehlerzustände: Spinner während Request; neutrale Fehlermeldung bei `!r.ok` (kein Stacktrace/Leak).
- [ ] Reaktivität: kein `localStorage`/Browser-Storage als Quelle der Wahrheit; Stand kommt vom Backend (docs/09 Zustands-Hinweis).
- [ ] `/student`-Route in `main.tsx` auf `SessionScreen` zeigen.

## Akzeptanzkriterien

- [ ] `SessionScreen` zeigt ein Konzept zur Zeit (ruhig, ein Skill) (AK docs/09 §6: „`SessionScreen` zeigt ein Konzept").
- [ ] `MasteryBar` zeigt gerundetes Prozent + Balken und gibt **kein** `uncertainty` nach aussen (AK docs/09 §6: „`MasteryBar` ohne Unsicherheit nach aussen").
- [ ] „Antwort absenden" ruft `turn({intent:"answer", answer, item_ref})`, zeigt `grade.feedback` und aktualisiert die `MasteryBar` aus `mastery`.
- [ ] Eine vorhandene Lehrernotiz wird auf der Schülerseite dezent angezeigt (AK docs/09 §6: „Lehrernotiz wird auf Schülerseite angezeigt").
- [ ] Unterstufen-Konfigurationsfall ist vorgesehen (reduzierter Text, Mastery verborgen) — als Config, nicht als zweite Codebasis (docs/09 §5).
- [ ] `tsc --noEmit` fehlerfrei.

## Tests / Verifikation

```bash
# Backend bereitstellen (fuer echten /student/turn)
docker compose -f infra/docker-compose.yml up -d
cd apps/api && uv run uvicorn its.main:app --reload   # liefert POST /student/turn
# Frontend
cd apps/web && npm run typecheck && npm run dev
```

Erwartet:
- Eine Antwort absenden → `grade.feedback` erscheint, MasteryBar bewegt sich entsprechend `mastery`.
- Im Schüler-DOM taucht **kein** Unsicherheitswert/keine Rohschätzung auf (manuell + Code-Review prüfen).
- Bei `ageBand:"primary"` ist die Prozentzahl verborgen.
- Optionaler Vitest-Komponententest für `MasteryBar`: `mastery=0.37` → Text enthält `37%`; mit `hidden` → kein Prozenttext.

## Abhängigkeiten

- **FE-S1** (Projektgerüst + `api/client.ts`): liefert `turn()`, Typen und Routing, auf denen `SessionScreen` aufsetzt.
- **API-1** (`POST /student/turn`, `GET /student/mastery`): der Endpoint muss erreichbar sein, damit Antwort/Feedback/Mastery real funktionieren.

Nachgelagert (warten auf FE-S2):
- **FE-S3** erweitert `TutorThread` um die Helfer-Buttons.
- **TST-4** (E2E-Smoke, E12) nutzt diesen Flow (Login → Session → Antwort → Mastery).

## Definition of Done

Projektweite DoD (`docs/00` Section 8), auf FE-S2 zugeschnitten:
- [ ] Akzeptanzkriterien dieses Tasks erfüllt (ein Konzept, schonende MasteryBar, Antwortpfad, Lehrernotiz, Unterstufenfall).
- [ ] Typecheck grün; optionale Komponententests grün. (Kein DB-Safety-Test direkt betroffen — Isolation liegt im Backend/RLS.)
- [ ] Keine PII in externen LLM-Prompts — entfällt im Frontend (generative Calls laufen serverseitig anonymisiert).
- [ ] **P5 eingehalten:** kein `uncertainty`/keine Rohschätzung auf der Schülerseite (im Review verifiziert).
- [ ] `uv`-only — entfällt für `apps/web`; kein `pip` im Python-Teil berührt.
- [ ] Zugehöriges GitHub-Issue FE-S2 geschlossen, E10-Epic-Checkliste aktualisiert.

