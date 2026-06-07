## Ziel

Ein kleiner, kuratierter Demo-Vault unter `content/math/` liefert valides Beispielmaterial — Prosa mit eingebettetem ` ```sql `-Sidecar-Block und mindestens einem `[[wikilink]]` — als Eingabe-Fixture für Parser (CON-1) und Pipeline (CON-2) und als Grundlage der späteren Retrieval-Demo (RET-2).

## Kontext & Prinzipien

- **P2 (Kuratierte Antworten):** Der Vault ist **kuratiertes** Domain-Material, nicht LLM-generiert. Genau diese Kuratierung ist es, die das System einem Kind zumutbar macht — das Material wird von Menschen verantwortet.
- **Retrieval-Qualität (Kernregel):** Die Demo-Notiz demonstriert die Prosa/Code-Trennung in der Praxis: ein erklärender Prosateil plus ein ` ```sql `-Block, der laut Kommentar „NICHT mit-embeddet" wird. Das Beispiel ist damit der Lackmustest für CON-1/CON-2.
- **P9 (`uv` ausschliesslich):** Keine Tooling-Auswirkung (reine Markdown-Dateien), aber Verifikation läuft über `uv run`.

> Hinweis: P1/RLS und P4/PII sind hier NICHT relevant — der Vault enthält ausschließlich geteiltes Lernmaterial, keine personenbezogenen Daten.

## Zu erstellende/ändernde Dateien

- `content/math/quadratic-equations.md` — die im Doc vorgegebene Demo-Notiz (Repo-Layout docs/00 §6: `content/ # kuratierter Markdown-Vault (Prosa + ```sql-Blöcke)`).
- `content/math/quadratic-formula.md` — eine zweite, verlinkte Notiz, damit der `[[quadratic-formula]]`-Link ein reales Ziel hat und CON-2 eine echte Kante anlegen kann.

## Schnittstellen & Signaturen

Exakter Inhalt aus docs/05 §6.3 für `content/math/quadratic-equations.md`:

````markdown
# Quadratische Ergänzung

Die quadratische Ergänzung formt ein Polynom in ein vollständiges Quadrat plus Restterm um.
Sie ist die Grundlage der quadratischen Lösungsformel. Verwandt: [[quadratic-formula]].

```sql
-- frische Detailzahl bei Bedarf (Sidecar, NICHT mit-embeddet)
SELECT avg(mastery) FROM learner_state ls
JOIN skills s ON s.id = ls.skill_id
WHERE s.key = 'complete-the-square';
```
````

Diese Notiz muss durch `parse_note` (CON-1) ohne Verlust laufen:
- `prose` = der Erklärungstext (ohne SQL),
- `sidecar_queries` = `["-- frische Detailzahl ... WHERE s.key = 'complete-the-square';"]`,
- `links` = `["quadratic-formula"]`.

## Umsetzungsschritte

- [ ] Verzeichnis `content/math/` sicherstellen (existiert laut docs/02 §1 bereits im Monorepo-Gerüst).
- [ ] `content/math/quadratic-equations.md` mit dem oben angegebenen Inhalt **exakt** anlegen (Prosa, ein ` ```sql `-Block, ein `[[quadratic-formula]]`-Link).
- [ ] `content/math/quadratic-formula.md` als zweite Notiz anlegen: kurze Prosa zur quadratischen Lösungsformel; optional ein eigener Sidecar-` ```sql `-Block; optional Rück-`[[quadratic-equations]]`.
- [ ] Frontmatter-/Pfadkonvention für `skill_key` dokumentieren (z. B. Dateiname = Skill-Key `quadratic-equations`), damit CON-2 `skill_id` auflösen kann.
- [ ] Markdown auf valide ` ```sql `-Zäune und korrekte `[[...]]`-Syntax prüfen.

> Hinweis: zu entscheiden — ob die `skill_key`-Zuordnung über YAML-Frontmatter (`---\nskill_key: quadratic-equations\n---`) oder über die Pfad-/Dateinamenskonvention erfolgt. Das ist eine CON-2-Entscheidung; CON-3 sollte die gewählte Konvention konsistent abbilden.

## Akzeptanzkriterien

- [ ] `content/math/quadratic-equations.md` existiert mit Prosa, genau einem ` ```sql `-Sidecar-Block und mindestens einem `[[wikilink]]` (docs/05 §7: „Demo-Vault vorhanden (CON-3)").
- [ ] Mindestens eine zweite Notiz existiert, sodass der `[[quadratic-formula]]`-Link ein reales Ziel hat.
- [ ] `parse_note` über die Demo-Notiz liefert nicht-leere `prose`, genau eine `sidecar_query` und `links == ["quadratic-formula"]`.

## Tests / Verifikation

```bash
cd apps/api
uv run python -c "from pathlib import Path; from its.content.parser import parse_note; p=parse_note(Path('../../content/math/quadratic-equations.md').read_text(encoding='utf-8')); print(len(p.prose)>0, p.links, len(p.sidecar_queries))"
```

Erwartete Ausgabe: `True ['quadratic-formula'] 1` — Prosa nicht leer, ein Link, eine Sidecar-Query. (Setzt voraus, dass CON-1 vorhanden ist; andernfalls rein statische Prüfung, dass die Dateien existieren und valides Markdown enthalten.)

## Abhängigkeiten

- **Keine** harte Abhängigkeit (kann zuerst oder parallel erstellt werden).
- **Nachgelagert:** **CON-1** und **CON-2** nutzen diese Dateien als Eingabe-Fixture; **RET-2** (Semantic-Demo) zeigt später Treffer aus genau diesem Material.

## Definition of Done

- [ ] Akzeptanzkriterien aus docs/05 §7 (CON-3) erfüllt.
- [ ] Tests/Verifikation grün (Parser-Durchlauf liefert erwartete Werte); Safety-Tests nicht betroffen.
- [ ] Keine PII enthalten — nur geteiltes Lernmaterial (P4 nicht betroffen).
- [ ] `uv`-only, keine `pip`-Aufrufe.
- [ ] Zugehöriges GitHub-Issue (CON-3) geschlossen, E5-Epic-Checkliste aktualisiert.
