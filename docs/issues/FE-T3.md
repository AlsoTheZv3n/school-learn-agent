## Ziel

`InterventionControls.tsx` erlaubt der Lehrperson, für eine:n Schüler:in eine **Notiz** zu hinterlegen und optional die **Einschätzung zu überschreiben** (`override_mastery`). Nach dem Absenden ist die Notiz persistiert und wird auf der Schülerseite als dezenter Hinweis angezeigt.

## Kontext & Prinzipien

- **P6 (Mensch im Loop ist Sicherheitsarchitektur):** Die Eingreifen-Funktion ist ein erstklassiger Pfad, kein Reporting. Eine KI ist nicht die alleinige Instanz über den Lernweg eines Kindes — die Lehrperson kann das Modell überstimmen. Dass die Notiz **auf der Schülerseite sichtbar** wird, macht den Menschen-im-Loop für die:den Lernende:n sichtbar (Transparenz).
- **P3 (das Modell verbessert sich, nicht der Agent):** Der Override wirkt auf das inspizierbare Learner-Modell (`teacher_notes.override_mastery`), nicht auf das Verhalten des Agenten direkt — das Verhalten folgt dem Modell. Nach dem Schreiben ist das Backend die Wahrheit; die UI lädt den Stand neu, statt lokal zu mutieren.
- **P1 (Safety in der DB):** Das Schreiben läuft über eine `scoped_session`; RLS stellt sicher, dass eine Lehrperson nur für Schüler:innen der eigenen Klassen schreiben kann. Die UI verlässt sich darauf, statt selbst zu prüfen.

## Zu erstellende/ändernde Dateien

Gemäss Repository-Layout (`docs/00` Section 6, `apps/web/`):

- `apps/web/src/teacher/InterventionControls.tsx` — **neu:** Notiz-Formular + optionaler Mastery-Override.
- `apps/web/src/api/client.ts` — **ändern:** `addNote(...)` typisiert ergänzen (falls nicht aus FE-T1/FE-T2).
- `apps/web/src/teacher/LearnerModelPanel.tsx` — **ändern:** `InterventionControls` einhängen; nach Erfolg Panel-Refetch (überschriebener Wert sofort sichtbar).

## Schnittstellen & Signaturen

Backend-Endpoint (aus docs/08 §3, API-2):

```python
@router.post("/teacher/student/{student_id}/note")
def add_note(student_id: str, body: str, skill_id: str | None = None,
             override_mastery: float | None = None,
             principal: Principal = Depends(current_principal)):
    # Lehrer-Intervention (P6): Notiz + optionaler Mastery-Override.
    with scoped_session(principal) as s:
        s.execute(text("""
          INSERT INTO teacher_notes (student_id, teacher_id, skill_id, body, override_mastery)
          VALUES (:sid, :tid, :skid, :b, :ov)
        """).bindparams(sid=student_id, tid=principal.user_id, skid=skill_id,
                        b=body, ov=override_mastery))
    return {"status": "ok"}
```

Frontend-Form (aus docs/09 §3, mit ergänztem Client-Call):

```ts
// docs/09 §1 nennt addNote(student_id, body) als Teil von api/client.ts.
// docs/09 §3: InterventionControls -> addNote(student_id, body), optional override_mastery.
export const addNote = (
  studentId: string,
  payload: { body: string; skill_id?: string; override_mastery?: number },
  t: string,
) => post<{ status: string }>(`/teacher/student/${studentId}/note`, payload, t);
```

Die Schülerseite zeigt die Notiz an (aus docs/09 §2):

> Ist eine `teacher_note` über die:den Schüler:in vorhanden (vom Backend mitgeliefert), wird sie als dezenter Hinweis gezeigt („Notiz von …") — der Mensch-im-Loop ist für die:den Lernende:n sichtbar (P6).

> Hinweis: zu entscheiden — die Backend-Signatur deklariert `body: str` und die Override-Parameter als einzelne Funktionsargumente (FastAPI interpretiert `str`-Argumente ohne Pydantic-Modell als Query-Parameter, optionale als Query). Ob der Request als **JSON-Body** oder als **Query-Parameter** erwartet wird, ist verbindlich festzulegen (Empfehlung: ein Pydantic-Request-Modell im Backend, JSON-Body im Frontend). Bis dahin Client-Call an die tatsächliche API-2-Form anpassen.

> Hinweis: zu entscheiden — Override-Semantik: Verdrängt `override_mastery` den BKT-Wert dauerhaft, oder ist es ein paralleler, angezeigter Hinweis? Spiegelt `GET /teacher/student/{id}/mastery` den Override danach wider? Das bestimmt, ob der Panel-Refetch den neuen Wert zeigt.

## Umsetzungsschritte

- [ ] `addNote(studentId, payload, token)` in `api/client.ts` an die tatsächliche API-2-Request-Form anbinden (siehe Hinweis).
- [ ] `InterventionControls.tsx`: Formular mit Pflichtfeld `body` (Textarea), optionalem `skill_id` (aus dem im Panel gewählten Skill vorbefüllbar) und optionalem `override_mastery` (Zahl 0–1, validiert).
- [ ] Client-seitige Validierung: `body` nicht leer; `override_mastery` im Bereich [0, 1].
- [ ] Sichtbarer Hinweistext im UI: „Diese Notiz wird der:dem Schüler:in angezeigt" (Transparenz, P6).
- [ ] Submit → `addNote(...)`; Erfolgs-/Fehler-Feedback (`403`/`404`/`422` differenziert).
- [ ] Nach Erfolg: `LearnerModelPanel` neu laden (Refetch), damit ein Override sofort sichtbar ist — statt lokalem optimistischem Update (P3).
- [ ] `InterventionControls` in die Detailsicht/das Panel (FE-T2) einhängen; `student_id` aus der Route durchreichen.

## Akzeptanzkriterien

- [ ] `apps/web/src/teacher/InterventionControls.tsx` schreibt eine Notiz über `addNote(student_id, …)`.
- [ ] Optionaler Mastery-Override (`override_mastery`) kann gesetzt und mitgeschickt werden; ungültige Werte werden client-seitig abgefangen.
- [ ] Die hinterlegte Notiz erscheint anschliessend auf der Schülerseite (vom Backend mitgeliefert; sichtbar gemachte Intervention, P6).
- [ ] Fehlerfälle (`403` keine Berechtigung / `404` unbekannt / `422` Validierung) werden differenziert und neutral behandelt.

## Tests / Verifikation

- [ ] `cd apps/web && npm run build` (bzw. `npx tsc --noEmit`) → fehlerfrei.
- [ ] `npm run lint` → grün.
- [ ] Komponenten-/Verhaltenstest (sofern Runner aus FE-S1): leeres `body` blockiert den Submit; gültiger Submit ruft `addNote` mit korrektem Pfad/Payload; `override_mastery` ausserhalb [0,1] wird abgewiesen.
- [ ] Manueller Smoke gegen laufende API: `curl -X POST -H "Authorization: Bearer <teacher-token>" -H "Content-Type: application/json" $VITE_API_BASE/teacher/student/<id>/note -d '{"body":"Test","override_mastery":0.6}'` → `{"status":"ok"}`; danach erscheint die Notiz auf der Schülerseite (Schüler-Token, Session-Screen).
- [ ] Schreibversuch für eine:n fremde:n Schüler:in → Backend antwortet `403`/`404` (RLS); UI zeigt neutralen Fehler.

## Abhängigkeiten

- **FE-T2** — liefert das LearnerModelPanel mit der:dem ausgewählten Schüler:in/Skill, an das `InterventionControls` angedockt wird und das nach dem Override neu geladen wird.
- **API-2** — liefert `POST /teacher/student/{id}/note` (Notiz + Override) hinter `scoped_session`/RLS.
- **(Querbezug)** FE-S2/E10 — zeigt die geschriebene Notiz auf der Schülerseite an; das schliesst den P6-Transparenzkreis.
- **Nachgelagert:** schliesst die FE-T-Kette ab; trägt zum E2E-Smoke (TST-4) bei.

## Definition of Done

- [ ] Akzeptanzkriterien aus docs/09 §6 (FE-T3: „InterventionControls schreibt Notiz/Override; Lehrernotiz auf Schülerseite") erfüllt.
- [ ] Build/Typecheck und Lint grün; Komponententests grün. RLS-Schreibschutz bleibt Backend-erzwungen; die UI prüft nicht selbst die Klassenzugehörigkeit.
- [ ] Keine PII in externen LLM-Prompts (hier nicht betroffen — kein LLM-Call).
- [ ] `uv`-only-Regel im Frontend-Task nicht einschlägig; keine Toolchain-Bypässe.
- [ ] Zugehöriges GitHub-Issue (FE-T3) geschlossen, Epic-E11-Checkliste aktualisiert.
