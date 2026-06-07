# Offene Fragen, Entscheidungen & Risiken — konsolidiert

> Automatisch konsolidiert aus der Detailplanung (ein Planungs-Agent pro Epic, E1-E14).
> **89 offene Entscheidungen** und **102 Risiken**. Jeder Eintrag nennt den Grund und einen empfohlenen Default bzw. eine Gegenmassnahme.
>
> Diese Liste **ergaenzt** das Fundament (docs/00-11) und die Detailplanung (docs/planning/E*.md).
> Die Punkte sind **vor** der jeweiligen Umsetzung zu klaeren. Reihenfolge folgt den Epics/Milestones.

## Inhalt
- [Offene Fragen und Entscheidungen](#offene-fragen-und-entscheidungen)
- [Risiken und Gegenmassnahmen](#risiken-und-gegenmassnahmen)

## Offene Fragen und Entscheidungen

### E1 Foundations: Monorepo, Infra, Skeleton  _(7)_
1. **Welches Build-Backend wird für das src-Layout in apps/api/pyproject.toml verwendet (Hatchling vs. setuptools)? Das Doc enthält kein [build-system].**
   - *Warum:* Ohne korrekt konfiguriertes Build-Backend findet uv das Paket unter src/its nicht; `import its` bzw. `uvicorn its.main:app` schlägt fehl und blockiert FND-4/FND-6.
   - *Empfehlung:* Hatchling: [build-system] requires=["hatchling"], build-backend="hatchling.build" plus [tool.hatch.build.targets.wheel] packages=["src/its"]. Schlank, gut von uv unterstützt, explizites src-Mapping.
2. **Wird die Python-Version nur als Range (requires-python >=3.12) gehalten oder zusätzlich über .python-version gepinnt?**
   - *Warum:* Unterschiedliche 3.12.x/3.13-Minor-Versionen zwischen lokal und CI können subtile Abweichungen verursachen; reproduzierbare CI profitiert von einem Pin.
   - *Empfehlung:* `.python-version` mit 3.12 in apps/api anlegen und setup-uv darauf ausrichten, Range im pyproject als Untergrenze belassen.
3. **Welcher pytest-asyncio-Modus gilt (asyncio_mode="auto" vs. explizite @pytest.mark.asyncio)?**
   - *Warum:* Sobald async-Tests (z. B. httpx.AsyncClient gegen FastAPI) hinzukommen, entscheiden falsche Defaults über stille Test-Skips; das betrifft direkt die Aussagekraft der CI.
   - *Empfehlung:* [tool.pytest.ini_options] asyncio_mode="auto" in pyproject.toml setzen, damit async-Tests ohne Marker-Boilerplate laufen.
4. **Welcher IdP und welches JWT-Claims-Mapping wird FND-5 später konkretisieren (Keycloak/Authentik vs. Entra ID; welcher Claim trägt role, welcher student_id; Bezug von JWT_PUBLIC_KEY)?**
   - *Warum:* Der Stub wirft NotImplementedError; ohne festgelegtes Claims-Mapping kann current_principal nicht implementiert werden und die Brücke zu RLS (app.current_student_id/teacher_id) bleibt offen. Sicherheits- und Compliance-relevant (P1/P4).
   - *Empfehlung:* Keycloak (self-hostbar in CH/EU, P8); role aus realm_roles/resource_access, student_id aus einem Custom-Claim `student_id`; JWT_PUBLIC_KEY = JWKS/Realm-Public-Key zur Signaturprüfung. Als eigener Task außerhalb M0 spezifizieren.
5. **Wird apps/web/ in M0 als reiner .gitkeep-Platzhalter geführt oder schon mit Vite/React+TS initialisiert?**
   - *Warum:* docs/09 (Frontend) ist ein späteres Epic; ein verfrühtes Frontend-Bootstrapping erweitert den M0-Scope und die CI (node-Toolchain) unnötig.
   - *Empfehlung:* In M0 nur .gitkeep-Platzhalter; React+TS-Init im Frontend-Epic, damit M0 klein und auf Backend/Infra fokussiert bleibt.
6. **Findet pytest die Tests im Repo-Root tests/ trotz working-directory apps/api, oder müssen testpaths/rootdir konfiguriert werden?**
   - *Warum:* Der CI-Schritt läuft `uv run pytest` aus apps/api; liegen die Tests in ../../tests, sammelt pytest sie evtl. nicht ein und meldet fälschlich 'no tests collected' (Exit 5).
   - *Empfehlung:* [tool.pytest.ini_options] testpaths=["../../tests", "tests"] (oder Tests unter apps/api/tests/ spiegeln). Empfehlung: explizites testpaths setzen und im CI-Schritt verifizieren, dass >=1 Test gesammelt wird.
7. **Soll die CI bereits einen ruff-Lint-Schritt enthalten (uv run ruff check .)?**
   - *Warum:* ruff ist als Dev-Dependency vorhanden; ein früher Lint-Gate verhindert Stil-/Importfehler-Drift, ist aber nicht in den AK von docs/02 gefordert.
   - *Empfehlung:* Optionalen Schritt `uv run ruff check .` nach den Tests ergänzen; zunächst nicht merge-blockierend, später hochstufen.

### E2 Database: Schema & Migrationen  _(5)_
1. **Alembic im sync- oder async-Modus aufsetzen (uv run alembic init -t async vs. sync)?**
   - *Warum:* Bestimmt env.py, den Engine-Treiber (psycopg sync vs. async) und wie Tests/Migrationen ausgeführt werden. Eine spätere Umstellung berührt env.py und alle Migrationen; die Wahl muss vor DB-1 feststehen, weil DB-3 (scoped_session) im Doc synchron formuliert ist und die Safety-Tests (E3) synchron laufen.
   - *Empfehlung:* Sync für M1. Die scoped_session-Referenz in docs/03 §5 und die RLS-Tests in docs/04 §5 sind synchron; psycopg3-sync genügt für das erwartete Lastprofil. Async erst bei gemessenem Bedarf, dann als gezielte Migration der Session-/Engine-Schicht.
2. **Welche konkrete Embedding-Dimension ersetzt den Platzhalter vector(1024)?**
   - *Warum:* docs/03 §3 markiert 1024 explizit als anzupassen ('Dim an Modell anpassen'). Die Dimension hängt am noch nicht gewählten Embedding-Modell. Ist sie falsch, sind Spalte und HNSW-Index falsch dimensioniert und CON-2/RET-2 schlagen fehl bzw. erzwingen eine Schemamigration mit Re-Embedding aller Inhalte.
   - *Empfehlung:* Dimension als benannte Konstante EMBEDDING_DIM zentralisieren und vorerst bei 1024 belassen (kompatibel z. B. mit vielen multilingualen Modellen). Endgültige Festlegung gemeinsam mit der LLM-/Embedding-Entscheidung in E4/E5 treffen; CH/EU-Residenz (P8) bevorzugt ein lokal betreibbares Modell.
3. **Wird app.current_student_id (und später app.current_teacher_id) über SET ... = :param oder über set_config() gesetzt?**
   - *Warum:* Postgres substituiert in SET-Statements keine Bind-Parameter serverseitig; der Doc-Auszug 'SET app.current_student_id = :sid' könnte zur Laufzeit anders quotieren als erwartet und im schlimmsten Fall den Kontext nicht setzen — was RLS still aushebelt (fail-open statt fail-closed). Sicherheitskritisch (P1).
   - *Empfehlung:* set_config('app.current_student_id', :sid, false) mit gebundenem Parameter für den Kontext verwenden; für SET ROLE den Rollennamen ausschliesslich aus der PG_ROLE-Allowlist interpolieren (keine freien Eingaben). In den E3-Safety-Tests gegenprüfen, dass current_setting den erwarteten Wert liefert.
4. **Wird der teacher_id-Hook (app.current_teacher_id) bereits in DB-3 vorbereitet oder vollständig in SAF-1 (E3) ergänzt?**
   - *Warum:* docs/04 verlangt, dass scoped_session für TEACHER zusätzlich app.current_teacher_id setzt. Unklare Zuständigkeit kann dazu führen, dass Lehrer-Queries leer bleiben (Policy ohne Variable) oder dass DB-3 Code für noch nicht existierende Rollen enthält. Betrifft die Schnittstelle zwischen E2 und E3.
   - *Empfehlung:* DB-3 legt den Branch strukturell als no-op-Vorbereitung an (TODO-Kommentar + Stelle markiert), SAF-1 füllt ihn vollständig aus. So bleibt die Naht sichtbar, ohne in E2 E3-Rollen vorwegzunehmen.
5. **DB-4 als versionierte Daten-Migration oder als separates, manuell auszuführendes Seed-Skript?**
   - *Warum:* docs/03 §6 formuliert 'Daten-Migration/Seed' mehrdeutig. Eine Migration läuft automatisch bei upgrade head mit (deterministisch, mit downgrade), ein Skript ist flexibler, aber leicht zu vergessen. Beeinflusst, ob der Demo-Graph in CI/frischen Umgebungen ohne Zusatzschritt vorhanden ist.
   - *Empfehlung:* Als Daten-Migration 0002_seed_math_skills (idempotent via ON CONFLICT, mit downgrade). Stammdaten (Fächer/Skills) gehören versioniert ins Schema; Personendaten/Lernkurven bleiben dem Mock-Seeder (docs/11, E13) vorbehalten, strikt getrennt.

### E3 Safety & Isolation (RLS + Min-Cohort)  _(7)_
1. **Soll auf den geschuetzten Tabellen zusaetzlich FORCE ROW LEVEL SECURITY gesetzt werden?**
   - *Warum:* Postgres wendet RLS standardmaessig NICHT auf den Tabellen-Owner an. Falls der App-Login-User `its` zugleich Owner der Tabellen ist (was aus docs nicht eindeutig hervorgeht), waeren die Policies fuer ihn wirkungslos und die gesamte Isolationsgarantie (P1) liefe ins Leere — ein stilles Datenleck.
   - *Empfehlung:* Ja, FORCE ROW LEVEL SECURITY in rls.sql/SAF-1 setzen. Das schliesst Owner-Bypass aus; der Test test_unset_scope_returns_no_rows deckt einen Bruch zusaetzlich auf.
2. **Wer liefert tests/conftest.py mit den Fixtures db_factory und two_students fuer das Safety-Gate (SAF-4)?**
   - *Warum:* docs/04 setzt diese Fixtures voraus, docs/10 verortet sie aber in TST-1 (Epic E12). Wenn SAF-4 hart auf E12 wartet, kann das CI-Safety-Gate erst sehr spaet scharf geschaltet werden — entgegen dem Prinzip 'Safety zuerst' (P1).
   - *Empfehlung:* Minimale Fixtures (engine mit alembic upgrade head inkl. rls.sql, db, db_factory, two_students) mit SAF-4 mitliefern und spaeter in TST-1 konsolidieren, damit das Gate nicht blockiert ist.
3. **Migrationsstil: sync- oder async-Alembic-env.py, und welche Migrationsnummer fuer die RLS-Policies?**
   - *Warum:* docs/03 nennt beide Varianten ('uv run alembic init -t async ... bzw. sync'); SAF-1 muss rls.sql aus einer Migration ausfuehren. Die Wahl beeinflusst env.py, Test-Setup (conftest.engine ruft command.upgrade) und die Reihenfolge nach 0001_core_schema.
   - *Empfehlung:* Sync-env.py fuer M1 (einfacher, ausreichend; conftest.py in docs/10 nutzt synchrones command.upgrade). RLS-Migration als 0002_rls_policies nach 0001_core_schema.
4. **Fehlt in rls.sql ein GRANT SELECT ON classes fuer its_teacher?**
   - *Warum:* Die Teacher-Policies (teacher_attempts_in_class, teacher_state_in_class) joinen in ihrer USING-Subquery enrollments mit classes. Ohne Lesrecht auf classes koennte die Policy-Auswertung fehlschlagen oder leer bleiben, sodass Lehrer faelschlich keine eigenen Schueler sehen.
   - *Empfehlung:* GRANT SELECT ON classes TO its_teacher (und ggf. its_student, falls spaeter benoetigt) in rls.sql/SAF-1 ergaenzen.
5. **Wie wird die Lehrer-Session-Variable app.current_teacher_id gesetzt — ausschliesslich in scoped_session, oder auch ueber teacher_id_of im Resolver?**
   - *Warum:* docs/03 sagt scoped_session setzt sie; docs/04 §3 definiert teacher_id_of, das principal.user_id zurueckgibt. Unklare Verantwortlichkeit kann zu doppeltem oder vergessenem Setzen fuehren und damit zu falscher Lehrer-Sichtbarkeit.
   - *Empfehlung:* Ausschliesslich scoped_session setzt SET app.current_teacher_id (analog zur Schueler-Variable); teacher_id_of liefert nur den Wert fuer Query-Parameter, setzt keine Session-Variable.
6. **Soll der Min-Cohort-Schwellenwert k pro Klasse/Fach uebersteuerbar sein, oder bleibt er global?**
   - *Warum:* Aktuell global via settings.min_cohort_k (Default 10). Je nach Klassengroessen koennten kleine Klassen sonst dauerhaft keine Aggregate liefern; ein zu kleines k waere ein Datenschutzrisiko. Die Signatur erlaubt bereits einen optionalen k-Parameter.
   - *Empfehlung:* Vorerst global (k=10), optionaler Call-Site-k bleibt in der Signatur erhalten. Pro-Klasse-Konfiguration erst bei nachgewiesenem Bedarf einfuehren.
7. **Soll ein Meta-/Regressionstest sicherstellen, dass jede neue PII-Tabelle RLS aktiviert hat?**
   - *Warum:* Eine spaeter hinzukommende personenbezogene Tabelle ohne RLS-Policy wuerde still leaken. Reine Konvention ('neue PII-Tabelle = RLS in derselben Migration') ist fehleranfaellig.
   - *Empfehlung:* Optionalen Test ergaenzen, der pg_class.relrowsecurity = true fuer eine kuratierte Liste von PII-Tabellen (attempts, learner_state, teacher_notes, enrollments) prueft — guenstige zusaetzliche Absicherung.

### E4 Retrieval: Router + 3 Modi + Graph  _(6)_
1. **Welches konkrete Embedding-Modell und welche reale Vektordimension werden verwendet (das Schema nutzt den Platzhalter `vector(1024)`)?**
   - *Warum:* RET-2 (Semantic) sucht ueber `content_embeddings.embedding`; die Dimension muss zwischen Schema (DB), Ingestion (CON-2) und Query-Embedding exakt uebereinstimmen, sonst schlagen Inserts/Queries fehl. Die Wahl beeinflusst zudem Inferenz-Ort und damit P4/P8 (CH/EU-Residenz, kein PII-Leak).
   - *Empfehlung:* Ein lokal/EU-hostbares Modell waehlen (z. B. ein mehrsprachiges Embedding-Modell, das Deutsch gut abdeckt) und dessen native Dimension verbindlich ins Schema und in eine zentrale Settings-Konstante uebernehmen, statt 1024 hartzucodieren. Default: lokales Modell wegen P4/P8; Dimension projektweit aus einer Stelle ableiten.
2. **Wer berechnet das Query-Embedding fuer RET-2 — der LLM-Client aus docs/07 oder eine eigene Embedding-Funktion?**
   - *Warum:* `semantic_search` nimmt einen fertigen `query_embedding: list[float]` entgegen, berechnet ihn aber nicht. docs/07 spezifiziert nur `complete()` (Text-Completion), keine `embed()`-Funktion. Ohne klare Zustaendigkeit ist der SEMANTIC-Pfad im Agenten (AG-2) nicht verdrahtbar.
   - *Empfehlung:* Eine dedizierte `embed(text) -> list[float]`-Funktion im `llm`-Modul (gleicher Backend-Switch wie `complete`, lokal bevorzugt) einfuehren und in AG-2 vor `semantic_search` aufrufen. RET-2 bleibt embedding-agnostisch (nimmt den Vektor entgegen).
3. **Wie ist `load_item` / `content/items.py` (in docs/07 `agent/nodes/assess.py` referenziert) spezifiziert — Schema des `Item`, Herkunft des Answer-Keys, Bezug zu `attempts.item_ref`?**
   - *Warum:* RET-2 gibt `sidecar_query` und Chunks zurueck, aber der Bruecke zwischen Retrieval-Ergebnis und kuratiertem Item (`item_ref`) fehlt eine Spezifikation. `load_item`/`content/items.py` ist nirgends in den Docs definiert, ist aber der kuratierte Answer-Key-Pfad (P2). Das blockiert primaer E8, beeinflusst aber die Bedeutung von `item_ref`/`sidecar_query` in E4.
   - *Empfehlung:* `content/items.py` mit `Item(skill_key, prompt, answer_key)` (wie in docs/10 Grading-Tests verwendet) und `load_item(item_ref) -> Item` aus dem kuratierten Vault definieren, getrennt vom LLM (P2). `item_ref` als stabiler Pfad/Key in den Vault. Als eigener Task in E5/E8 fuehren, in E4 nur als bekannte Luecke vermerken.
4. **Soll RET-5 (Graph) auch Kanten mit `kind='related'` traversieren, oder ausschliesslich `prerequisite`?**
   - *Warum:* `skill_edges.kind` kennt `prerequisite` und `related`. docs/05 spezifiziert nur `prerequisites()` ueber `prerequisite`. Wenn das Dashboard/der Agent verwandte Skills empfehlen soll, fehlt eine Funktion — eine spaetere Nachruestung waere eine API-Aenderung.
   - *Empfehlung:* Vorerst nur `prerequisite` (exakt wie Doc). Eine analoge `related(skill_id)`-Funktion erst bei konkretem Bedarf aus E6/E8 ergaenzen; in E4 nur als Hinweis im Issue belassen.
5. **Wie ist die im Plan erwaehnte 'Soft-Cohort via Vektor-Aehnlichkeit (Lernende wie diese:r)' fuer RET-4 definiert?**
   - *Warum:* docs/05 erwaehnt Soft-Kohorten als Moeglichkeit, definiert sie aber nicht (Aehnlichkeitsmass, Schwelle, Bezugsvektor pro Schueler). Ohne Definition ist nur die harte `class_id`-Kohorte implementierbar; eine spaetere Soft-Cohort koennte neue De-Anonymisierungsflaechen oeffnen.
   - *Empfehlung:* Fuer E4 ausschliesslich die harte `class_id`-Kohorte implementieren. Soft-Kohorten als spaeteres, separat zu spezifizierendes Feature zuruekstellen — mit der nicht verhandelbaren Auflage, dass auch ihr Aggregat durch `enforce_min_cohort` laeuft.
6. **Erhaelt RET-3 (Individual) einen Lehrer-Zugriffspfad, oder bleibt der Lehrer-Blick auf einen Schueler ein separater Endpunkt in E9?**
   - *Warum:* `require_student_scope` deckt nur Schueler-Principals ab; RLS erlaubt Lehrern via `app.current_teacher_id` Lesezugriff auf Schueler ihrer Klassen. Ohne Klaerung ist unklar, wie ein Lehrer den Mastery-Stand eines einzelnen Schuelers im Open Learner Model (P5/P6) abruft.
   - *Empfehlung:* RET-3 strikt auf den Schueler-Selbstzugriff beschraenken (wie Doc). Den Lehrer-Blick auf einen einzelnen Schueler als eigenen, RLS-abgesicherten Endpunkt/Funktion in E9 (`api/teacher.py`) fuehren, der `teacher_id_of` + `app.current_teacher_id` nutzt.

### E5 Content-Ingestion (Markdown-Vault)  _(8)_
1. **Welche konkrete Embedding-Schnittstelle (Funktionsname, Modul, Backend-Verzweigung) nutzt CON-2? docs/07 spezifiziert nur complete(system,user), aber keine embed()-Funktion.**
   - *Warum:* CON-2 kann das Embedding ohne eine definierte Schnittstelle nicht aufrufen; ohne klare Naht (z. B. injizierbares embed_fn) lässt sich die Pipeline weder testen noch P8-konform umschalten.
   - *Empfehlung:* Eine its/llm/client.py::embed(text: str) -> list[float] einführen, die analog zu complete() per settings.llm_backend zwischen lokal und frontier wählt; CON-2 nimmt sie als injizierbaren Parameter embed_fn entgegen (für Tests mockbar).
2. **Welches Embedding-Modell und welche Vektordimension werden verwendet? Das Schema nutzt den Platzhalter vector(1024) mit Kommentar 'Dim an Modell anpassen'.**
   - *Warum:* Stimmt die Modell-Dimension nicht mit der Spalte überein, schlägt jeder content_embeddings-Insert fehl. Die Wahl bestimmt außerdem die Migration und (bei frontier) die Datenresidenz (P8).
   - *Empfehlung:* Lokales Modell als Default (P8/P4): z. B. ein mehrsprachiges Sentence-Transformer-Embedding (768 oder 1024 dim). Dimension verbindlich festlegen und die vector(N)-Spalte exakt darauf migrieren; Pipeline validiert die zurückgegebene Dimension.
3. **Wie wird content_notes.skill_id aufgelöst — über YAML-Frontmatter (skill_key) oder über eine Pfad-/Dateinamenskonvention?**
   - *Warum:* Ohne festgelegte Konvention bleibt skill_id oft NULL, wodurch Skill-bezogene Kanten und das spätere Mapping von Material auf Skills brechen.
   - *Empfehlung:* Pfad-/Dateinamenskonvention content/<subject>/<skill-key>.md als Primärquelle, optional durch ein YAML-Frontmatter-Feld skill_key überschreibbar; fehlende Skills werden geloggt, Notiz wird mit skill_id=NULL trotzdem angelegt.
4. **Wie werden [[wikilinks]] persistiert — als skill_edges (kind='related') oder als separate Notiz-Kanten-Tabelle? docs/00 erwähnt 'Notiz-Kanten', das Schema kennt aber nur skill_edges.**
   - *Warum:* RET-5 (Graph-Traversal) liest skill_edges; landen Notiz-Links woanders, sind sie für den Graph unsichtbar. Eine separate Tabelle wäre wiederum eine ungeplante Schemaänderung.
   - *Empfehlung:* Wikilinks zwischen skill-tragenden Notizen als skill_edges mit kind='related' persistieren (nur bei aufgelösten Endpunkten). Reine Notiz-zu-Notiz-Links ohne Skill-Bezug vorerst nur loggen, bis eine Notiz-Edge-Tabelle nötig wird.
5. **Wie chunkt die Pipeline die Prosa (Absatzgrenzen, Min/Max-Größe, Overlap, Überschriften-Behandlung)?**
   - *Warum:* Chunking bestimmt die Retrieval-Qualität direkt; zu große Chunks verwässern Treffer, zu kleine zerstückeln den Kontext.
   - *Empfehlung:* Start einfach: nach Leerzeilen/Absätzen splitten, leere Chunks verwerfen, kein Overlap. Min-Länge (z. B. > 20 Zeichen) als Filter. Verfeinerung erst bei gemessen schlechtem Retrieval.
6. **Wird sidecar_query an alle Chunks einer Notiz gehängt oder nur an den ersten? Das Doc sagt 'erste passende Query'.**
   - *Warum:* Mehrfach gespeicherte Sidecar-Queries blähen die Embedding-Tabelle auf und können bei der Eskalation doppelte Treffer liefern; nur am ersten Chunk verliert ggf. den Bezug, wenn ein anderer Chunk matched.
   - *Empfehlung:* sidecar_query an jeden Chunk derselben Notiz hängen (die erste passende Query der Notiz), damit jede Trefferzeile direkt die Eskalations-Query mitführt — Speicher ist günstig, RET-2 braucht keinen Zusatz-Join.
7. **Wie verhält sich die Re-Ingestion (Idempotenz) bei einer geänderten Datei — voller Rebuild oder Upsert über source_path?**
   - *Warum:* Ohne definierte Strategie entstehen bei jedem Lauf Duplikate in content_notes/content_embeddings, was Retrieval verfälscht.
   - *Empfehlung:* Upsert über source_path: bestehende Notiz finden, ihre content_embeddings (ON DELETE CASCADE) löschen und neu schreiben, Prosa/skill_id aktualisieren. Garantiert reproduzierbare, duplikatfreie Läufe.
8. **Über welche Postgres-Rolle/Session läuft die Ingestion (CLI-Entrypoint), da content_* keine RLS hat?**
   - *Warum:* Eine falsch gewählte Rolle könnte entweder zu restriktiv (Insert verweigert) oder unnötig privilegiert sein; der CLI-Pfad ist nicht der request-scoped scoped_session-Pfad.
   - *Empfehlung:* Eine dedizierte privilegierte/Owner-Rolle (z. B. its_admin oder ein Ingestion-Account) für content_*-Inserts verwenden — bewusst getrennt vom RLS-gebundenen Schüler-/Lehrer-Pfad, da Lernmaterial nicht personenbezogen ist.

### E6 Learner-Modell (BKT)  _(6)_
1. **Welcher konkrete numerische Referenzwert wird für den LM-1-Test 'bekannte Referenzwerte für eine kurze Sequenz' fixiert (z. B. der exakte Wert von mastery_after([True], BKTParams()))?**
   - *Warum:* docs/06 fordert den Test, nennt aber keine Zahl. Ohne fixierten Erwartungswert ist der Test entweder trivial (nur Range/Monotonie) oder es wird ein Wert geraten. Ein falsch geratener Referenzwert würde einen korrekten Algorithmus fälschlich als rot markieren.
   - *Empfehlung:* Den Wert einmalig mit den Default-BKTParams (p_init=0.2, p_learn=0.15, p_slip=0.10, p_guess=0.20) berechnen, als Kommentar dokumentieren und mit Toleranz 1e-9 (math.isclose) asserten — z. B. posterior(0.2, True, params) und mastery_after([True], params) als zwei fixierte Anker.
2. **Wie wird learner_state.updated_at beim UPDATE (nicht nur INSERT) aktualisiert?**
   - *Warum:* Das ORM-Modell in docs/03 hat nur server_default=func.now(), das ausschliesslich bei INSERT greift. Ohne onupdate bleibt updated_at beim Fortschreiben der Mastery stehen — das untergräbt das Open Learner Model (Lehrperson sieht veraltete Zeitstempel) und Audit (P3).
   - *Empfehlung:* Das Modell in DB-2 um mapped_column(..., onupdate=func.now()) erweitern (saubere, deklarative Lösung). Alternativ im Service state.updated_at explizit setzen; die deklarative Variante wird empfohlen, da sie auch andere Schreibpfade abdeckt.
3. **Sind BKT-Parameter (p_init/p_learn/p_slip/p_guess) global-default oder pro Skill kalibrierbar/persistiert?**
   - *Warum:* BKTParams ist aktuell ein globaler Default. In der Praxis variieren slip/guess stark pro Skill; ein globaler Default kann Mastery systematisch verzerren und damit Pädagogik und Lehrer-Einschätzung verfälschen.
   - *Empfehlung:* Für M3 globalen Default belassen (dünne Daten, kein Trainingskorpus — passt zur BKT-Begründung). Optionalen params-Parameter von record_attempt nutzen, um später pro Skill kalibrierte Werte (aus einer skill_params-Tabelle) einzuspeisen. Persistierung als späteres Issue vormerken, nicht in E6.
4. **Welche genaue Form hat der DKT-Stub (LM-3): formgleiche Funktion mit NotImplementedError oder reine Doku-Datei?**
   - *Warum:* docs/06 sagt nur 'interface-kompatibler Stub'. Die exakte Signatur (gleich wie record_attempt? eigenes predict-Interface?) ist unspezifiziert. Eine willkürlich erfundene Signatur erschwert den späteren Swap statt ihn vorzubereiten.
   - *Empfehlung:* Eine zu record_attempt formgleiche Funktion (gleiche Parameter, Rückgabe LearnerState), die NotImplementedError wirft — so greift ein späterer Swap an genau einer Aufrufstelle. Plus Modul-Docstring mit den zwei Aktivierungsbedingungen.
5. **Definiert E6 eine eigene Pytest-Fixture für (Student + Skill) zum Testen von record_attempt, oder wird auf docs/10 (conftest) gewartet?**
   - *Warum:* docs/10 definiert nur two_students und seeded_student_and_item (letztere für den Agent-Test, nicht 1:1 für Tracing). Ohne passende Fixture kann der LM-2-Integrationstest nicht gegen die echte RLS-DB laufen, und der Schreibpfad bliebe ungetestet.
   - *Empfehlung:* Eine kleine lokale Fixture seeded_student_and_skill in tests/test_tracing.py (oder ergänzend in conftest.py) anlegen, die einen Student und einen Skill via Admin/Owner-Pfad seedet — analog zu two_students aus docs/10 §2.
6. **Werden mastery/uncertainty defensiv auf [0,1] geklemmt?**
   - *Warum:* Die BKT-Mathematik kann durch Gleitkomma-Drift minimal über 1.0 oder unter 0.0 geraten. Ein Wert >1.0 in learner_state würde im Dashboard (Mastery-Bar) und in Schwellen-Entscheidungen (z. B. Konfidenz ≥ 0.9 im Agent) inkonsistent wirken.
   - *Empfehlung:* Kein hartes Clamping in der reinen LM-1-Mathematik (Property-Test deckt den Bereich ab), aber im Tracing-Service (LM-2) ein defensives max(0.0, min(1.0, ...)) beim Schreiben von mastery/uncertainty, dokumentiert als reine Sicherheitsmassnahme.

### E7 Grading-Strategy-Registry  _(6)_
1. **Wie wird ein kuratiertes Item (inkl. answer_key) zur Laufzeit geladen? docs/07 referenziert `its.content.items.load_item`, das nirgends spezifiziert ist.**
   - *Warum:* GR-* definiert nur die `Item`-Dataclass. Ohne klar definierte Quelle (Vault-Datei, DB-Tabelle, Sidecar-Metadatum) kann der Agent (assess_node) den kuratierten Key nicht beziehen — P2 (kuratiert statt LLM-halluziniert) hängt direkt daran.
   - *Empfehlung:* Items aus dem kuratierten Markdown-Vault/der DB laden (Modul `its.content.items` als Teil von E5/E8); E7 liefert nur die Dataclass und garantiert die Frozen-Immutabilität des Keys. `load_item` als eigene Aufgabe in E8 explizit aufnehmen.
2. **Soll der Math-Grader rein symbolisch-exakt prüfen oder auch numerische Toleranz unterstützen (z. B. 0.333 ≈ 1/3)?**
   - *Warum:* Symbolisch-exakte Prüfung lehnt mathematisch akzeptable Dezimalnäherungen ab und kann ein korrekt rechnendes Kind als falsch markieren (P2-Falsch-Negativ). Umgekehrt erzeugt zu grosse Toleranz Falsch-Positive.
   - *Empfehlung:* Default symbolisch-exakt wie im Doc (`sp.simplify(got - expected) == 0`). Optionalen Modus/eine Toleranz pro `Item` (z. B. Feld `tolerance`) erst einführen, wenn ein konkreter Aufgabentyp es erfordert — bis dahin nicht erfinden.
3. **Welcher konkrete subject_key-Wortschatz gilt ('math', 'language', 'history') und wie wird er mit TutorState.subject_key und der subjects-Tabelle (DB) konsistent gehalten?**
   - *Warum:* `get_grader(subject_key)` wirft `LookupError`, wenn der Agent einen Key nutzt, der nicht registriert ist. Inkonsistente Strings führen zu Laufzeit-Fehlern im Bewertungspfad.
   - *Empfehlung:* Genau die im Doc verwendeten Keys `"math"`, `"language"`, `"history"` als kanonisch festlegen und in einer zentralen Konstante/Enum spiegeln, gegen die sowohl `subjects.key` (DB) als auch `TutorState.subject_key` validiert werden.
4. **Registrierung über Import-Side-Effect in grading/__init__.py oder über eine explizite bootstrap_graders()-Funktion?**
   - *Warum:* Import-Side-Effects sind in Tests schwer zu isolieren und können je nach Importreihenfolge überraschen; eine explizite Funktion ist testbarer, weicht aber vom Doc ab.
   - *Empfehlung:* Doc-konform Import-Side-Effect in `grading/__init__.py` beibehalten (einfach, auffindbar), zusätzlich eine explizite `bootstrap_graders()`-Funktion bereitstellen, die `__init__` aufruft — so bleibt der Start-Pfad testbar.
5. **Welche LLM-Funktion/Signatur und welcher Confidence-Wert gelten für History-Vorschläge?**
   - *Warum:* History soll einen LLM-Vorschlag liefern (Rubric-gestützt) mit confidence < 1.0. Ohne festgelegte Schnittstelle (AG-3 `its.llm.client.complete`) und ohne definierten Confidence-Wert ist unklar, ob die Schwelle in update_model_node (>= 0.9) korrekt greift.
   - *Empfehlung:* History bleibt bis AG-3 ein Stub ohne externen Call und meldet einen festen Wert < 0.9 (z. B. 0.5). Nach AG-3: Aufruf ausschliesslich über `its.llm.client.complete` (scrub vorgeschaltet, P4); Confidence aus dem LLM-Vorschlag ableiten, aber strikt auf < 1.0 deckeln.
6. **Ist SympyfyError/eval-Verhalten von sympify ein Sicherheitsrisiko bei freier Schülereingabe, und soll stattdessen sp.parse_expr mit eingeschränktem local_dict/transformations verwendet werden?**
   - *Warum:* `sympify` kann Eingaben weitgehend evaluieren; bei minderjährigen Nutzern mit freier Texteingabe ist das eine Angriffsfläche (Ressourcenverbrauch, unerwartete Ausdrücke).
   - *Empfehlung:* Doc-konform `sympify` als Ausgangspunkt, aber mit Eingabelängen-Limit und Test gegen bösartige/überlange Eingaben; mittelfristig auf `sp.parse_expr` mit restriktivem `local_dict` und ohne implizite Funktionsaufrufe umstellen.

### E8 Agent-Loop (LangGraph)  _(7)_
1. **Wie ist content/items.py::load_item spezifiziert (Signatur, Datenquelle des kuratierten answer_key)?**
   - *Warum:* assess_node (AG-2) importiert load_item hart, aber weder Datei noch Signatur existieren irgendwo im Plan. Ohne Klärung lässt sich der zentrale kuratierte Bewertungspfad (P2) nicht final umsetzen, oder es entsteht eine erfundene API.
   - *Empfehlung:* Minimaler Loader load_item(item_ref: str) -> Item, der das kuratierte Item (skill_key, prompt, answer_key, rubric) aus einer items-Tabelle bzw. aus dem Vault-Frontmatter lädt; answer_key kommt ausschliesslich aus der Kuratierung, nie vom LLM. items-Tabelle in der DB bevorzugen (versionierbar, abfragbar).
2. **Erwartet die gepinnte langgraph-Version (>=0.2) Dataclass-State (wie im Doc) oder TypedDict/Dict-Patch-Nodes?**
   - *Warum:* docs/07 zeigt mutierende Dataclass-Nodes (def node(state)->state). Manche LangGraph-Versionen erwarten TypedDict-State und Dict-Patches als Rückgabe. Eine Fehlannahme bricht graph.invoke() und damit den gesamten Loop.
   - *Empfehlung:* Gegen die in pyproject.toml gepinnte Version implementieren und am Doc-Muster (Dataclass, mutieren+zurückgeben) festhalten; falls die Version Dict-State erzwingt, einen dünnen Adapter dokumentieren, statt eine API zu erfinden.
3. **Wie wird die request-scoped, RLS-gescopte Session in update_model_node injiziert?**
   - *Warum:* Das Doc öffnet eine freie SessionLocal() mit dem Kommentar 'in der Praxis request-scoped Session injizieren'. Eine ungescopte Session umgeht den RLS-Kontext (app.current_student_id) und verletzt P1 — eine fehlerhafte Query könnte fremde Zeilen berühren.
   - *Empfehlung:* Session per Closure in build_graph() oder über eine ContextVar injizieren, die innerhalb von scoped_session(principal) gesetzt ist. So läuft jeder Schreibvorgang RLS-gescopt; ein Schüler-Principal ohne student_id führt fail-closed zu PermissionError.
4. **Wie löst _skill_id den skill_key in eine skill_id (UUID) auf?**
   - *Warum:* update_model_node braucht skill_id für Attempt und record_attempt, hat aber nur skill_key. Die Auflösung ist nirgends spezifiziert; ein falscher Scope (skill_key nicht eindeutig ohne subject_id) kann auf das falsche Skill schreiben.
   - *Empfehlung:* _skill_id(skill_key, subject_key) -> UUID via SELECT id FROM skills WHERE key=:key AND subject_id=(SELECT id FROM subjects WHERE key=:subject); innerhalb derselben gescopten Session, mit eindeutigem (subject_id, key)-Constraint wie im DB-Schema.
5. **Welches konkrete LLM-Backend (lokales Modell + Frontier-SDK/Endpoint) wird genutzt, und welcher Endpoint erfüllt CH/EU-Datenresidenz (P8)?**
   - *Warum:* AG-3 ist safety-critical. Ohne konkrete Wahl bleiben _complete_frontier/_complete_local Stubs; ein nicht-EU-Frontier-Endpoint würde P8 (revDSG/DSGVO) verletzen.
   - *Empfehlung:* Default llm_backend=local mit einer Qwen2.5-Instruct-Variante (z. B. 7B) lokal; Frontier nur gegen einen CH/EU-Endpoint (z. B. Azure OpenAI Switzerland North). Entscheidung explizit dokumentieren, bevor frontier in Produktion aktiviert wird.
6. **Ist die Konfidenz-Schwelle 0.9 fix oder konfigurierbar (ggf. pro Fach)?**
   - *Warum:* Der Wert 0.9 steuert direkt P6 (was automatisch zementiert wird vs. Lehrer-Review). Hardcoding erschwert die fachspezifische Feinjustierung (Math 1.0 deterministisch vs. History < 1.0).
   - *Empfehlung:* Schwelle als settings.confidence_commit_threshold (Default 0.9) konfigurierbar machen; History-Grader liefert bewusst < 1.0, sodass offene Antworten nie ohne Lehrerbestätigung in learner_state landen.
7. **Welche konkreten Argumente erhalten semantic/individual/population in retrieve_node?**
   - *Warum:* docs/07 beschreibt retrieve_node nur als 'ruft je nach route den passenden Modus'. semantic_search braucht ein query_embedding, individual ein Principal, population class_id+skill_id — diese Beschaffung ist im Agent-Kontext unspezifiziert.
   - *Empfehlung:* retrieve_node mappt Mode->Aufruf: SEMANTIC nutzt ein über den llm-Client berechnetes query_embedding des skill_key/der Frage; INDIVIDUAL nutzt das Principal aus dem gescopten Session-Kontext; POPULATION braucht class_id (offen, woher) und läuft via enforce_min_cohort. class_id-Herkunft separat klären.

### E9 Backend-API (Student + Teacher)  _(7)_
1. **Wie wird die request-scoped DB-Session in die LangGraph-Agent-Nodes injiziert? Der update_model-Node in docs/07 öffnet ein eigenes SessionLocal() ohne Rollen-/student_id-Kontext, während POST /student/turn bereits scoped_session(principal) öffnet.**
   - *Warum:* Sicherheitskritisch (P1): Schreibt der Node über eine ungescopte Session, umgeht er RLS — ein attempt/learner_state könnte unter falschem Kontext geschrieben werden. Zudem laufen zwei Sessions/Transaktionen pro Turn auseinander.
   - *Empfehlung:* Die scoped_session in den Graph-Kontext geben (LangGraph 'configurable'/contextvar) und im update_model-Node statt eines neuen SessionLocal() diese Session verwenden. Mit dem AG-Owner abstimmen, da es AG-2 berührt.
2. **Gibt _graph.invoke(state) die TutorState-Dataclass oder ein dict zurück?**
   - *Warum:* Der Doc-Code nutzt result.grade/result.mastery (Attributzugriff). LangGraph serialisiert den State häufig zu einem dict, dann schlägt der Attributzugriff fehl und /student/turn bricht zur Laufzeit.
   - *Empfehlung:* An der AG-1-Implementierung verifizieren; falls dict, im API-Code result['grade'] verwenden oder den State explizit re-instanziieren (TutorState(**result)). Nicht raten.
3. **load_item / content/items.py (in docs/07 assess_node referenziert) ist nirgends spezifiziert. Woher kommt das kuratierte Item inkl. answer_key?**
   - *Warum:* Ein ANSWER-Turn (intent=answer) ruft load_item(item_ref). Ohne diese Funktion lässt sich der Bewertungspfad — und damit der API-1-ANSWER-Integrationstest — nicht ausführen.
   - *Empfehlung:* Vor dem API-1-ANSWER-Test als eigenes (AG-2/Content-)Issue klären: content/items.py mit load_item(item_ref) -> Item, das Items aus dem kuratierten Vault/DB lädt. API-1 zunächst mit intent=explain testen, ANSWER nachziehen.
4. **Soll der Schüler-Endpoint GET /student/mastery uncertainty gar nicht erst serialisieren (eigenes StudentSkillMastery-Schema ohne uncertainty) oder sich auf UI-Disziplin verlassen?**
   - *Warum:* P5: Die Unsicherheit gehört der Lehrerseite. Liefert das Schüler-API die Rohunsicherheit mit, ist sie über die Netzwerk-Response abgreifbar, auch wenn die UI sie nicht zeigt.
   - *Empfehlung:* Eigenes schlankes StudentSkillMastery-Schema (skill_id, name, mastery, attempts_count) ohne uncertainty — Defense-in-depth, nicht auf Frontend-Disziplin verlassen.
5. **Welche Form hat der Body von POST /teacher/student/{id}/note — loses Query-Param body (wie im Doc) oder ein Pydantic-NoteIn-Schema?**
   - *Warum:* Notiz-Freitext über Minderjährige als Query-Param landet in der URL und damit in Server-/Proxy-Logs (PII-Leak, P4). Zudem ist override_mastery unvalidiert.
   - *Empfehlung:* Pydantic-NoteIn { body: str, skill_id: str | None, override_mastery: float | None (0..1) } als Request-Body; override_mastery per Field(ge=0, le=1) validieren.
6. **Woher kommt das JWT im Frontend und wie mappen die Claims auf Principal (user_id, role, student_id)? current_principal ist noch ein FND-5-Stub.**
   - *Warum:* E9 definiert den HTTP-Vertrag, von dem E10/E11 abhängen. Ohne festgelegtes Claims-Mapping ist unklar, wie student_id (für RLS) und teacher_id zustande kommen.
   - *Empfehlung:* IdP-Wahl gemäss docs/00 §5 (Keycloak/Authentik o. Entra ID) treffen; Mapping: sub->user_id, realm/role-Claim->role, eigener Claim student_id für Schüler. Bis FND-5 fertig ist, in Tests via dependency_overrides setzen.
7. **Wird student_id im Teacher-Pfad als Pydantic-UUID-Path-Param validiert oder als str gebunden und in der Query gecastet?**
   - *Warum:* Ein ungültiger oder nicht-UUID student_id kann je nach Bindung zu einem 500 (DB-Cast-Fehler) statt 404/422 führen; das Verhalten sollte konsistent zum Fehlermodell (API-3) sein.
   - *Empfehlung:* student_id/class_id/skill_id als Pydantic-UUID im Pfad deklarieren -> ungültige Werte ergeben automatisch 422; in der Query als str(uuid) binden.

### E10 Frontend: Schueler-Session  _(6)_
1. **Woher bezieht das Frontend den Auth-Token (Bearer) für api/client.ts?**
   - *Warum:* api/client.ts erwartet einen token: string, aber FND-5 liefert nur einen JWT-Stub und der IdP (Keycloak/Authentik/Entra) ist nicht festgelegt. Ohne klare Token-Herkunft ist der Login-Flow undefiniert und FE-S2 lässt sich nicht gegen echte, RLS-gescopte Endpoints betreiben.
   - *Empfehlung:* Token-Bezug hinter einem dünnen auth/token.ts-Provider kapseln (vorerst Stub), der später einen OIDC-Flow (Authorization Code + PKCE) gegen den gewählten IdP liefert; der Token-Claim trägt role und student_id, exakt die Felder, auf die RLS keyt.
2. **Wie gelangt die teacher_note auf die Schülerseite?**
   - *Warum:* docs/09 verlangt die Anzeige einer Lehrernotiz auf der Schülerseite (P6), aber weder TurnResponse noch GET /student/mastery (docs/08) enthalten ein teacher_note-Feld. Ohne definierten Lieferweg lässt sich die AK 'Lehrernotiz wird auf Schülerseite angezeigt' nicht erfüllen, ohne ein Schema zu erfinden.
   - *Empfehlung:* TurnResponse (E9/API-3) um optionales teacher_note?: { author: string; body: string } erweitern, befüllt aus teacher_notes der scoped_session; das Frontend rendert es defensiv nur, wenn vorhanden.
3. **Woher kommt die aktuelle Frage und ihr item_ref für den Antwortpfad?**
   - *Warum:* item_ref ist in docs/08/09 nur ein Request-Feld; es ist nicht spezifiziert, wie das Frontend die anzuzeigende Frage und das zugehörige item_ref erhält. Ohne das kann TutorThread keine Frage anzeigen und keinen korrekten answer-Turn bilden.
   - *Empfehlung:* TurnResponse um die nächste Frage (Text) und item_ref erweitern, oder einen intent:"next"-Aufruf definieren, der Frage + item_ref liefert; bis dahin in FE-S2 als TODO markieren statt erfinden.
4. **Woher stammt der Unterstufen-/Sekundarstufen-Schalter (ageBand)?**
   - *Warum:* docs/09 §5 verlangt einen Konfigurationsfall (Unterstufe: weniger Text, Mastery verborgen). Quelle des Schalters (Token-Claim, Profil-Endpoint, Routing) ist offen; falsche Voreinstellung könnte einem 7-Jährigen einen entmutigenden Prozentwert zeigen.
   - *Empfehlung:* ageBand als Prop in SessionScreen durchreichen, Quelle vorerst ein Token-Claim (Stub) bzw. ein späteres Schülerprofil-Feld; Default 'secondary' nur, wenn die Stufe sicher bekannt ist, sonst Mastery verbergen.
5. **VITE_API_BASE-Default und CORS bei getrenntem API-Host?**
   - *Warum:* Default ist leerer String (gleicher Origin). Wird die API in einer eigenen CH/EU-Region/Host betrieben (P8), braucht es eine gesetzte Base-URL plus CORS-Freigabe am Backend, sonst schlagen alle Calls fehl.
   - *Empfehlung:* In apps/web/.env.example einen dokumentierten VITE_API_BASE-Default führen; CORS-Bedarf an E9 melden und Web-Assets in derselben CH/EU-Region ausliefern.
6. **Welche Test-/Lint-Toolchain gilt für apps/web?**
   - *Warum:* Die Docs nennen für das Frontend keine konkreten Test-Tools (Playwright erst in TST-4/E12). Ohne festgelegtes Mindest-Gate bleibt die Qualitätssicherung für E10 unklar.
   - *Empfehlung:* tsc --noEmit als verpflichtendes CI-Gate; Vitest optional für MasteryBar (P5) und Pfadtrennung (P2); Playwright-E2E in TST-4/E12 belassen.

### E11 Frontend: Lehrer-Dashboard  _(5)_
1. **Über welchen Endpoint bezieht das Dashboard (FE-T1) die Klassen- und Schülerliste? API-2 (docs/08 §3) spezifiziert nur student_mastery, distribution und add_note — keinen GET /teacher/classes bzw. GET /teacher/class/{id}/students.**
   - *Warum:* Ohne Listen-Endpoint hat die Dashboard-Shell keine Datenquelle für die Klassen-/Schülerauswahl, und die distribution-Ansicht (FE-T2) hat keine class_id. Das blockiert FE-T1/FE-T2 funktional.
   - *Empfehlung:* In API-2 zwei RLS-gefilterte Endpoints nachziehen: GET /teacher/classes (-> Klassen der Lehrperson) und GET /teacher/class/{class_id}/students (-> Schüler:innen der Klasse). Bis dahin Übergangslösung: Navigation per direkt durchgereichter student_id.
2. **Woher stammt das Auth-Token im Frontend und wie werden Rolle und user_id aus den Claims gemappt? FND-5 (docs/02 §5) ist ein Stub (current_principal wirft NotImplementedError).**
   - *Warum:* Das Routing (student/teacher) und jeder Teacher-Call brauchen ein gültiges Token mit Rolle. Ohne definierten Flow/Claims-Mapping ist das Dashboard nicht real testbar und nicht produktionsreif.
   - *Empfehlung:* IdP (Keycloak/Authentik oder Entra ID, docs/00 §5) mit OIDC-Redirect; Rolle aus einem realm-/app-spezifischen Claim (z. B. roles oder ein dediziertes role-Claim) auf Role.{STUDENT,TEACHER,ADMIN} mappen, user_id aus sub. Für lokale Entwicklung ein kurzlebiges Devtoken, das client.ts als Parameter erhält.
3. **Wird der Request für POST /teacher/student/{id}/note als JSON-Body oder als Query-Parameter erwartet? Die Backend-Signatur deklariert body: str sowie skill_id/override_mastery als einzelne Funktionsargumente (FastAPI behandelt diese ohne Pydantic-Modell als Query-Parameter).**
   - *Warum:* Der Frontend-Client (addNote) muss exakt zur Backend-Erwartung passen, sonst 422. Der docs/09-Auszug addNote(student_id, body) ist mehrdeutig gegenüber der docs/08-Signatur.
   - *Empfehlung:* Im Backend ein Pydantic-Request-Modell NoteRequest {body: str; skill_id?: str; override_mastery?: float} einführen und im Frontend als JSON-Body senden — konsistent mit dem übrigen API-Stil und client.post<T>.
4. **Welche Semantik hat override_mastery? Verdrängt es den BKT-Wert dauerhaft oder ist es ein paralleler, angezeigter Hinweis — und spiegelt GET /teacher/student/{id}/mastery den Override anschliessend wider?**
   - *Warum:* Bestimmt, ob das LearnerModelPanel nach einem Override per Refetch den neuen Wert zeigt, und ob der Agent (P3) dem überschriebenen oder dem BKT-Wert folgt. Falsche Annahme führt zu inkonsistenter Anzeige.
   - *Empfehlung:* override_mastery in teacher_notes als auditierbarer, vorrangiger Wert speichern; der mastery-Read-Pfad (und der Agent) priorisiert einen vorhandenen, jüngsten Override über den BKT-Wert; das Panel zeigt sowohl BKT-Schätzung als auch den Override-Marker.
5. **Wie wird die teacher_note an die Schülerseite geliefert (für die Anzeige in FE-S2)? In docs/09 §2 heisst es nur 'vom Backend mitgeliefert', aber kein konkreter Feld-/Endpoint-Vertrag existiert.**
   - *Warum:* FE-T3 verlangt, dass die Notiz auf der Schülerseite erscheint (AK + P6-Transparenz). Ohne definierten Liefermechanismus ist das AK nicht verifizierbar und der P6-Kreis nicht geschlossen.
   - *Empfehlung:* Die TurnResponse (oder GET /student/mastery) um ein optionales Feld teacher_note: {body, from} erweitern, das die jüngste relevante Notiz für die:den eingeloggte:n Schüler:in (RLS-gescoped) mitliefert; FE-S2 rendert es als dezenten Hinweis.

### E12 Testing & CI  _(6)_
1. **Wie werden kuratierte Items mit answer_key geladen? Die Fixture seeded_student_and_item (docs/10 §5) und die Funktion load_item / das Modul content/items.py (von assess_node in docs/07 §3 benutzt) sind nirgends spezifiziert.**
   - *Warum:* Ohne sie kann der Agent-Integrationstest (TST-3) nicht laufen — assess_node ruft load_item(item_ref) und braucht einen kuratierten answer_key. Auch TST-4 (E2E) braucht ein bewertbares Item. Das ist die zentrale Lücke für die Integrations-/E2E-Ebene.
   - *Empfehlung:* content/items.py mit load_item(item_ref) -> Item definieren, das Items aus dem kuratierten Vault/einer items-Tabelle lädt. Für die Tests zunächst eine Inline-Fixture (oder monkeypatch) mit item_ref='expand-1', answer_key='x**2 + 2*x + 1', subject='math' nutzen, bis content/items.py final spezifiziert ist.
2. **Wie erhält update_model_node die request-scoped Session? Der Doc-Stub (docs/07 §3) öffnet ein eigenes SessionLocal() mit dem Kommentar 'in der Praxis: die request-scoped Session injizieren'.**
   - *Warum:* Im Test läuft der Turn in db_factory.as_student(...) (eigene Session mit RLS-Kontext). Öffnet der Node ein zweites SessionLocal(), fehlt der RLS-Kontext (kein SET app.current_student_id) und der Schreibpfad könnte fail-closed 0 Zeilen sehen oder gegen die Isolation arbeiten. Direkter Blocker für TST-3.
   - *Empfehlung:* Die Session als Abhängigkeit in den Graph-State/Node injizieren (z. B. über einen contextvar oder ein in build_graph übergebenes Session-Factory-Argument), sodass derselbe RLS-Kontext gilt. Im Test die db_factory.as_student-Session injizieren.
3. **Wie werden Auth-Token im HTTP-E2E-Smoke beschafft? current_principal ist in FND-5 ein Stub, der NotImplementedError wirft.**
   - *Warum:* Ohne testbare Auth kann der HTTP-Smoke (TST-4) keine Schüler-/Lehrer-Requests absetzen. Betrifft auch die Konkretheit des Auth-Flows insgesamt (JWT/IdP, Claims-Mapping auf Role + student_id).
   - *Empfehlung:* FastAPI dependency_overrides für current_principal mit Test-Principals (Schüler mit student_id, Lehrer mit user_id) im E2E nutzen. Parallel den realen Pfad als Test-JWT gegen settings.jwt_public_key vorbereiten, sobald FND-5 echtes JWT-Decoding implementiert.
4. **Alembic sync oder async (env.py)? docs/03 §6 lässt beides offen ('uv run alembic init -t async ... bzw. sync').**
   - *Warum:* Die engine-Fixture ruft command.upgrade(cfg, 'head') synchron. Eine async-env.py erfordert anderes Setup und kann im Testlauf nicht-deterministisch oder fehlerhaft sein. Betrifft TST-1 direkt.
   - *Empfehlung:* Sync-Alembic für Migrationen und Tests verwenden (einfachere, deterministische command.upgrade-Nutzung in der engine-Fixture). Async nur einführen, wenn ein gemessener Bedarf besteht.
5. **Welche Commit/Rollback-Isolationsstrategie gilt für TST-3, dessen Schreibpfad commit() aufruft?**
   - *Warum:* Die db-Fixture (TST-1) basiert auf Rollback der äusseren Transaktion. Ein commit() in update_model_node innerhalb dieser Transaktion bricht die Isolation oder hinterlässt Reststände für Folgetests.
   - *Empfehlung:* TST-3 nicht über die db-Rollback-Fixture, sondern über db_factory.as_student(...) mit eigener Session laufen lassen und explizit aufräumen (Teardown löscht angelegte attempts/learner_state) oder eine Savepoint-/nested-transaction-Strategie verwenden.
6. **Ist der Browser-E2E (Playwright) für M6 verbindlich oder optional?**
   - *Warum:* docs/10 §6 lässt beide Varianten zu ('je nach Reifegrad'). Playwright-Tests sind flaky-anfällig und erhöhen CI-Komplexität; Unklarheit blockiert die Scope-Festlegung von TST-4.
   - *Empfehlung:* HTTP-Smoke als verbindlich und CI-blockierend; Browser-E2E (Playwright) optional und nicht-blockierend führen, bis er stabil ist.

### E13 Mock-Data-Seeder  _(6)_
1. **Soll der Seeder ein reproduzierbares RNG über eine explizite --seed-Flagge erhalten? Im Doc ist rng=random.Random() ein nicht geseedeter Default.**
   - *Warum:* Ohne festen Seed sind Demos und Tests nicht reproduzierbar; eine flackernde Mastery-Verteilung erschwert verlässliche Vorführungen und das Schreiben stabiler Assertions für MOCK-2.
   - *Empfehlung:* Ein --seed-Argument (Default 42) einführen, an seed()/_simulate_history durchreichen und als random.Random(seed) instanziieren; für unreproduzierbare Last bewusst --seed weglassen können.
2. **Wie wird garantiert, dass das load-Profil Kohorten >= MIN_COHORT_K erzeugt, wenn --students-per-class frei wählbar ist (Default 20, MIN_COHORT_K=10)?**
   - *Warum:* Wird --students-per-class unter MIN_COHORT_K gesetzt, werfen die Population-Aggregate (RET-4) CohortTooSmall und das zentrale load-Ziel (testbare Aggregate) ist verfehlt.
   - *Empfehlung:* Im load-Profil validieren: ist students_per_class < MIN_COHORT_K, eine deutliche Warnung ausgeben (oder abbrechen). Default 20 belassen, da > 10.
3. **Soll _reset() optional auch Content-Tabellen (content_notes, content_embeddings, subjects, skills, skill_edges) leeren? A.3 sagt 'und optional Content', ohne Tabellenliste.**
   - *Warum:* attempts.skill_id und learner_state.skill_id referenzieren skills ohne ON DELETE CASCADE; ein unbedachter Content-Reset könnte FK-Verletzungen auslösen, und das Curriculum ist ohnehin idempotent neu seedbar.
   - *Empfehlung:* Standardmäßig nur personenbezogene Tabellen truncaten (wie im Doc). Content-Reset als separate, ausgeschaltete Option (--reset-content) anbieten, die zuerst personenbezogene Tabellen leert.
4. **Als welcher DB-User verbindet sich der Seeder über DATABASE_URL — privilegierter Owner (its) oder eine RLS-Rolle?**
   - *Warum:* Der Seeder schreibt klassenübergreifend und muss RLS umgehen; verbände er sich als its_student, würden RLS-Policies die Inserts/Updates fail-closed blockieren und der Seed schlüge fehl.
   - *Empfehlung:* Dokumentieren und voraussetzen, dass DATABASE_URL im Dev auf den Owner its zeigt; kein SET ROLE im Seeder. Die Endnutzer-Isolation bleibt davon unberührt (Seeder läuft nur in Dev).
5. **Müssen item_ref-Werte (seed-{skill.key}-{i}) auf reale Items aus dem Grading-/Content-Pfad zeigen, oder sind synthetische Refs akzeptabel?**
   - *Warum:* Falls spätere Features (z. B. ein Item-Loader) item_ref auflösen, würden synthetische Mock-Refs ins Leere zeigen; falls nicht, ist synthetisch unproblematisch und einfacher.
   - *Empfehlung:* Synthetische seed-…-Refs belassen, da der Seeder keinen Grader aufruft und item_ref im Mock nur eine Versuchs-Referenz ist; bei späterem Item-Loader-Bedarf neu bewerten.
6. **Wie wird _simulate_history aus scripts/seed.py auf its.* zugreifen — über uv run aus apps/api heraus (sys.path) oder über ein installiertes Paket?**
   - *Warum:* scripts/seed.py liegt im Repo-Root, importiert aber its.learner_model.tracing und its.db.models aus apps/api/src; ohne korrekten Pfad/Editable-Install schlägt der Import fehl.
   - *Empfehlung:* Wie in den Aufruf-Beispielen (cd apps/api; uv run python ../../scripts/seed.py) das Skript im Kontext des apps/api-uv-Projekts ausführen, sodass its über die installierte/editable Paketauflösung importierbar ist.

### E14 Produktionsdaten & Compliance  _(7)_
1. **Welcher stabile externe Schlüssel wird für den idempotenten Roster-Upsert verwendet, und wird das Schema dafür um eine Spalte erweitert?**
   - *Warum:* Das Schema in docs/03 hat keine external_id/external_key auf students/classes. Ohne stabilen Schlüssel ist die geforderte Idempotenz (PROD-1) nicht erfüllbar, und ein blinder Insert würde Schüler verdoppeln und damit die Min-Cohort-Zählung (SAF-3) verfälschen.
   - *Empfehlung:* Alembic-Migration ergänzen: students.external_id text UNIQUE und classes.external_key text UNIQUE; Upsert via INSERT ... ON CONFLICT DO UPDATE auf diesen Spalten.
2. **Welches Quellformat und welches exakte Spaltenschema hat die Roster-Quelle (CSV vs. Schul-API)?**
   - *Warum:* docs/11 nennt nur 'CSV/Schul-API' ohne Felddefinition; ohne festgelegtes Schema ist die Pydantic-Validierung in PROD-1 unterspezifiziert.
   - *Empfehlung:* CSV mit Spalten external_id, display_name, grade_level, class_key (validiert über das RosterRow-Pydantic-Modell); API-Adapter später nachrüstbar, gleiche RosterRow-Validierung.
3. **Wird der Löschpfad pro Schüler:in nur dokumentiert oder als ausführbares, geguardetes CLI bereitgestellt?**
   - *Warum:* docs/11 B.3 fordert einen 'Löschpfad für einzelne Schüler:innen', spezifiziert aber kein Werkzeug. Ein rein dokumentierter SQL-Pfad ist fehleranfälliger im Betrieb und schlechter auditierbar.
   - *Empfehlung:* scripts/delete_student.py (uv-Entrypoint, --student-id oder --external-id) das DELETE FROM students WHERE id=... ausführt und auf CASCADE vertraut; durch denselben Prod-Guard wie der Import geschützt.
4. **Welche konkreten Aufbewahrungsfristen gelten pro Datenkategorie (attempts, learner_state, teacher_notes, students/PII, content)?**
   - *Warum:* docs/11 fordert ein 'definiertes Aufbewahrungsfenster pro Datenkategorie', nennt aber keine Werte. Ohne Zahlen ist das Retention-Konzept (PROD-3) nicht prüfbar.
   - *Empfehlung:* Vorschlag zur fachlich/rechtlichen Bestätigung: PII/students und attempts/learner_state für die Dauer der Einschulung + 12 Monate, teacher_notes analog; content unbefristet (kein Personenbezug). Werte sind als gegen revDSG/DSGVO zu prüfen zu markieren.
5. **Welcher konkrete CH/EU-Provider und welche Region werden für DB und (externe) LLM-Inferenz gewählt?**
   - *Warum:* P8 verlangt CH/EU-Residenz; docs/11 nennt nur Beispiele (Azure Switzerland, Exoscale, Infomaniak). Ohne konkrete Wahl bleibt die Deploy-Konfiguration (PROD-3) unvollständig und die DATABASE_URL-Trennung (PROD-2) hat kein konkretes Ziel.
   - *Empfehlung:* Default-Empfehlung: Managed Postgres in einer Schweizer Region (z. B. Exoscale/Infomaniak CH) und LLM_BACKEND=local (Qwen2.5) für Echtdaten; frontier nur mit AVV + No-Training + CH/EU-Inferenz.
6. **Soll bei DATA_MODE=prod zusätzlich verhindert werden, dass DATABASE_URL auf localhost zeigt (Defense-in-depth)?**
   - *Warum:* Der reine DATA_MODE-Guard schützt nicht vor einer falsch gesetzten Prod-DATABASE_URL, die versehentlich auf die Dev-DB zeigt; ein localhost-Check reduziert das Risiko eines Datenleaks zwischen Mock und Prod.
   - *Empfehlung:* Ja, als harter Fehler: bei DATA_MODE=prod abbrechen, wenn DATABASE_URL localhost/127.0.0.1 enthält; als Teil von PROD-2 implementieren.
7. **Embedding-Modell und Vektordimension: bleibt vector(1024) der Platzhalter, oder wird vor dem Produktiv-Content-Import ein konkretes Modell festgelegt?**
   - *Warum:* PROD-1 importiert echten Content über CON-2, das vector(1024) als 'Dim an Modell anpassen' deklariert. Ein späterer Modellwechsel würde ein Re-Embedding aller Produktivinhalte und eine Schema-/Index-Migration erzwingen.
   - *Empfehlung:* Vor dem ersten Produktiv-Content-Import ein konkretes, CH/EU-/lokal betreibbares Embedding-Modell festlegen und die Vektordimension in Schema und HNSW-Index entsprechend setzen, statt 1024 ungeprüft zu übernehmen.

## Risiken und Gegenmassnahmen

### E1 Foundations: Monorepo, Infra, Skeleton  _(7)_
- **src-Layout wird vom Build-Backend nicht erkannt → `import its` / `uvicorn its.main:app` schlägt lokal und in CI fehl.**
  - *Gegenmassnahme:* Build-Backend (Hatchling) mit explizitem packages=["src/its"] konfigurieren; in FND-2 Smoke-Test `uv run python -c "import its"` als Gate, bevor FND-4/FND-6 starten.
- **Schleichende pip-Nutzung in lokalen Skripten oder CI verletzt P9 und die projektweite DoD.**
  - *Gegenmassnahme:* CI nutzt ausschließlich astral-sh/setup-uv + uv-Befehle; kein requirements.txt im Repo; optional ein Grep-/Lint-Gate gegen 'pip install'. uv.lock committen für Reproduzierbarkeit.
- **pgvector-/uuid-ossp-Extension fehlt zur Laufzeit: init/-Skripte laufen nur beim ersten Volume-Start; der CI-Service mountet kein init-Volume.**
  - *Gegenmassnahme:* In CI expliziter `CREATE EXTENSION IF NOT EXISTS vector`-Schritt (bereits im Doc); lokal `docker compose down -v` bei Init-Änderungen; Verifikation via `SELECT extname FROM pg_extension`.
- **CI meldet fälschlich grün/mehrdeutig, weil keine Tests gesammelt werden (pytest Exit 5) — Safety-Regressionen würden später unbemerkt durchrutschen.**
  - *Gegenmassnahme:* Mindestens test_health.py (FND-4) und test_auth_stub.py (FND-5) anlegen, bevor CI scharf geschaltet wird; testpaths in pyproject setzen; Lauf prüft, dass >=1 Test gesammelt wurde; Branch-Protection erzwingt den ci-Check.
- **Unsicherer Auth-Bypass: ein scheinbar funktionierender current_principal-Stub könnte einen Fake-Principal liefern und so Tests/Endpoints unsicher 'grün' machen (P1-Risiko bei Daten Minderjähriger).**
  - *Gegenmassnahme:* Stub wirft bewusst NotImplementedError statt einen Principal zu fabrizieren; klare TODO-Markierung; PG_ROLE-Namen exakt an die spätere RLS (docs/04) gebunden, damit kein Mapping-Bruch entsteht.
- **Compliance/PII (P4/P8): versehentliches Committen echter Secrets/Keys oder Klartext-PII über .env, oder verfrühte externe LLM-Calls aus M0.**
  - *Gegenmassnahme:* .env via .gitignore ausgeschlossen, nur .env.example mit leeren Platzhaltern; LLM_BACKEND=local als Default; Principal trägt keine Klartext-PII; CH/EU-Hosting als spätere Infra-Entscheidung explizit markiert (Compose nur Prototyp).
- **Dev-Credentials (its/its_dev_pw, Port 5432 öffentlich gemappt) könnten versehentlich in produktionsnahe Umgebungen gelangen.**
  - *Gegenmassnahme:* Compose und CI-Service nutzen nur ephemere Dev-Credentials; Produktions-Konfiguration über separate, nicht versionierte Secrets in CH/EU-Hosting; im README klarstellen, dass infra/docker-compose.yml nur lokal/Prototyp ist.

### E2 Database: Schema & Migrationen  _(7)_
- **Der HNSW-Index auf content_embeddings(embedding) wird von Alembic-Autogenerate nicht erkannt und fehlt nach der Migration — der Semantic-Modus (RET-2) fällt still auf Sequential Scan zurück oder schlägt fehl.**
  - *Gegenmassnahme:* Index in DB-1 explizit per op.execute('CREATE INDEX ... USING hnsw (embedding vector_cosine_ops)') anlegen; im Smoke-Test gegen pg_indexes auf das Vorhandensein und die hnsw-Definition prüfen; downgrade droppt den Index zuerst.
- **scoped_session kehrt ohne RESET ROLE in den Connection-Pool zurück — eine nachfolgende Anfrage erbt die fremde Rolle/den fremden student_id-Kontext und liest fremde Schülerdaten (Cross-Request-Leak). Sicherheitskritisch (P1).**
  - *Gegenmassnahme:* RESET ROLE zwingend im finally; zusätzlich app.current_student_id zurücksetzen/auf LOCAL-Scope begrenzen (SET LOCAL bzw. set_config(..., is_local=true) innerhalb einer Transaktion). In den E3-Tests (test_rls) wird der Leak aktiv gegengeprüft.
- **Bind-Parameter in SET-Statements werden serverseitig nicht substituiert; app.current_student_id bleibt ungesetzt, RLS wird fail-open statt fail-closed — fremde oder alle Zeilen werden sichtbar.**
  - *Gegenmassnahme:* Kontext über set_config('app.current_student_id', :sid, false) mit echtem Bind-Param setzen; Rollennamen nur aus der PG_ROLE-Allowlist interpolieren; in der Verifikation current_setting('app.current_student_id', true) auslesen und mit der gesetzten UUID vergleichen.
- **SQL-Injection-Fläche bei der Interpolation des Rollennamens in SET ROLE, falls der Wert je aus Nutzereingaben statt aus der festen PG_ROLE-Map stammt.**
  - *Gegenmassnahme:* Rollenname ausschliesslich aus dem geschlossenen PG_ROLE-Mapping (FND-5) beziehen; keine freien Strings akzeptieren; optional gegen eine Allowlist (its_student|its_teacher|its_admin) validieren, bevor interpoliert wird.
- **Modelle (DB-2) und Migration (DB-1) driften auseinander — die App erwartet ein anderes Schema als migriert ist; subtile Bugs bis hin zu falscher Isolation.**
  - *Gegenmassnahme:* Als Verifikation alembic revision --autogenerate ausführen; der Diff muss leer sein. Diesen Check in CI als wiederkehrenden Gate-Schritt etablieren.
- **PII-Ausweitung im Schema: spätere Bequemlichkeitsfelder (z. B. echter Name, Geburtsdatum, Freitext) in students verletzen P4 und erschweren die Compliance (revDSG/DSGVO, Minderjährige).**
  - *Gegenmassnahme:* students strikt auf display_name/grade_level/created_at begrenzen (Code-Review-Gate); jede Erweiterung erfordert eine dokumentierte Begründung und Datenschutz-Prüfung; ON DELETE CASCADE für den Löschpfad ist bereits vorbereitet (PROD-3, P8).
- **Datenresidenz (P8): Migrationen/Seeds werden versehentlich gegen eine Nicht-CH/EU- bzw. Prototyp-DB (z. B. Railway) mit echten Daten ausgeführt.**
  - *Gegenmassnahme:* DB-4 legt nur anonyme Stammdaten an (keine Personendaten); Personendaten laufen über den durch DATA_MODE-Guards geschützten Seeder (docs/11); Produktions-DATABASE_URL strikt von Dev getrennt und in CH/EU-Region (Azure Switzerland, Exoscale, Infomaniak).

### E3 Safety & Isolation (RLS + Min-Cohort)  _(8)_
- **Owner-Bypass von RLS: Wenn der App-Login-User `its` zugleich Tabellen-Owner ist, ignoriert Postgres die Policies fuer ihn — die gesamte Zeilenisolation (P1) waere unwirksam, ohne dass es offensichtlich ist.**
  - *Gegenmassnahme:* FORCE ROW LEVEL SECURITY auf den geschuetzten Tabellen setzen; konsequentes SET ROLE its_student/teacher (kein Owner-Kontext) in scoped_session und DBFactory; test_unset_scope_returns_no_rows als Bruch-Detektor in SAF-4.
- **Safety-Tests laufen gegen die falsche Engine (z. B. SQLite) oder mit privilegiertem Lesepfad, sodass RLS gar nicht geprueft wird und die Tests faelschlich gruen sind.**
  - *Gegenmassnahme:* Tests strikt gegen echtes Postgres mit pgvector-Service (FND-6); conftest.engine wendet alembic upgrade head inkl. rls.sql an; alle Lese-Assertions ausschliesslich ueber db_factory.as_student/as_teacher; Daten-Setup getrennt vom Lesepfad.
- **Aggregat-Query umgeht enforce_min_cohort: Eine Population-Query, die die zentrale Schwelle nicht aufruft, kann eine Einzelperson de-anonymisieren (Aggregat-Leak).**
  - *Gegenmassnahme:* Konvention 'jede Aggregat-Antwort geht durch enforce_min_cohort' plus AK in RET-4 ('ausschliesslich via enforce_min_cohort'); zentrale, reviewbare Funktion; API-3 mappt CohortTooSmall neutral auf 403.
- **Off-by-one in der Schwelle (<= statt <) verweigert n==k faelschlich oder laesst n<k durch und leakt.**
  - *Gegenmassnahme:* Strikt < verwenden; Grenzwert-Tests (n==k erlaubt, n==k-1 verweigert) und Default-k-Test in test_cohort_threshold.py (empfohlene Ergaenzung zu den Pflicht-Faellen).
- **Vergessene RLS auf einer spaeter hinzukommenden PII-Tabelle leakt still.**
  - *Gegenmassnahme:* Konvention 'neue PII-Tabelle = RLS-Policy in derselben Migration'; optionaler Meta-Test, der relrowsecurity=true fuer alle bekannten PII-Tabellen verlangt.
- **CI-Safety-Gate wird uebersprungen oder laeuft nicht vorgelagert, sodass ein Bruch der Isolationsgarantie erst spaet oder gar nicht auffaellt.**
  - *Gegenmassnahme:* Dedizierter, vorgelagerter 'Safety gate (blocking)'-Schritt in ci.yml vor der vollen Suite; Merge blockiert bei Rot; Branch-Protection so konfigurieren, dass dieser Check Pflicht ist (zu klaeren mit Repo-Admin).
- **Lehrer-Sichtbarkeit zu eng oder zu weit: Fehlendes GRANT SELECT ON classes laesst die Teacher-Policy-Subquery leer laufen (Lehrer sieht keine eigenen Schueler), oder eine zu breite Policy zeigt klassenfremde Kinder (P6-Verstoss).**
  - *Gegenmassnahme:* GRANT SELECT ON classes TO its_teacher ergaenzen; Teacher-Policies exakt ueber enrollments JOIN classes WHERE teacher_id = app.current_teacher_id keyen; dedizierter Test fuer 'Lehrer sieht nur eigene Klasse' (empfohlen, formal in API-2/TST).
- **Admin-Pfad: Ein versehentliches pauschales BYPASSRLS oder eine zu breite Admin-Policy umgeht die gesamte Isolation.**
  - *Gegenmassnahme:* Kein pauschales BYPASSRLS; Admin-Funktionen ausschliesslich ueber dedizierte, gepruefte Pfade; falls Admin-Policies noetig, gezielt einzeln (FOR ALL TO its_admin USING(true)) und review-pflichtig.

### E4 Retrieval: Router + 3 Modi + Graph  _(9)_
- **Individual-Leak: eine eigentlich zu scopende Query (RET-3) liefert fremde Schuelerzeilen, wenn der Code-Filter fehlerhaft ist oder die Session nicht RLS-gescoped uebergeben wird.**
  - *Gegenmassnahme:* Doppelte Absicherung erzwingen: `require_student_scope` (fail-closed) im Code UND RLS in der DB. Tests gegen echtes Postgres mit angewandtem `rls.sql` (kein SQLite), die explizit pruefen, dass Schueler A 0 Zeilen von B sieht. Diese Tests CI-blockierend (analog SAF-4).
- **Aggregat-Leak: ein Population-Aggregat (RET-4) ueber eine Gruppe von genau einer Person wird zur de-anonymisierten Einzelauskunft.**
  - *Gegenmassnahme:* `skill_mastery_distribution` gibt das Ergebnis ausschliesslich via `enforce_min_cohort` zurueck; kein Codepfad liefert das rohe Aggregat. Test, dass n < k zuverlaessig `CohortTooSmall` wirft; `CohortTooSmall` nicht im Modul abfangen.
- **Router (RET-1) waehlt faelschlich INDIVIDUAL ohne vorhandenen Scope und erzeugt damit einen ungescopten Personen-Pfad.**
  - *Gegenmassnahme:* Fail-safe-Regel im Router: bei `has_student_scope=False` nie INDIVIDUAL zurueckgeben (Fallback SEMANTIC). Unit-Test fuer genau diesen Fall. Zusaetzlich faengt RET-3/RLS jeden ungescopten Versuch ab (Defense-in-depth).
- **SQL-Injection ueber dynamische Query-Parameter (Vektor-Literal in RET-2, IDs in RET-3/4/5).**
  - *Gegenmassnahme:* Ausnahmslos Bindparams nutzen (wie in den Doc-Snippets), kein f-String/`.format` in SQL. Eingabetypen pruefen (`query_embedding: list[float]`, IDs als UUID/str). Pydantic-Validierung der Query-Parameter an der API-Grenze (E9).
- **Schlechtes Retrieval, weil Codebloecke mit-embeddet wurden — SQL-Tokens verzerren die Vektoren (Abhaengigkeit von CON-2).**
  - *Gegenmassnahme:* RET-2 setzt voraus, dass CON-2 nur Prosa embeddet und SQL als `sidecar_query` trennt (E5-Kernregel). Integrationstest fuer RET-2 erst gegen korrekt eingespielte Embeddings; bis CON-2 fertig ist, mit kontrollierten Stub-Vektoren testen.
- **Vektordimensions-Drift: Schema (vector(1024)), Ingestion und Query-Embedding nutzen unterschiedliche Dimensionen → Laufzeitfehler oder leise falsche Treffer.**
  - *Gegenmassnahme:* Dimension projektweit aus einer zentralen Quelle (Settings/Schema) ableiten, nicht hartcodieren. Embedding-Modell+Dimension verbindlich festlegen (siehe offene Frage). Smoke-Test, der die Insert-/Query-Dimension gegen die Schema-Dimension prueft.
- **Unbegrenzte/zyklische Graph-Traversierung in RET-5 (Zyklen in `skill_edges`) fuehrt zu Hang oder Ressourcenerschoepfung.**
  - *Gegenmassnahme:* Tiefenlimit `d.depth < :max_depth` in der rekursiven CTE durchsetzen; `max_depth` validieren. Test mit kuenstlichem Zyklus, der Terminierung beweist.
- **PII-Compliance (P4/P8): Individual-/Population-Daten (Namen, IDs, Mastery Minderjaehriger) gelangen ueber spaetere Agent-/LLM-Pfade nach aussen.**
  - *Gegenmassnahme:* RET-3/RET-4 geben Daten nur innerhalb des Systems zurueck; die Anonymisierung vor externen LLM-Calls liegt verbindlich beim LLM-Client (`llm/anonymize.scrub`, docs/07). In E4 sicherstellen, dass kein Retrieval-Modul selbst ein externes LLM aufruft. Hosting in CH/EU-Region (P8).
- **Verstoss gegen P9 durch versehentliche `pip`-Nutzung beim Hinzufuegen einer Dependency.**
  - *Gegenmassnahme:* Keine neue Dependency in E4 erwartet (alles via vorhandenem sqlalchemy/pgvector). Falls doch noetig: ausschliesslich `uv add`. CI/Review pruefen auf `pip`-Aufrufe.

### E5 Content-Ingestion (Markdown-Vault)  _(7)_
- **Datenresidenz-Verstoß (P8): Prosa-Chunks werden beim Embedding an eine Frontier-API außerhalb CH/EU geschickt.**
  - *Gegenmassnahme:* Embedding-Pfad zwingend über settings.llm_backend leiten, Default 'local'; Frontier nur mit explizit CH/EU-konformem Endpoint. CI/Konfig prüft, dass im Default-Modus kein externer Call erfolgt.
- **Schlechtes Retrieval durch mit-embeddete Code-Tokens, falls die Prosa/Code-Trennung lückenhaft ist (z. B. Fence ohne Sprach-Tag, verschachtelte Zäune).**
  - *Gegenmassnahme:* Parser-Regex aus dem Doc unverändert übernehmen; Unit-Tests für mehrere Fences, Fence ohne Tag und Inline-Backticks; Integrationstest assertet, dass kein content_embeddings.chunk SQL-Schlüsselwörter (z. B. 'SELECT') enthält.
- **Embedding-Dimension passt nicht zur vector(1024)-Schemaspalte → harte Insert-Fehler oder (schlimmer) stille Fehlkonfiguration.**
  - *Gegenmassnahme:* Modell+Dimension verbindlich festlegen, Migration darauf anpassen; Pipeline validiert die Länge des zurückgegebenen Vektors gegen die Spaltendefinition und bricht mit klarer Meldung ab.
- **Nicht-idempotente Ingestion erzeugt bei jedem Lauf Duplikate in content_notes/content_embeddings und verfälscht die Vektorsuche.**
  - *Gegenmassnahme:* Upsert/Replace über source_path als natürlichen Schlüssel; bestehende Embeddings vor dem Neuschreiben via CASCADE entfernen; deterministisch sortierte Datei-Discovery für reproduzierbare Läufe.
- **Falsch-positive Kanten/Links: ein [[wikilink]] in einem SQL-Kommentar oder ein nicht auflösbares Linkziel erzeugt fehlerhafte oder verwaiste skill_edges.**
  - *Gegenmassnahme:* Wikilinks ausschließlich aus der bereinigten Prosa (nach Fence-Entfernung) extrahieren; Kanten nur bei beidseitig aufgelösten Endpunkten anlegen; nicht auflösbare Ziele/Skills loggen statt zu raten.
- **Unklare Schema-Heimat für Notiz-Kanten (docs/00 'Notiz-Kanten' vs. nur skill_edges) führt zu inkonsistenter Persistenz und unsichtbaren Kanten für RET-5.**
  - *Gegenmassnahme:* Vor CON-2 verbindlich entscheiden (offene Frage 4): skill-bezogene Links als skill_edges kind='related'; reine Notiz-Links zunächst nur loggen, bis eine eigene Tabelle gemessen nötig ist.
- **Privilegierter Ingestion-Pfad umgeht das RLS-Gate; eine Verwechslung mit dem request-scoped Pfad könnte versehentlich Schüler-Tabellen mit derselben Owner-Rolle berühren.**
  - *Gegenmassnahme:* Ingestion strikt auf content_*/skill_edges beschränken; dedizierte Rolle/Account nur mit den nötigen Rechten; CLI-Entrypoint dokumentiert getrennt vom scoped_session-Request-Pfad halten.

### E6 Learner-Modell (BKT)  _(6)_
- **Direkter Schreibzugriff auf learner_state umgeht record_attempt (z. B. im Agent-Node oder einer API), wodurch mastery, uncertainty und attempts_count auseinanderlaufen (P3-Verletzung).**
  - *Gegenmassnahme:* record_attempt als einzigen dokumentierten Schreibpfad markieren (Modul-Docstring); in Code-Review explizit prüfen; im Integrationstest sicherstellen, dass uncertainty == 1/(attempts_count+1) gilt. Mittelfristig prüfen, ob eine DB-Trigger-/Constraint-Absicherung sinnvoll ist.
- **Numerische Drift / Division durch 0 führt zu mastery außerhalb [0,1] oder zu NaN, was Pädagogik und Lehrer-Einschätzung verfälscht.**
  - *Gegenmassnahme:* den>0-Guard in posterior (aus dem Doc) beibehalten; Property-Test 'immer in [0,1]'; defensives Clamping beim Schreiben in learner_state (siehe offene Frage).
- **DKT-Stub wird versehentlich aktiviert oder verdrahtet, wodurch eine nicht-interpretierbare Black-Box den Lernweg Minderjähriger beeinflusst (P5-Verletzung).**
  - *Gegenmassnahme:* Stub wirft NotImplementedError; Aktivierungsbedingungen explizit dokumentiert; Test, der den geworfenen Fehler erzwingt; kein Import von dkt in tracing/agent.
- **Compliance/PII (P4/P8): learner_state oder Attempt-Inhalte (raw_answer) könnten indirekt PII enthalten oder versehentlich in einen externen LLM-Pfad geraten.**
  - *Gegenmassnahme:* learner_state führt nur IDs/Zahlen (keine Klartext-PII). E6 ruft kein externes LLM auf. Bewusst keine Namen/Freitext im Learner-Modell speichern; raw_answer ist Teil von Attempt (DB-2) und darf nie roh an externe LLMs — der Anonymizer (docs/07) bleibt für den generativen Pfad zuständig.
- **RLS-Interaktion: record_attempt wird außerhalb einer korrekt gescopten Session aufgerufen (ohne app.current_student_id), wodurch Schreib-/Lesezugriffe fail-closed scheitern oder fremde Zeilen berührt werden könnten.**
  - *Gegenmassnahme:* Service committet nicht selbst und setzt voraus, in scoped_session (docs/03 §5) zu laufen; Aufrufer (Agent/API) öffnet die Session mit Rolle + student_id; test_rls.py (docs/04/10) bleibt CI-blockierend und prüft Isolation auch für learner_state.
- **session.get mit Composite-PK als Dict verhält sich versionsabhängig (SQLAlchemy 2.0); Fehlverhalten könnte einen zweiten learner_state-Datensatz statt eines Updates erzeugen.**
  - *Gegenmassnahme:* Integrationstest mit zwei aufeinanderfolgenden record_attempt-Aufrufen prüft, dass attempts_count==2 auf EINEM Datensatz steht; SQLAlchemy-Version in pyproject (>=2.0) pinnen.

### E7 Grading-Strategy-Registry  _(7)_
- **SymPy `sympify` evaluiert weitgehend beliebige Ausdrücke aus freier Schülereingabe (Ressourcenverbrauch, unerwartete/komplexe Ausdrücke) — Sicherheitsangriffsfläche bei Minderjährigen.**
  - *Gegenmassnahme:* Eingabelänge hart begrenzen; Tests gegen bösartige/überlange Eingaben; mittelfristig `sp.parse_expr` mit eingeschränktem `local_dict`/`transformations` statt `sympify`; Fehlerpfad fängt `SympifyError`/`TypeError` ab und liefert sicheres `GradeResult(False, ..., 1.0)`.
- **Falsch-positive Mathe-Bewertung durch numerische vs. symbolische Äquivalenz (z. B. 0.333 vs 1/3) — P2-Bruch: ein Kind wird falsch bestätigt oder fälschlich als falsch markiert.**
  - *Gegenmassnahme:* Default symbolisch-exakt (`sp.simplify(got - expected) == 0`); Toleranz/Modus nur bewusst pro Item einführen; Tests mit äquivalenten Formen und Grenzfällen; Konvention im Code dokumentieren.
- **History zementiert einen LLM-Vorschlag ungeprüft ins learner_state (P6-Bruch), wenn die Konfidenz versehentlich >= der Zementierungs-Schwelle (0.9 in AG-2) gesetzt wird.**
  - *Gegenmassnahme:* HistoryGrader setzt strukturell `confidence < 1.0` (und < 0.9); Unit-Test erzwingt dies; die Schwellenlogik in `update_model_node` (AG-2) hält niedrige Konfidenz vom automatischen Schreiben ab und übergibt an die Lehrperson.
- **Roher Schüler-Antworttext (potenziell mit Namen/PII) gelangt über den History-LLM-Pfad an eine externe API — P4-Bruch.**
  - *Gegenmassnahme:* History ruft den LLM ausschliesslich über `its.llm.client.complete` (AG-3) auf, der `scrub` vor jedem externen Call anwendet; vor Verfügbarkeit von AG-3 bleibt History ein Stub ohne realen externen Call; defense-in-depth: dem LLM nur Rubric/Skill-Kontext statt Rohtext reichen, wo möglich.
- **Erosion der einzigen Plugin-Naht (P7): andere Module (retrieval/agent/learner_model) werden ebenfalls 'registrierbar' gemacht, weil die Registry als generisches Muster wirkt.**
  - *Gegenmassnahme:* Registry-API auf `grading/` beschränkt halten; keine generischen Registry-Helfer exportieren; Code-Review-Checkpunkt und Doku, dass `grading/` die einzige Naht ist (docs/00 Section 6).
- **Inkonsistenter subject_key zwischen Registry, TutorState und subjects-Tabelle führt zu `LookupError` im Bewertungspfad zur Laufzeit.**
  - *Gegenmassnahme:* Kanonische Keys (`math`/`language`/`history`) in zentraler Konstante/Enum festlegen; gegen `subjects.key` (DB) und `TutorState.subject_key` validieren; Registrierungs-Smoke-Test prüft, dass alle erwarteten Keys auffindbar sind.
- **Verstoss gegen P9 (uv-only) durch versehentliche pip-Nutzung beim Hinzufügen weiterer Grading-Dependencies.**
  - *Gegenmassnahme:* `sympy` ist bereits in pyproject.toml (FND-2); weitere Dependencies nur via `uv add`; DoD-Check und CI (uv sync) blockieren pip-Abweichungen.

### E8 Agent-Loop (LangGraph)  _(7)_
- **P4-Leck: freier Schülertext (z. B. raw_answer oder ein Name in der Frage) gelangt an ein externes LLM, weil ein Node-Pfad scrub umgeht.**
  - *Gegenmassnahme:* scrub ausnahmslos in client.complete() vor jeder Backend-Verzweigung; explain_node baut den Prompt nur aus skill_key+intent; Unit-Test test_anonymize.py plus ein Test, dass explain_node keinen Namen in den user-Prompt schreibt.
- **P1/RLS-Bruch: update_model_node öffnet eine ungescopte SessionLocal() und schreibt/liest ohne app.current_student_id, sodass eine fehlerhafte Query fremde Schülerzeilen berühren könnte.**
  - *Gegenmassnahme:* Node innerhalb scoped_session(principal) betreiben (request-scoped Session injizieren); Integrationstest gegen echtes Postgres mit RLS; fail-closed, wenn student_id fehlt (PermissionError).
- **P6-Verletzung: ein Bug schreibt auch bei niedriger Konfidenz in learner_state und zementiert eine möglicherweise falsche Einschätzung ohne Lehrer-Review.**
  - *Gegenmassnahme:* Konfidenz-Gate confidence >= 0.9 explizit und getestet (Fall confidence=0.5 -> kein Write, mastery is None); Schwelle ggf. konfigurierbar; History-Grader liefert bewusst < 1.0.
- **P2-Verletzung: der answer_key oder eine korrekt/falsch-Entscheidung stammt versehentlich aus dem generativen Pfad (LLM) statt aus dem kuratierten Grader.**
  - *Gegenmassnahme:* Graph trennt assess (kuratiert) strukturell von explain (generativ) per bedingter Kante; assess nutzt ausschliesslich load_item.answer_key + get_grader; EXPLAIN_SYSTEM erzeugt keine endgültigen Bewertungen.
- **P8-Verletzung: das frontier-Backend sendet (selbst gescrubbte) Daten an einen Nicht-CH/EU-Endpoint und verletzt die Datenresidenz für Minderjährige.**
  - *Gegenmassnahme:* Default llm_backend=local; frontier nur gegen CH/EU-Endpoint freigeben; Residenz-Constraint in client.py/Doku vermerken; Entscheidung vor Produktivschaltung dokumentieren.
- **Erfundene Bibliotheks-API: falsche Annahmen über die LangGraph-Version (StateGraph/add_conditional_edges/compile/invoke) oder über ein nicht spezifiziertes LLM-SDK führen zu nicht lauffähigem Code.**
  - *Gegenmassnahme:* Nur gegen die in pyproject.toml gepinnten Versionen implementieren; bei Abweichung Doc-Hinweis statt Erfindung; _complete_frontier/_complete_local bis zur SDK-Entscheidung als nicht-leakende, klar markierte Stubs.
- **Undefinierte Abhängigkeit load_item / _skill_id: assess_node und update_model_node hängen an nicht spezifizierten Funktionen, was zu improvisierten und potenziell unsicheren Implementierungen führt.**
  - *Gegenmassnahme:* load_item-Signatur und answer_key-Quelle vorab klären (offene Frage 1); _skill_id als eindeutigen Lookup über (subject_id, key) innerhalb der gescopten Session definieren; bis zur Klärung als blockierend markieren statt zu raten.

### E9 Backend-API (Student + Teacher)  _(8)_
- **Doppelte/uneinheitliche DB-Session: POST /student/turn öffnet scoped_session, aber der update_model-Agent-Node öffnet ein eigenes ungescoptes SessionLocal() — Schreibzugriff könnte RLS umgehen und unter falschem Kontext laufen (P1-Bruch).**
  - *Gegenmassnahme:* Die request-scoped Session in den Graph-Kontext injizieren und im Node wiederverwenden; als expliziten Umsetzungsschritt + offene Frage mit dem AG-Owner führen. Test: attempt/learner_state werden nur für die scoped student_id geschrieben.
- **Detail-Leak über Fehlerantworten: ein Safety-Exception-Text (z. B. 'cohort n=3 below threshold k=10') in der Response macht die Antwort selbst zur De-Anonymisierungsquelle (Aggregat-Leak).**
  - *Gegenmassnahme:* Zentraler Exception-Handler (API-3) gibt ausschliesslich neutrale Meldungen ({"detail":"forbidden"}); Exception-Text nur ins Log. Test prüft, dass der Response-Body keine n=/Schwellen-Info enthält.
- **PII in der URL: POST /note mit body als Query-Param schreibt Freitext über Minderjährige in Server-/Proxy-/Access-Logs.**
  - *Gegenmassnahme:* Notiz als Pydantic-Body-Schema (POST-Body), nie als Query-Param; override_mastery auf 0..1 validieren (P4).
- **RLS in der Test-DB nicht aktiv -> HTTP-Tests bestehen falsch-positiv und eine Isolationsverletzung bleibt unentdeckt.**
  - *Gegenmassnahme:* Tests laufen gegen echtes Postgres mit angewandtem rls.sql (Fixtures engine/db_factory aus docs/10); kein SQLite. Vorgelagerter, blockierender Safety-CI-Schritt bleibt aktiv.
- **Schüler-API liefert uncertainty mit aus, obwohl P5 sie der Lehrerseite vorbehält — die Rohschätzung ist über die Netzwerk-Response abgreifbar, selbst wenn die UI sie verbirgt.**
  - *Gegenmassnahme:* Eigenes schlankes StudentSkillMastery-Schema ohne uncertainty für /student/mastery (Defense-in-depth statt UI-Disziplin).
- **current_principal ist ein Stub (FND-5) und wirft NotImplementedError -> Endpoints sind ohne echtes JWT nicht aufrufbar; bei vorzeitigem Produktionseinsatz wäre Auth offen.**
  - *Gegenmassnahme:* In Tests app.dependency_overrides[current_principal] setzen; im Issue als Vorbedingung markieren; Produktion erst nach FND-5 (echtes JWT-Decoding gegen settings.jwt_public_key).
- **Typ-/Key-Mismatch zwischen mastery_overview-dicts (z. B. UUID-skill_id) und dem SkillMastery-Schema (str) -> 500 bei der Response-Serialisierung.**
  - *Gegenmassnahme:* skill_id in der Query zu text casten (::text wie in teacher.py) oder im Schema-Validator konvertieren; Verifikation als Testschritt.
- **Datenresidenz: in M4 läuft ggf. noch Railway o. Ä.; Schülerdaten Minderjähriger erfordern CH/EU-Residenz (P8).**
  - *Gegenmassnahme:* API für Prototyp ok, Produktion in CH/EU-Region (Azure Switzerland/Exoscale/Infomaniak) gemäss docs/00 §5; in PROD-3 verankert, hier als Deployment-Vorbedingung notieren.

### E10 Frontend: Schueler-Session  _(7)_
- **Leak der Unsicherheit/Rohschätzung auf der Schülerseite (Bruch von P5).**
  - *Gegenmassnahme:* MasteryBar-Props nehmen uncertainty gar nicht erst entgegen; myMastery() mappt nur mastery durch; Code-Review plus optionaler Test, der prüft, dass kein Unsicherheitswert im Schüler-DOM gerendert wird.
- **Vermischung von Bewertungs- und generativem Pfad (Bruch von P2): ein Helfer-Klick erzeugt fälschlich eine grade oder hebt die Mastery an.**
  - *Gegenmassnahme:* Helfer-Buttons rufen ausschliesslich intent: explain/hint/why und rendern nur explanation; Assertion/Test stellt sicher, dass MasteryBar-Wert und grade-Anzeige nach einem Helfer-Aufruf unverändert bleiben; UI trennt die Button-Gruppen sichtbar.
- **PII oder direkte externe LLM-Calls aus dem Browser (Bruch von P4).**
  - *Gegenmassnahme:* Frontend ruft ausschliesslich die eigene Backend-API (/student/turn); generative Erklärungen und Anonymisierung laufen serverseitig; keine PII in Query-Strings oder Client-Logs.
- **Statische Web-Assets ausserhalb CH/EU ausgeliefert (Bruch von P8).**
  - *Gegenmassnahme:* Deploy der Web-Assets in derselben CH/EU-Region wie die API festlegen und in der Deploy-/Compliance-Doku (Verweis PROD-3) dokumentieren.
- **Undefinierte Auth-Token-Herkunft führt zu unsicherem oder gar fehlendem Scoping beim Aufruf der RLS-gescopten Endpoints.**
  - *Gegenmassnahme:* Token-Bezug an einer Stelle kapseln und als TODO markieren; vor Produktion durch echten OIDC-Flow ersetzen; bis dahin keine produktiven Schülerdaten anbinden.
- **FE-S2 wird gegen einen erfundenen Mock statt gegen API-1 gebaut und weicht vom echten Vertrag ab.**
  - *Gegenmassnahme:* Typisierter api/client.ts als einzige Naht; gegen den realen TurnResponse/SkillMastery-Typ aus docs/08 typprüfen; Mock nur temporär und klar markiert, vor Merge auf echten Endpoint umstellen.
- **Fehlerantworten des Backends (403 Safety, 422 Validierung) leaken Details oder verwirren das Kind.**
  - *Gegenmassnahme:* Im Frontend nur neutrale, ermutigende Fehlermeldungen anzeigen (kein Statuscode/Stacktrace); Safety-403 als allgemeiner Hinweis behandeln, nicht als Datenleck-Detail.

### E11 Frontend: Lehrer-Dashboard  _(6)_
- **P1-Bruch durch UI-seitige Filterung: Wenn das Dashboard versucht, selbst nach 'eigenen Klassen' zu filtern, statt sich auf RLS zu verlassen, entsteht eine zweite, fehleranfällige Sicherheitsgrenze, die im Widerspruch zur DB-verankerten Isolation steht.**
  - *Gegenmassnahme:* Bewusst keine Zugehörigkeits-Filterung im Frontend; ausschliesslich die RLS-gefilterten Teacher-Endpoints konsumieren. Backend-Gegenprobe (curl mit fremder student_id liefert 0 Zeilen/403/404) als Verifikationsschritt; Code-Review-Regel.
- **P5-Bruch: uncertainty (und attempts_count) werden versehentlich in eine geteilte oder Schüler-Komponente durchgereicht und damit dem Kind angezeigt, was demotiviert und die bewusste Präsentations-Trennung untergräbt.**
  - *Gegenmassnahme:* uncertainty nur in teacher/-Komponenten verwenden; getrennte TypeScript-Typen für Schüler- vs. Lehrer-Sicht; Smoke-Test bestätigt, dass die Schüler-Antwort kein uncertainty-Feld rendert.
- **Min-Cohort-403 wird als generischer Fehler behandelt (Error-Toast oder Retry), wodurch die Datenschutzgarantie für die Lehrperson unverständlich wird oder im schlimmsten Fall Roh-Zahlen geleakt werden.**
  - *Gegenmassnahme:* Statuscode-spezifische Behandlung in client.ts/Panel: 403 der Verteilung -> dedizierte MinCohortNotice statt Zahlen; expliziter Komponententest für den 403-Pfad.
- **PII Minderjähriger (Schülernamen, Lernstand) gelangt in Browser-Logs, Fehler-Telemetrie oder URLs und verlässt damit potenziell die CH/EU-Residenz (P8).**
  - *Gegenmassnahme:* Nur darstellen, was API-2 liefert; keine PII in console-Logs/URL-Query; Telemetrie (falls vorhanden) ohne Klartext-PII; Datenresidenz bleibt Backend-/Hosting-Sache (CH/EU-Region).
- **Fehlende Audit-Spur bei Mastery-Override: Ein Override ohne nachvollziehbaren Urheber/Zeitpunkt unterläuft die Auditierbarkeit (P3/P7), die ein menschliches Eingreifen über ein KI-Modell erst legitimiert.**
  - *Gegenmassnahme:* teacher_notes schreibt teacher_id, skill_id, override_mastery und body (Backend); die UI macht den Override als Notiz-Eintrag sichtbar und lädt das Panel nach dem Schreiben neu, statt nur lokal zu mutieren.
- **Vertrags-Drift zwischen Frontend-Typen und API-2-Schemas (z. B. addNote-Request-Form Query vs. JSON, oder fehlendes uncertainty-Feld), was zu 422-Fehlern oder stillen Anzeigefehlern führt.**
  - *Gegenmassnahme:* TypeScript-Typen exakt aus den Pydantic-Schemas (docs/08 §1) spiegeln; npm run build/tsc --noEmit als Gate; offene Frage zur addNote-Request-Form vor Implementierung klären; HTTP-Smoke gegen die laufende API.

### E12 Testing & CI  _(8)_
- **Tests laufen versehentlich gegen SQLite oder eine DB ohne aktivierte RLS — dann wird die wichtigste Eigenschaft (Zeilenisolation) gar nicht geprüft, und ein RLS-Regress bleibt unentdeckt (Kinderdaten-Leak).**
  - *Gegenmassnahme:* DATABASE_URL hart auf Postgres mit pgvector erzwingen; Guard in conftest.py, der ohne Postgres-URL mit klarer Meldung abbricht; Safety-Gate als vorgelagerter, blockierender CI-Schritt (docs/10 §7) gegen den Postgres-Service-Container.
- **Das Safety-Gate ist umgehbar (z. B. via -k-Filter oder Skip), sodass ein Build grün wird, obwohl test_rls.py/test_cohort_threshold.py nicht liefen.**
  - *Gegenmassnahme:* Eigener, vorgelagerter CI-Schritt mit explizit benannten Dateipfaden (uv run pytest tests/test_rls.py tests/test_cohort_threshold.py -q) VOR der Full Suite; keine Skip-/Filter-Mechanik im Safety-Schritt; Branch-Protection verlangt diesen Check.
- **Commit im Agent-Schreibpfad (update_model_node) bricht die Transaktions-Rollback-Isolation der db-Fixture und hinterlässt Reststände, die Folgetests verfälschen.**
  - *Gegenmassnahme:* TST-3 über db_factory.as_student mit eigener Session + explizitem Teardown oder Savepoint-Isolation; Session-Injektion klären, damit der Node die Test-Session nutzt; nach dem Test angelegte attempts/learner_state gezielt entfernen.
- **Der HTTP-E2E-Smoke benötigt Auth, aber current_principal ist Stub (NotImplementedError) — ohne saubere Test-Auth wird Auth im Test umgangen, was eine reale Sicherheitslücke verschleiern kann (Token-/Rollen-Mapping ungetestet).**
  - *Gegenmassnahme:* Für den Smoke dependency_overrides mit Test-Principals nutzen, aber den realen JWT-Pfad (settings.jwt_public_key, Claims-Mapping auf Role + student_id) als Folgeaufgabe markieren und gesondert testen, sobald FND-5 echtes Decoding liefert.
- **PII gelangt über den explain-Pfad in einen externen LLM-Call, falls ein E2E/Integration-Test versehentlich intent=explain mit echtem Frontier-Backend fährt (P4-Verletzung).**
  - *Gegenmassnahme:* Tests mit settings.llm_backend=local oder gemocktem complete laufen lassen; test_anonymize.py sichert scrub ab; im E2E den ANSWER-Pfad (kuratiert, kein LLM) als Default; jeden explain-Test nur mit gescrubbtem/gemocktem Client.
- **CI-Postgres ohne nötige Extensions (vector/uuid-ossp) lässt die rls.sql-/Schema-Migration scheitern, was als Test-Infrastrukturfehler statt als echter Regress missinterpretiert wird.**
  - *Gegenmassnahme:* engine-Fixture/CI-Schritt installiert CREATE EXTENSION vector und uuid-ossp vor dem Alembic-upgrade (FND-6 macht das bereits für vector; uuid-ossp ergänzen); Migration idempotent (DO-Block für Rollen) wie in docs/04 §2.
- **Daten-/Compliance-Risiko: Test- und Seed-Daten mit realistischen PII-ähnlichen Namen könnten in Logs/CI-Artefakten landen (Minderjährige, revDSG/DSGVO, P8).**
  - *Gegenmassnahme:* In Fixtures nur synthetische, nicht-identifizierende display_names verwenden; keine echten Schülerdaten in Tests; CI-DB ephemer (Service-Container, kein Persist); Test-Artefakte nicht mit DB-Dumps anreichern.
- **Flaky Browser-E2E (Playwright) blockiert oder destabilisiert die CI und untergräbt das Vertrauen in das Safety-Gate, wenn beide im selben Job laufen.**
  - *Gegenmassnahme:* HTTP-Smoke verbindlich/blockierend; Playwright in einem separaten, nicht-blockierenden Job; Safety-Gate strikt von E2E-Browser-Läufen trennen, damit ein flaky Browser-Test nie das Safety-Signal verdeckt.

### E13 Mock-Data-Seeder  _(7)_
- **Mock-Daten oder ein Reset landen versehentlich in der Produktions-DB (Datenverlust / Vermischung von Echt- und Mock-Daten bei Minderjährigen).**
  - *Gegenmassnahme:* Identischer _guard_not_prod() vor JEDEM Schreibpfad (Seed und Reset), der bei DATA_MODE != mock vor dem ersten DB-Zugriff per sys.exit abbricht; zusätzlich (E14/PROD-2) strikt getrennte DATABASE_URLs für Dev und Prod.
- **Direktes Schreiben von learner_state würde P3 verletzen und Demo-Verteilungen vom Live-Modell entkoppeln (irreführendes Open Learner Model).**
  - *Gegenmassnahme:* Mastery ausschließlich über record_attempt (LM-2) ableiten; Code-Review/Test stellt sicher, dass der Seeder keinen direkten Insert/Update auf learner_state ausführt.
- **Uniform-zufällige Antworten erzeugen unbrauchbare, gleichförmige Mastery-Werte; Demos und Population-Tests verlieren Aussagekraft.**
  - *Gegenmassnahme:* Latente Fähigkeit je Schüler:in (betavariate) plus Übungsfortschritt; Verifikation über Streuungs-/Varianz-Check auf learner_state.mastery.
- **load-Profil erzeugt Kohorten < MIN_COHORT_K, wodurch RET-4-Aggregate CohortTooSmall werfen und nicht testbar sind.**
  - *Gegenmassnahme:* Default students-per-class > k halten und im load-Profil bei Unterschreitung von MIN_COHORT_K warnen/abbrechen.
- **Performance-/Speicherprobleme bei großen load-Läufen durch N+1 record_attempt-Aufrufe und einen einzigen End-Commit.**
  - *Gegenmassnahme:* Bulk-Inserts für attempts, periodische flushes/Batch-Commits, Tracing weiterhin über den Service; Last in CI begrenzen.
- **Seeder verbindet sich mit einer RLS-Rolle (its_student) und schlägt fail-closed fehl, oder ein Fehlkonfigurierter Owner-Zugang öffnet Prod.**
  - *Gegenmassnahme:* DATABASE_URL im Dev auf Owner its setzen, kein SET ROLE im Seeder; klar dokumentieren, dass dieser privilegierte Zugang nur in Dev existiert und der Prod-Guard ihn dort sperrt.
- **Synthetische display_name-Werte könnten versehentlich realistische PII enthalten oder mit Echtdaten kollidieren.**
  - *Gegenmassnahme:* Eindeutig synthetische Namensschemata (z. B. 'Schueler:in {n}') verwenden; keine realen Namenslisten einbinden; Mock strikt von Prod getrennt halten (P4/P8).

### E14 Produktionsdaten & Compliance  _(8)_
- **Versehentlicher Seed/Reset gegen die Prod-DB löscht oder verfälscht Echtdaten Minderjähriger (TRUNCATE im Reset-Pfad).**
  - *Gegenmassnahme:* Code-seitiger Guard _guard_not_prod() (DATA_MODE != mock => sys.exit) für Seed und Reset; getrennte DATABASE_URL; optionaler localhost-Check bei prod; Unit-Tests beweisen, dass der Seeder in prod abbricht (PROD-2).
- **Mock- und Echtdaten landen im selben Datenbank-Cluster und vermischen sich (verfälscht Min-Cohort-Aggregate und leakt Testdaten in Prod-Sichten).**
  - *Gegenmassnahme:* Strikt getrennte DATABASE_URL/Datenbanken, dokumentierte 'kein gemeinsamer Cluster'-Regel, getrennte Skripte (seed.py vs. import_production.py) mit gegensätzlichen Guards; .env in .gitignore, Prod-Secrets nie eingecheckt.
- **Re-Import eines Rosters erzeugt Duplikate (doppelte Schüler), wodurch Kohortenzahlen über MIN_COHORT_K springen und die De-Anonymisierungs-Schwelle (SAF-3) ausgehebelt wird.**
  - *Gegenmassnahme:* Idempotenter Upsert über stabile externe Schlüssel (external_id/external_key, UNIQUE); Idempotenz-Test (zweimaliger Import => identische Zeilenzahl) in PROD-1.
- **PII Minderjähriger gelangt im Klartext an eine externe LLM-API (Verstoss gegen P4/P8 und revDSG/DSGVO).**
  - *Gegenmassnahme:* Echtdaten-Default LLM_BACKEND=local; bei frontier greift scrub() (llm/anonymize.py) vor jedem externen Call plus verpflichtender AVV/DPA mit No-Training-Setting und CH/EU-Inferenz, dokumentiert in PROD-3.
- **Datenhaltung ausserhalb CH/EU (z. B. Prototyp-Hosting Railway oder eine nicht-EU-LLM-Region) verletzt die Residenzpflicht.**
  - *Gegenmassnahme:* CH/EU-Region in der Deploy-Konfiguration (infra/) festschreiben, Prototyp-Hosting explizit für Echtdaten ausschliessen; getrennte Prod-DATABASE_URL zeigt auf CH/EU-DB (PROD-2/PROD-3).
- **Unvollständige Löschung auf Lösch-Anfrage (Betroffenenrecht): verwaiste Zeilen in attempts/learner_state/teacher_notes bleiben bestehen.**
  - *Gegenmassnahme:* Löschpfad nutzt das ON DELETE CASCADE des Schemas (ein DELETE FROM students); CASCADE-Smoke-Test belegt, dass abhängige Zeilen verschwinden (PROD-3).
- **Teil-Commit eines fehlerhaften Roster-Imports hinterlässt die DB in inkonsistentem Zustand.**
  - *Gegenmassnahme:* Alle Zeilen vor dem Schreiben per Pydantic validieren, Fehler sammeln und melden; Import in einer Transaktion mit Rollback bei Fehler (PROD-1).
- **Rechtliche Fehlannahmen im Compliance-Dokument werden als verbindlicher Rechtsrat missverstanden.**
  - *Gegenmassnahme:* Expliziter Disclaimer ('Architektur-Leitplanken, kein Rechtsrat') und Markierung aller rechtlichen Angaben als gegen aktuelle Quellen (revDSG/DSGVO, kantonal) zu prüfen; fachliche/rechtliche Prüfung vor Go-Live verpflichtend (PROD-3).

