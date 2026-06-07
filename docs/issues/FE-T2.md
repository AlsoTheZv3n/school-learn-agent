## Ziel

Für eine:n im Dashboard ausgewählte:n Schüler:in zeigt `LearnerModelPanel.tsx` pro Skill `mastery` **und** `uncertainty` (plus `attempts_count`), sodass die Lehrperson sieht, *warum* das System eine Einschätzung trifft und *wie verlässlich* sie ist. Eine optionale Verteilungsansicht ruft `distribution(class_id, skill_id)`; bei zu kleiner Kohorte (`403`) zeigt die UI „zu wenige Lernende für eine anonyme Auswertung" statt Zahlen.

## Kontext & Prinzipien

- **P5 (Open Learner Model):** Das ist der Kern dieses Tasks. Im Gegensatz zur Schülerseite (die nur `mastery` als ermutigendes Prozent zeigt) rendert die Lehrerseite die Unsicherheit explizit — als Unsicherheitsband oder „n Versuche"-Indikator. BKT ist interpretierbar gewählt, damit genau das sichtbar gemacht werden kann. `uncertainty` darf **niemals** in eine geteilte/Schüler-Komponente durchgereicht werden.
- **P1 (Safety in der DB) / Min-Cohort:** Die Verteilungsansicht aggregiert über eine Kohorte. Unterschreitet die Gruppe die Schwelle `k`, liefert das Backend `403` (neutral). Die UI macht daraus einen Datenschutz-Hinweis — Min-Cohort sichtbar gemacht, nicht ein generischer Fehler.
- **P3 (das Modell verbessert sich, nicht der Agent):** Das Panel zeigt eine inspizierbare Mastery-Schätzung pro Skill; es ist die Grundlage für die Intervention (FE-T3) und macht das Modell auditierbar.

## Zu erstellende/ändernde Dateien

Gemäss Repository-Layout (`docs/00` Section 6, `apps/web/`):

- `apps/web/src/teacher/LearnerModelPanel.tsx` — **neu:** Mastery inkl. Unsicherheit pro Skill + Verteilungsansicht.
- `apps/web/src/api/client.ts` — **ändern:** `studentMastery(studentId, token)` und `distribution(classId, skillId, token)` typisiert ergänzen (falls nicht aus FE-T1).
- `apps/web/src/teacher/Dashboard.tsx` — **ändern:** Panel in die Detailsicht (`/teacher/student/:studentId`) einhängen.
- `apps/web/src/components/` — **neu/optional:** `MinCohortNotice`-Hinweiskomponente; Unsicherheitsband-Darstellung.

## Schnittstellen & Signaturen

Pydantic-Schemas der Antwort (aus docs/08 §1 — als TypeScript-Typen spiegeln):

```python
class SkillMastery(BaseModel):
    skill_id: str
    name: str
    mastery: float
    uncertainty: float          # Open Learner Model (P5) — Lehrerseite zeigt das
    attempts_count: int

class CohortStat(BaseModel):
    n: int
    avg_mastery: float
```

Teacher-Endpoints (aus docs/08 §3, API-2):

```python
@router.get("/teacher/student/{student_id}/mastery", response_model=list[SkillMastery])
#   SELECT ls.skill_id, sk.name, ls.mastery, ls.uncertainty, ls.attempts_count ...
#   RLS (teacher_*_in_class): nur Schüler:innen der eigenen Klassen.

@router.get("/teacher/class/{class_id}/skill/{skill_id}/distribution", response_model=CohortStat)
#   via enforce_min_cohort -> n < k => 403 (neutral).
```

Vorgeschlagene TypeScript-Typen + Client-Calls (zu ergänzen in `api/client.ts`):

```ts
export interface SkillMastery {
  skill_id: string;
  name: string;
  mastery: number;       // 0..1
  uncertainty: number;   // nur Lehrerseite (P5)
  attempts_count: number;
}
export interface CohortStat { n: number; avg_mastery: number; }

export const studentMastery = (studentId: string, t: string) =>
  get<SkillMastery[]>(`/teacher/student/${studentId}/mastery`, t);

// distribution: 403 NICHT in einen generischen Fehler verwandeln, sondern als
// "Kohorte zu klein" signalisieren (z. B. eigener Typ/Ergebnisobjekt).
export const distribution = (classId: string, skillId: string, t: string) =>
  get<CohortStat>(`/teacher/class/${classId}/skill/${skillId}/distribution`, t);
```

> Hinweis: zu entscheiden — der Doc-Auszug in docs/09 §1 nennt nur `post<T>`. Ein `get<T>`-Helfer (mit Auth-Header und statuscode-bewusster Behandlung von `403`/`404`) ist analog zu ergänzen; die exakte Signatur kommt aus FE-S1.

> Hinweis: zu entscheiden — die Verteilungsansicht braucht eine `class_id`. Ohne den in FE-T1 offenen Klassenlisten-Endpoint ist `class_id` im Frontend nicht verfügbar. Bis dahin ist die Verteilungsansicht optional/hinter der Klassen-Auswahl gekapselt.

## Umsetzungsschritte

- [ ] TypeScript-Typen `SkillMastery` (mit `uncertainty`, `attempts_count`) und `CohortStat` in `api/client.ts` definieren — exakt gegen die API-2-Schemas.
- [ ] `studentMastery(studentId, token)` implementieren (`GET /teacher/student/{id}/mastery`).
- [ ] `LearnerModelPanel.tsx`: Liste aller Skills rendern; pro Zeile Mastery-Balken + Unsicherheitsband (z. B. `mastery ± uncertainty` als helleres Band) + „n Versuche"-Badge aus `attempts_count`.
- [ ] Sortierung „niedrigste Mastery zuerst" / „höchste Unsicherheit zuerst" für Dichte anbieten.
- [ ] `uncertainty` ausschliesslich in `teacher/`-Komponenten verwenden; nie an geteilte/Schüler-Komponenten weiterreichen (P5).
- [ ] Verteilungsansicht: `distribution(classId, skillId)` aufrufen; Erfolg → `n` + `avg_mastery` anzeigen.
- [ ] `403`-Pfad: `MinCohortNotice` rendern („zu wenige Lernende für eine anonyme Auswertung") statt Zahlen oder Error-Toast.
- [ ] Loading-/Error-States (z. B. `404` unbekannte:r Schüler:in) sauber behandeln.
- [ ] Panel in die Detailsicht aus FE-T1 einhängen (Datenfluss: `student_id` aus der Route).

## Akzeptanzkriterien

- [ ] `apps/web/src/teacher/LearnerModelPanel.tsx` zeigt pro Skill Mastery **inkl. Unsicherheit** (Band/„n Versuche"-Indikator) und macht „warum" sichtbar (P5).
- [ ] `uncertainty` erscheint **nur** auf der Lehrerseite, nie in Schüler-/geteilten Komponenten.
- [ ] Die Verteilungsansicht zeigt bei `403` (Min-Cohort) den Hinweis „zu wenige Lernende für eine anonyme Auswertung" statt Zahlen.
- [ ] Daten kommen ausschliesslich aus den RLS-gefilterten Teacher-Endpoints; kein Frontend-Filter auf Schülerzugehörigkeit.

## Tests / Verifikation

- [ ] `cd apps/web && npm run build` (bzw. `npx tsc --noEmit`) → fehlerfrei; Typen stimmen mit den API-2-Schemas überein.
- [ ] `npm run lint` → grün.
- [ ] Komponenten-/Verhaltenstest (sofern Runner aus FE-S1): bei `studentMastery`-Mock werden `mastery` und `uncertainty` gerendert; bei `403`-Mock der Verteilung erscheint der Min-Cohort-Hinweis (keine Zahlen).
- [ ] Manueller Smoke gegen laufende API: `curl -H "Authorization: Bearer <teacher-token>" $VITE_API_BASE/teacher/student/<id>/mastery` liefert Objekte **mit** `uncertainty`; im Panel sichtbar. Eine kleine Kohorte über `.../distribution` liefert `403` → UI zeigt Hinweis.

## Abhängigkeiten

- **FE-T1** — liefert die Dashboard-Shell und die Detailsicht-Navigation mit der `student_id`, in die dieses Panel eingehängt wird.
- **API-2** — liefert `GET /teacher/student/{id}/mastery` (inkl. `uncertainty`) und den `distribution`-Endpoint mit Min-Cohort-`403`.
- **Nachgelagert:** FE-T3 (greift auf die:den im Panel gewählte:n Schüler:in/Skill für die Intervention zu) und TST-4 (E2E-Smoke „Lehrer sieht Stand inkl. Unsicherheit" hängt explizit von FE-T2 + API-2 ab).

## Definition of Done

- [ ] Akzeptanzkriterien aus docs/09 §6 (FE-T2: „LearnerModelPanel zeigt Mastery inkl. Unsicherheit"; FE-T3-bezogen: Kohorten-`403` als Hinweis) erfüllt.
- [ ] Build/Typecheck und Lint grün; Komponententests grün. RLS/Min-Cohort bleiben Backend-erzwungen; das Frontend leakt keine Zahlen bei `403`.
- [ ] Keine PII in externen LLM-Prompts (hier nicht betroffen — kein LLM-Call).
- [ ] `uv`-only-Regel im Frontend-Task nicht einschlägig; keine Toolchain-Bypässe.
- [ ] Zugehöriges GitHub-Issue (FE-T2) geschlossen, Epic-E11-Checkliste aktualisiert.
