## Ziel

Die Lehrperson öffnet `/teacher`, sieht ihre Klassen und die zugehörigen Schüler:innen und kann eine:n Schüler:in zur Detailsicht auswählen. Es erscheinen **ausschliesslich eigene Klassen** — erzwungen durch RLS im Backend, nicht durch Filterlogik im Frontend.

## Kontext & Prinzipien

- **P1 (Safety in der DB):** Der Dashboard-Code enthält bewusst **keine** „nur eigene Klassen"-Logik. Die Teacher-RLS-Policy (`teacher_*_in_class`) sorgt dafür, dass `GET /teacher/...` nur Schüler:innen der eigenen Klassen zurückgibt. Selbst eine fehlerhafte UI darf keine fremden Schüler:innen anzeigen. Deshalb: UI rendert, was das Backend liefert — nicht mehr.
- **P6 (Mensch im Loop):** Das Dashboard ist der Einstieg in den erstklassigen Verifizieren-/Eingreifen-Pfad, kein Admin-Nachgedanke. Die Shell muss eine saubere Navigation zur Detailsicht (LearnerModelPanel, FE-T2) bereitstellen.
- **P8 (Datenresidenz CH/EU):** Schülernamen sind PII Minderjähriger; das Frontend zeigt nur, was API-2 liefert, und schreibt keine Namen in Browser-Logs.

## Zu erstellende/ändernde Dateien

Gemäss Repository-Layout (`docs/00` Section 6, `apps/web/`):

- `apps/web/src/teacher/Dashboard.tsx` — **neu:** Klassen-/Schülerliste + Einstieg in die Detailsicht.
- `apps/web/src/api/client.ts` — **ändern:** Teacher-Calls ergänzen (`studentMastery`, ggf. `distribution`, `addNote`), falls FE-S1 nur Student-Calls enthielt.
- `apps/web/src/main.tsx` — **ändern:** Routen `/teacher` und `/teacher/student/:studentId` registrieren; Rollenweiche `teacher` aus dem Auth-Token.
- `apps/web/src/components/` — **neu/optional:** wiederverwendbare Loading-/Error-/Empty-States.

## Schnittstellen & Signaturen

`api/client.ts` (Auszug aus docs/09 §1) — Basis und Auth-Header sind bereits gesetzt:

```ts
const BASE = import.meta.env.VITE_API_BASE ?? "";

async function post<T>(path: string, body: unknown, token: string): Promise<T> {
  const r = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
    body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error(`${r.status}`);
  return r.json() as Promise<T>;
}
```

Teacher-Endpoints, gegen die das Dashboard navigiert (aus docs/08 §3, API-2):

```python
@router.get("/teacher/student/{student_id}/mastery", response_model=list[SkillMastery])
# RLS (teacher_*_in_class): nur Schüler:innen der eigenen Klassen sichtbar.

@router.get("/teacher/class/{class_id}/skill/{skill_id}/distribution", response_model=CohortStat)
# via enforce_min_cohort -> kleine Gruppen liefern 403.

@router.post("/teacher/student/{student_id}/note")  # body: str, skill_id?, override_mastery?
```

Auth-Principal (aus docs/02 §5), Quelle der Rolle für die Routing-Weiche:

```python
@dataclass(frozen=True)
class Principal:
    user_id: str
    role: Role               # STUDENT | TEACHER | ADMIN
    student_id: str | None = None
```

> Hinweis: zu entscheiden — API-2 spezifiziert **keinen** Endpoint für die Klassen-/Schülerliste selbst (kein `GET /teacher/classes` bzw. `GET /teacher/class/{id}/students`). Bis dieser Endpoint existiert, ist die Klassenliste ohne Datenquelle. Übergangslösung: Navigation/Detailsicht per direkt eingegebener/durchgereichter `student_id`. Endpoint in API-2 nachfordern.

## Umsetzungsschritte

- [ ] Route `/teacher` und `/teacher/student/:studentId` im Router (`main.tsx`) registrieren.
- [ ] Rollenweiche: bei Rolle `teacher` aus dem Auth-Token auf `/teacher` leiten (analog `/student`).
- [ ] `Dashboard.tsx` als Shell anlegen: Layout-Bereich für Klassenliste (links) und Schülerliste (rechts/darunter).
- [ ] Datenquelle für Klassen-/Schülerliste anbinden — sobald der Listen-Endpoint geklärt ist (siehe Hinweis); bis dahin Übergangslösung über `student_id`.
- [ ] Beim Auswählen einer:s Schüler:in auf die Detailsicht (`/teacher/student/:studentId`) navigieren, in der später `LearnerModelPanel` (FE-T2) eingehängt wird.
- [ ] `api/client.ts` um Teacher-Calls erweitern (`studentMastery`, `distribution`, `addNote`), falls noch nicht vorhanden; Token-Parameter durchreichen.
- [ ] Loading-/Error-/Empty-States: „keine Klassen" sauber rendern (kein leerer Bildschirm).
- [ ] Sicherstellen, dass **keinerlei** Client-seitige „eigene Klassen"-Filterung existiert (P1).

## Akzeptanzkriterien

- [ ] `apps/web/src/teacher/Dashboard.tsx` existiert und zeigt Klassen-/Schülerliste mit Einstieg in die Detailsicht.
- [ ] Es erscheinen ausschliesslich eigene Klassen, **ohne** Frontend-Filter (RLS-erzwungen) — die UI reicht nur durch, was das Backend liefert.
- [ ] Routing trennt `/student` und `/teacher`; die Rolle stammt aus dem Auth-Token.
- [ ] Auswahl einer:s Schüler:in führt zur Detailsicht (Vorbereitung für FE-T2).
- [ ] `api/client.ts` stellt typisierte Teacher-Calls bereit (mind. `studentMastery`).

## Tests / Verifikation

- [ ] `cd apps/web && npm run build` (bzw. `npx tsc --noEmit`) → fehlerfrei.
- [ ] `npm run lint` → grün.
- [ ] Manueller Smoke gegen laufende API: mit Teacher-Token `/teacher` öffnen → eigene Klassen/Schüler:innen erscheinen; mit einem Token ohne Klassenzuordnung erscheint die Empty-State, nicht fremde Daten.
- [ ] Gegenprobe Backend: `curl -H "Authorization: Bearer <teacher-token>" $VITE_API_BASE/teacher/student/<eigener-schueler>/mastery` liefert Zeilen; ein fremder `student_id` liefert `0` Zeilen bzw. `403`/`404` (RLS).

## Abhängigkeiten

- **FE-S1** — liefert das `apps/web`-Gerüst (Vite+React+TS), den typisierten `api/client.ts` und das getrennte student/teacher-Routing, auf dem diese Shell aufsetzt.
- **API-2** — liefert die RLS-gefilterten Teacher-Endpoints als Datenquelle.
- **Nachgelagert:** FE-T2 (braucht die Detailsicht-Navigation und die `student_id` aus dieser Shell) und FE-T3 (über FE-T2).

## Definition of Done

- [ ] Akzeptanzkriterien aus docs/09 §6 (FE-T1: „Dashboard zeigt nur eigene Klassen") erfüllt.
- [ ] Build/Typecheck und Lint grün; Komponententests (sofern Runner vorhanden) grün. RLS-Safety bleibt Backend-Sache und ist nicht durch Frontend-Filter umgangen.
- [ ] Keine PII in externen LLM-Prompts (hier nicht betroffen — kein LLM-Call).
- [ ] `uv`-only-Regel betrifft den Python-Teil nicht in diesem Task; im Frontend kein Bypass der Projekt-Toolchain.
- [ ] Zugehöriges GitHub-Issue (FE-T1) geschlossen, Epic-E11-Checkliste aktualisiert.
