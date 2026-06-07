# 09 — Frontend: Schüler & Lehrer (E10, E11, M4)

**Ziel:** Zwei sehr unterschiedliche Sichten über dieselben Daten — die **ruhige** Schüler-Session
(ein Konzept zur Zeit) und das **dichte** Lehrer-Dashboard (Open Learner Model + Intervention).

**Voraussetzungen:** API-1 (Student-Endpoints), API-2 (Teacher-Endpoints).
**Issues:** FE-S1 … FE-S3 (Schüler), FE-T1 … FE-T3 (Lehrer).

---

## 1. Projekt-Setup (FE-S1)

`apps/web` mit Vite + React + TypeScript. Routing trennt `/student` und `/teacher` (Rolle aus
dem Auth-Token). `api/client.ts` kapselt `fetch` inkl. Auth-Header und typisierter Antworten.

```
apps/web/src/
├── main.tsx
├── api/client.ts          # typisierte Calls: turn(), myMastery(), studentMastery(), distribution(), addNote()
├── components/            # geteilte UI-Bausteine
├── student/
│   ├── SessionScreen.tsx  # die Session-Hülle
│   ├── TutorThread.tsx    # Erklärung + Frage + Antwortfeld + Helfer-Aktionen
│   └── MasteryBar.tsx     # schonende %-Anzeige (NICHT die Rohschätzung)
└── teacher/
    ├── Dashboard.tsx
    ├── LearnerModelPanel.tsx   # Mastery inkl. Unsicherheit pro Skill
    └── InterventionControls.tsx
```

`api/client.ts` (Auszug):

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

---

## 2. Schüler-Session (FE-S2, FE-S3)

Designziel (wie im Mockup): **ein Konzept zur Zeit**, ruhig, ermutigend. Der Lernstand wird
**schonend** dargestellt — ein einzelner Fortschrittsbalken pro aktuellem Skill, nicht die
Rohschätzung mit Unsicherheit.

Komponenten:
- `MasteryBar.tsx`: nimmt `mastery` (0–1) → zeigt gerundetes Prozent + Balken. **Kein**
  `uncertainty`-Wert nach aussen (P5: das ist Lehrerseite).
- `TutorThread.tsx`: zeigt die Erklärung (Agent), die aktuelle Frage und ein Antwortfeld.
  - „Antwort absenden" → `turn({intent:"answer", answer, item_ref})` → zeigt `grade.feedback`
    und aktualisiert die `MasteryBar` aus `mastery`.
  - **Helfer-Aktionen (FE-S3)** rufen den **generativen** Pfad, klar getrennt vom Bewertungspfad:
    - „Anders erklären" → `turn({intent:"explain"})`
    - „Hinweis" → `turn({intent:"hint"})`
    - „Wozu?" → `turn({intent:"why"})`
- Lehrernotiz-Anzeige: ist eine `teacher_note` über die:den Schüler:in vorhanden (vom Backend
  mitgeliefert), wird sie als dezenter Hinweis gezeigt („Notiz von …") — der Mensch-im-Loop
  ist für die:den Lernende:n sichtbar (P6).

> Zustands-Hinweis: Antworten-Feedback und Mastery sind reaktiv (React-State). Keine
> Browser-Storage-Abhängigkeit nötig; der Stand kommt vom Backend.

---

## 3. Lehrer-Dashboard (FE-T1 … FE-T3)

Designziel: **Dichte** und Transparenz — das Gegenteil der Schülerseite.

- `Dashboard.tsx` (FE-T1): Klassenliste → Schülerliste; Einstieg in die Detailsicht. Nur die
  eigenen Klassen erscheinen (durch RLS erzwungen; die UI muss nichts filtern).
- `LearnerModelPanel.tsx` (FE-T2) — **Open Learner Model (P5):** zeigt pro Skill `mastery`
  **und** `uncertainty` (z. B. Balken + Unsicherheitsband oder „n Versuche"-Indikator), sodass
  die Lehrperson sieht, *warum* das System eine Einschätzung trifft und wie verlässlich sie ist.
- `InterventionControls.tsx` (FE-T3) — **Intervention (P6):** Notiz hinterlegen
  (`addNote(student_id, body)`), optional Mastery überschreiben (`override_mastery`). Diese
  Notiz erscheint anschliessend auf der Schülerseite.

Kohorten-Sicht: eine Verteilungsansicht ruft `distribution(class_id, skill_id)`; bei zu kleiner
Kohorte liefert das Backend `403` → die UI zeigt „zu wenige Lernende für eine anonyme Auswertung"
statt Zahlen (Min-Cohort sichtbar gemacht).

---

## 4. Die zentrale Designentscheidung: zwei Sichten, eine Wahrheit

Dieselbe `learner_state`-Zeile, zwei Präsentationen:

| | Schülerseite | Lehrerseite |
|---|---|---|
| `mastery` | als ermutigendes Prozent | als Wert |
| `uncertainty` | **nicht** gezeigt | gezeigt (Verlässlichkeit) |
| Ton | ruhig, ein Konzept | dicht, Übersicht |
| Aktion | lernen/antworten | verifizieren/eingreifen |

Das ist das Scoping-Prinzip, angewandt auf **Präsentation**, nicht nur auf Daten.

---

## 5. Altersabhängigkeit (wichtig, vor dem Bau klären)

Dieses Design zielt auf **Sekundarstufe** (textlastig, Tippfeld, selbstgesteuert). Für die
**Unterstufe** ist es ein anderer Screen: deutlich weniger Text, Tippen statt Tastatur, mehr
Scaffolding — und die Mastery-Anzeige für das Kind eher **verborgen** (nur Lehrer/Eltern), da
ein Prozentwert für ein 7-jähriges Kind eher entmutigt als motiviert. Diese Variante ist in
`FE-S2` als Konfigurationsfall vorzusehen, nicht als zweite Codebasis.

---

## 6. Akzeptanzkriterien (gesamt)

- [ ] `apps/web` mit Vite/TS; getrenntes Routing student/teacher; typisierter `api/client.ts` (FE-S1)
- [ ] `SessionScreen` zeigt ein Konzept; `MasteryBar` ohne Unsicherheit nach aussen (FE-S2)
- [ ] Helfer-Aktionen rufen den `explain`-Pfad, getrennt vom Bewertungspfad (FE-S3)
- [ ] Lehrernotiz wird auf Schülerseite angezeigt (FE-S2/FE-T3)
- [ ] `Dashboard` zeigt nur eigene Klassen (RLS) (FE-T1)
- [ ] `LearnerModelPanel` zeigt Mastery **inkl.** Unsicherheit (FE-T2)
- [ ] `InterventionControls` schreibt Notiz/Override; Kohorten-`403` als „zu wenige Lernende" (FE-T3)

---

## Claude-Code-Prompt

```
Setze E10 + E11 (docs/09-frontend.md) um: apps/web mit Vite+React+TS, getrenntes Routing
student/teacher, typisierter api/client.ts. Schülerseite: SessionScreen + TutorThread
(Antwort->turn(answer); Helfer-Buttons->turn(explain|hint|why)) + MasteryBar (gerundetes %,
KEINE Unsicherheit). Lehrer-Dashboard: Dashboard (nur eigene Klassen), LearnerModelPanel
(mastery + uncertainty), InterventionControls (addNote + override; Kohorten-403 als Hinweis).
Zeige Lehrernotizen auf der Schülerseite. Halte die Präsentations-Trennung (P5) ein und sieh
einen Unterstufen-Konfigurationsfall in MasteryBar vor. Schreibe einen E2E-Smoke (Login->Session
->Antwort->Mastery; Lehrer sieht Stand). Schliesse FE-S1..3 und FE-T1..3.
```
