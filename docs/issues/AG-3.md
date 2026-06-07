## Ziel

Der LLM-Client und die Anonymisierungsschicht stehen: `llm/client.py::complete` scrubbt PII vor jedem externen Call und schaltet per Config zwischen lokalem und Frontier-Backend um; `llm/anonymize.py::scrub` entfernt Namen/Daten/E-Mails; `llm/prompts/` stellt die System-Prompts (z. B. `EXPLAIN_SYSTEM`) bereit. Dieser Task ist `safety-critical`.

## Kontext & Prinzipien

- **P4 (PII verlässt die Maschine nicht im Klartext):** Es geht um Minderjährige. `scrub` läuft in `complete()` **vor** jeder Backend-Verzweigung, sodass kein Pfad daran vorbeiführt. Defense-in-depth: dem LLM werden ohnehin nur IDs/Skill-Keys übergeben (siehe AG-2); `scrub` ist die zweite Verteidigungslinie für versehentlich durchgereichten Freitext.
- **P8 (Datenresidenz CH/EU):** Das Frontier-Backend darf in Produktion nur einen CH/EU-konformen Endpoint nutzen; alternativ läuft alles Identifizierende auf einem lokalen Modell (Qwen2.5 o. Ä.). Die Backend-Umschaltbarkeit (`settings.llm_backend`) ist genau dafür da.
- **P2 (kuratiert vs. generativ):** Der LLM-Client bedient nur den *generativen* Pfad (`explain`). Die System-Prompts dürfen keine endgültigen Bewertungen erzeugen — die kommen aus `assess`. Der `EXPLAIN_SYSTEM`-Ton ist altersgerecht, knapp, ermutigend.

## Zu erstellende/ändernde Dateien

- `apps/api/src/its/llm/anonymize.py` — `scrub(text)`.
- `apps/api/src/its/llm/client.py` — `complete(system, user)` + Backend-Implementierungen.
- `apps/api/src/its/llm/prompts/__init__.py` — `EXPLAIN_SYSTEM` u. a. Konstanten.
- `apps/api/src/its/llm/__init__.py` — Paket-Init (sofern noch nicht vorhanden).

## Schnittstellen & Signaturen

`apps/api/src/its/llm/anonymize.py`:

```python
import re

# Vor JEDEM externen Call anzuwenden. Defense-in-depth zusätzlich dazu:
# dem LLM werden ohnehin nur IDs/Skill-Keys übergeben, keine Namen.
_PATTERNS = [
    (re.compile(r"\b[A-ZÄÖÜ][a-zäöü]+\s[A-ZÄÖÜ][a-zäöü]+\b"), "[NAME]"),
    (re.compile(r"\b\d{2}\.\d{2}\.\d{4}\b"), "[DATE]"),
    (re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"), "[EMAIL]"),
]

def scrub(text: str) -> str:
    for pat, repl in _PATTERNS:
        text = pat.sub(repl, text)
    return text
```

`apps/api/src/its/llm/client.py`:

```python
from its.config import settings
from its.llm.anonymize import scrub

def complete(system: str, user: str) -> str:
    user = scrub(user)               # P4: PII raus, bevor irgendetwas die Maschine verlässt
    if settings.llm_backend == "frontier":
        return _complete_frontier(system, user)   # API-Call; user ist bereits gescrubbt
    return _complete_local(system, user)           # lokales Modell (Qwen2.5 o. Ä.)
```

Referenz Config (aus FND-4, damit der Body autark ist):

```python
class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    database_url: str
    data_mode: str = "mock"
    min_cohort_k: int = 10
    llm_backend: str = "local"          # local | frontier
    llm_api_key: str | None = None
    jwt_public_key: str | None = None

settings = Settings()  # type: ignore[call-arg]
```

`apps/api/src/its/llm/prompts/__init__.py`: Konstanten wie `EXPLAIN_SYSTEM` (Ton: altersgerecht, knapp, ermutigend; keine endgültigen Bewertungen — die kommen aus `assess`).

## Umsetzungsschritte

- [ ] `llm/__init__.py` und `llm/prompts/__init__.py` anlegen.
- [ ] `anonymize.py` mit `_PATTERNS` (Name/Datum/E-Mail) und `scrub(text)` (wendet alle Pattern in Reihe an).
- [ ] `client.py::complete(system, user)`: **zuerst** `user = scrub(user)`, dann Backend-Switch über `settings.llm_backend`.
- [ ] `_complete_local(system, user)` implementieren (lokales Modell, z. B. Qwen2.5) — oder klar markierter, lauffähiger Stub, der Eingaben nicht extern sendet.
- [ ] `_complete_frontier(system, user)` implementieren — API-Call gegen CH/EU-konformen Endpoint; `settings.llm_api_key` nutzen; `user` ist bereits gescrubbt.
- [ ] `EXPLAIN_SYSTEM` in `prompts/__init__.py` definieren (altersgerecht, knapp, ermutigend; **keine** korrekt/falsch-Urteile).
- [ ] Sicherstellen: kein Codepfad in `complete()` umgeht `scrub` (scrub vor der Verzweigung).

> Hinweis: zu entscheiden — konkretes lokales Modell (Qwen2.5-Variante/Grösse) und das Frontier-SDK/der Endpoint sind im Plan offen. Keine SDK-API erfinden; bis zur Entscheidung `_complete_frontier`/`_complete_local` als klar dokumentierte, nicht-leakende Stubs halten.
> Hinweis: zu entscheiden — welcher Frontier-Endpoint erfüllt P8 (CH/EU-Datenresidenz)? Bis geklärt, Default `llm_backend=local`.

## Akzeptanzkriterien

- [ ] Jeder externe Call läuft durch `scrub` (scrub steht vor der Backend-Verzweigung in `complete`).
- [ ] `scrub` ersetzt Vor-/Nachname-Muster, `dd.mm.yyyy`-Daten und E-Mail-Adressen.
- [ ] Backend per `settings.llm_backend` (`local` | `frontier`) umschaltbar.
- [ ] `EXPLAIN_SYSTEM` vorhanden; Ton altersgerecht/knapp/ermutigend; erzeugt keine endgültigen Bewertungen (P2).
- [ ] Dem LLM werden konzeptionell nur IDs/Skill-Keys gereicht (defense-in-depth dokumentiert).

## Tests / Verifikation

- [ ] `uv run pytest tests/test_anonymize.py -q` → `scrub("Sven Weidenmann, 14.03.2010, a@b.de")` ersetzt Name, Datum und E-Mail durch `[NAME]`/`[DATE]`/`[EMAIL]`.
- [ ] Backend-Switch (Unit, gemockt): bei `settings.llm_backend == "frontier"` wird `_complete_frontier` aufgerufen, sonst `_complete_local`; in beiden Fällen ist der `user`-Parameter bereits gescrubbt.
- [ ] `uv run python -c "from its.llm.prompts import EXPLAIN_SYSTEM; print(bool(EXPLAIN_SYSTEM))"` → `True`.

## Abhängigkeiten

- **FND-4** (`its/config.py`: `settings.llm_backend`, `settings.llm_api_key`) — der Client liest das Backend und den API-Key daraus.
- **Nachgelagert:** AG-2 (`explain_node` ruft `complete` und nutzt `EXPLAIN_SYSTEM`), CON-2/E5 (Ingestion nutzt den `llm`-Client zum Embedden — gleicher Anonymisierungs-/Backend-Pfad).

## Definition of Done

- [ ] Akzeptanzkriterien dieses Tasks erfüllt.
- [ ] Tests grün, inkl. `test_anonymize.py` (P4-Nachweis) — dieser Task ist `safety-critical`.
- [ ] Keine PII in externen LLM-Prompts: `scrub` läuft nachweislich vor jedem externen Call.
- [ ] `uv`-only, keine `pip`-Aufrufe.
- [ ] GitHub-Issue AG-3 geschlossen, E8-Epic-Checkliste aktualisiert.
