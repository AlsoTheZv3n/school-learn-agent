## Ziel

Drei Helfer-Aktionen im `TutorThread` — „Anders erklären", „Hinweis" und „Wozu?" — rufen den **generativen** Pfad (`intent: explain | hint | why`) und zeigen dessen `explanation` an, **strikt getrennt** vom Bewertungspfad. Sie verändern weder die MasteryBar noch eine `grade`-Anzeige.

## Kontext & Prinzipien

- **P2 (kuratierte Bewertung vs. generative Freiheit):** Dies ist der Kern dieses Tasks. Der Bewertungspfad (`answer` → kuratierter Answer Key) und der generative Pfad (`explain`/`hint`/`why` → freie Erklärung) sind im Backend bereits getrennt; das Frontend muss diese Trennung sichtbar halten. Ein Helfer-Klick darf **nie** eine Bewertung erzeugen oder die Mastery anheben — generative Fehler sind geringfügig und das Kind fragt einfach erneut.
- **P4/P8 (PII / Residenz):** Die generativen Aufrufe gehen über das eigene Backend (`/student/turn`), das vor externen LLM-Calls anonymisiert. Das Frontend ruft keine externen LLMs direkt und sendet keine PII in Query-Strings/Logs.
- **P5 (mittelbar):** Auch der generative Pfad führt zu keiner Anzeige von Unsicherheit auf der Schülerseite.

## Zu erstellende/ändernde Dateien

Gemäss Repository-Layout (`docs/00` Section 6) und `docs/09` Abschnitt 2:

```
apps/web/src/student/
└── TutorThread.tsx   # ändern: drei Helfer-Buttons + Anzeige der explanation
```

Keine neuen Dateien zwingend nötig; `api/client.ts` aus FE-S1 wird unverändert genutzt (`turn()` deckt alle Intents ab).

## Schnittstellen & Signaturen

Client-Vertrag (FE-S1 / `docs/09` Abschnitt 1) — `Intent` enthält bereits alle Helfer-Werte:

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

Verhalten laut `docs/09` Abschnitt 2 (Helfer-Aktionen, FE-S3):

```
„Anders erklären" → turn({intent:"explain"})
„Hinweis"        → turn({intent:"hint"})
„Wozu?"          → turn({intent:"why"})
```

Backend-Hintergrund (`docs/07-agent.md`): Bei diesen Intents verzweigt der Graph auf den `explain`-Node (generativ); nur `intent:"answer"` läuft über `assess` (kuratiert). Das Frontend zeigt entsprechend `TurnResponse.explanation` an und lässt `grade`/`mastery` unberührt.

## Umsetzungsschritte

- [ ] In `TutorThread.tsx` drei Buttons ergänzen: „Anders erklären", „Hinweis", „Wozu?".
- [ ] „Anders erklären" → `turn({subject_key, skill_key, intent:"explain", item_ref})`.
- [ ] „Hinweis" → `turn({subject_key, skill_key, intent:"hint", item_ref})`.
- [ ] „Wozu?" → `turn({subject_key, skill_key, intent:"why", item_ref})`.
- [ ] Antwort: `TurnResponse.explanation` in der Thread-Ansicht anzeigen.
- [ ] Sicherstellen, dass Helfer-Aufrufe **nicht** die MasteryBar aktualisieren und **keine** `grade`-Anzeige setzen (nur `explanation` rendern).
- [ ] UI-Trennung sichtbar machen: Helfer-Buttons optisch von „Antwort absenden" abgesetzt (eigene Button-Gruppe).
- [ ] Race-/Doppelklick-Schutz: Buttons während eines laufenden Requests deaktivieren.
- [ ] Fehlerfall neutral behandeln (kein Stacktrace; freundliche „Versuch es nochmal"-Meldung).

## Akzeptanzkriterien

- [ ] Die drei Helfer-Aktionen rufen `turn({intent:"explain"})`, `turn({intent:"hint"})` bzw. `turn({intent:"why"})` (AK docs/09 §6: „Helfer-Aktionen rufen den `explain`-Pfad").
- [ ] Der generative Pfad ist klar getrennt vom Bewertungspfad: ein Helfer-Klick erzeugt **keine** `grade` und ändert die MasteryBar **nicht** (AK docs/09 §6: „getrennt vom Bewertungspfad").
- [ ] `TurnResponse.explanation` wird angezeigt.
- [ ] Buttons sind optisch von „Antwort absenden" abgesetzt; während eines Requests deaktiviert.
- [ ] `tsc --noEmit` fehlerfrei.

## Tests / Verifikation

```bash
docker compose -f infra/docker-compose.yml up -d
cd apps/api && uv run uvicorn its.main:app --reload
cd apps/web && npm run typecheck && npm run dev
```

Erwartet (manuell):
- Klick „Anders erklären"/„Hinweis"/„Wozu?" → eine `explanation` erscheint; MasteryBar-Wert und `grade.feedback` bleiben **unverändert**.
- Netzwerk-Tab: Request-Body enthält das jeweils korrekte `intent` und **kein** `answer`-Feld (bzw. leer).

Erwartet (optionaler Vitest-Test):
- Mock von `turn()`; Klick auf „Hinweis" ruft `turn` mit `intent:"hint"`; nach Auflösung ist die MasteryBar-Prop unverändert und keine `grade`-Komponente gerendert.

## Abhängigkeiten

- **FE-S2** (Session-Screen): liefert `TutorThread`, die MasteryBar-Verdrahtung und den State, in den die Helfer-Buttons eingebettet werden.

Nachgelagert (warten auf FE-S3):
- **TST-4** (E2E-Smoke, E12) deckt den vollständigen Schüler-Flow inkl. Helfer-Aktionen ab.

## Definition of Done

Projektweite DoD (`docs/00` Section 8), auf FE-S3 zugeschnitten:
- [ ] Akzeptanzkriterien dieses Tasks erfüllt (drei Intents, Pfadtrennung, `explanation`-Anzeige).
- [ ] Typecheck grün; optionaler Pfadtrennungs-Test grün.
- [ ] **P2 eingehalten:** generativer Pfad berührt weder Bewertung noch Mastery (im Review verifiziert).
- [ ] Keine PII in externen LLM-Prompts — entfällt im Frontend (Anonymisierung im Backend vor jedem externen Call).
- [ ] `uv`-only — entfällt für `apps/web`; kein `pip` im Python-Teil berührt.
- [ ] Zugehöriges GitHub-Issue FE-S3 geschlossen, E10-Epic-Checkliste aktualisiert.

