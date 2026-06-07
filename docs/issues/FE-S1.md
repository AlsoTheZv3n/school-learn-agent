## Ziel

Lauffähiges React/TypeScript-Frontend-Gerüst unter `apps/web` (Vite), mit nach Rolle getrenntem Routing (`/student` und `/teacher`) und einem einzigen, typisierten API-Client (`api/client.ts`), der `fetch` inkl. Auth-Header und typisierter Antworten kapselt. Dies ist das gemeinsame Fundament für die Schüler-Session (E10) und das Lehrer-Dashboard (E11).

## Kontext & Prinzipien

- **P5 (Open Learner Model, Präsentations-Trennung):** Schon im Setup wird die Trennung `/student` vs. `/teacher` angelegt. Die Schülerseite darf später keine Unsicherheit zeigen, die Lehrerseite schon — das Routing macht diese „zwei Sichten auf eine Wahrheit" strukturell sichtbar.
- **P7 (genau eine Naht analog auf Frontend-Ebene):** Alle HTTP-Calls laufen über **eine** Stelle (`api/client.ts`). Kein wucherndes Adapter-Geflecht; der Übergang vom Auth-Stub zum echten IdP-Token wird so eine Einzeländerung.
- **P4/P8 (PII / Datenresidenz):** Der Client ruft ausschliesslich die eigene Backend-API (anonymisierung + LLM passieren serverseitig). Keine direkten externen LLM-Calls aus dem Browser; statische Assets später CH/EU.
- **P9 gilt hier NICHT** (nur Python-Teil); `apps/web` nutzt npm/Vite, nicht `uv`.

## Zu erstellende/ändernde Dateien

Gemäss Repository-Layout (`docs/00` Section 6: `apps/web/`) und `docs/09` Abschnitt 1:

```
apps/web/
├── package.json                 # neu (Vite-Scaffold)
├── tsconfig.json                # neu
├── vite.config.ts               # neu
├── index.html                   # neu
├── .env.example                 # neu: VITE_API_BASE=
└── src/
    ├── main.tsx                 # neu: Router-Setup /student + /teacher
    ├── api/
    │   └── client.ts            # neu: typisierte Calls turn(), myMastery()
    ├── components/              # leer/Platzhalter (geteilte UI-Bausteine)
    ├── student/                 # Verzeichnis anlegen (Inhalt in FE-S2/FE-S3)
    └── teacher/                 # Verzeichnis anlegen (Inhalt in E11)
```

> Hinweis: zu entscheiden — Lint/Test-Toolchain (eslint/Vitest) ist in den Docs nicht festgelegt. Mindest-Gate ist `tsc --noEmit`.

## Schnittstellen & Signaturen

`api/client.ts` exakt nach `docs/09-frontend.md` Abschnitt 1:

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

Zusätzlich der schonende Mastery-Call (passend zum Backend `GET /student/mastery`, `docs/08` Abschnitt 2 — Schülerseite zeigt nur `mastery`, nicht `uncertainty`):

```ts
// GET-Helper analog zu post(), mit Auth-Header.
export interface MySkillMastery {
  skill_id: string;
  name: string;
  mastery: number;   // NUR mastery nach aussen (P5) — uncertainty bleibt Lehrerseite
}
export const myMastery = (t: string) => /* GET /student/mastery */ Promise.resolve([] as MySkillMastery[]);
```

> Hinweis: zu entscheiden — Herkunft des `token`. FND-5 ist nur ein JWT-Stub; der echte IdP (Keycloak/Authentik/Entra) steht noch nicht fest. Token-Bezug an EINER Stelle kapseln und als TODO markieren, nicht erfinden.

Der Backend-Antworttyp (zur Konsistenz, `docs/08` Abschnitt 1):

```python
class TurnResponse(BaseModel):
    grade: GradeOut | None = None       # correct: bool, feedback: str, confidence: float
    mastery: float | None = None
    explanation: str | None = None
    route_reason: str | None = None
```

## Umsetzungsschritte

- [ ] In `apps/web` ein Vite-React-TS-Projekt scaffolden (`npm create vite@latest . -- --template react-ts`).
- [ ] `react-router-dom` hinzufügen; in `src/main.tsx` Routen `/student` und `/teacher` definieren (Rolle später aus dem Auth-Token).
- [ ] `src/api/client.ts` mit `post<T>`, `Intent`, `TurnResponse`, `turn()` exakt nach Doc-Auszug anlegen.
- [ ] `myMastery()`-GET-Helper ergänzen, der nur `mastery` (kein `uncertainty`) durchreicht.
- [ ] `VITE_API_BASE` über `import.meta.env` lesen; `.env.example` mit `VITE_API_BASE=` anlegen.
- [ ] Token-Bezug in einem kleinen Provider (z. B. `src/auth/token.ts`) kapseln, vorerst Stub mit klarer TODO-Markierung.
- [ ] Verzeichnisse `src/components/`, `src/student/`, `src/teacher/` anlegen (Inhalt folgt in FE-S2/FE-S3/E11).
- [ ] npm-Skripte sicherstellen: `dev`, `build`, `typecheck` (`tsc --noEmit`).
- [ ] Prüfen, dass `apps/web/node_modules`, `dist/` bereits durch die FND-1-`.gitignore` abgedeckt sind.

## Akzeptanzkriterien

- [ ] `apps/web` ist ein Vite + React + TS Projekt; `npm install` und `npm run build` laufen fehlerfrei (AK docs/09 §6: „`apps/web` mit Vite/TS").
- [ ] Getrenntes Routing `/student` und `/teacher` ist vorhanden (AK docs/09 §6: „getrenntes Routing student/teacher").
- [ ] `src/api/client.ts` exportiert `Intent`, `TurnResponse`, `turn()` (typisiert) und einen `myMastery()`-Helper, der **kein** `uncertainty` durchreicht (AK docs/09 §6: „typisierter `api/client.ts`").
- [ ] `tsc --noEmit` ist fehlerfrei.
- [ ] Auth-Token-Bezug ist an einer Stelle gekapselt und als TODO markiert.

## Tests / Verifikation

```bash
# in apps/web
npm install
npm run typecheck      # tsc --noEmit -> 0 Fehler
npm run build          # erzeugt dist/ ohne Fehler
npm run dev            # Vite-Dev-Server startet; / leitet auf /student bzw. /teacher
```

Erwartet: Build und Typecheck grün; Dev-Server liefert die Routen `/student` und `/teacher` aus (vorerst Platzhalter-Komponenten).

## Abhängigkeiten

- **FND-1** (Monorepo-Grundgerüst): liefert das `apps/web`-Verzeichnis und die Root-`.gitignore`, in das dieses Projekt scaffoldet.

Nachgelagert (warten auf FE-S1):
- **FE-S2** braucht das Projektgerüst + `api/client.ts`.
- **FE-T1** (E11) baut auf demselben Routing/Gerüst auf.

## Definition of Done

Projektweite DoD (`docs/00` Section 8), auf FE-S1 zugeschnitten:
- [ ] Akzeptanzkriterien dieses Tasks erfüllt (Setup, Routing, typisierter Client).
- [ ] Build + Typecheck grün (kein Safety-Test direkt betroffen; kein LLM-Pfad).
- [ ] Keine PII in externen LLM-Prompts — entfällt (Frontend ruft keine externen LLMs direkt).
- [ ] `uv`-only — entfällt für `apps/web` (npm/Vite); kein `pip` im Python-Teil verändert.
- [ ] Zugehöriges GitHub-Issue FE-S1 geschlossen, E10-Epic-Checkliste aktualisiert.

