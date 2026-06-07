# UI/UX-Redesign-Plan (für Google Stitch)

Ziel: aus dem funktionalen Skelett eine vollwertige, kontextreiche Oberfläche machen —
mit **Navigation, Footer, mehreren Seiten und Detailtiefe** — ohne die Prinzipien zu
brechen (P5 ruhige Schüler-/dichte Lehrersicht, Mensch-im-Loop sichtbar, kindersicher,
CH/EU). Dieses Dokument ist die **Design-Vorlage**: oben das Konzept, unten die
**Stitch-Prompts** zum Kopieren.

---

## 0. So nutzt du es mit Stitch

1. **Erst den „Design-System"-Prompt** (§6.0) in Stitch geben → setzt Marke, Farben,
   Typografie, Komponenten-Stil. Zwei Stimmungen: **„calm"** (Schüler) und **„dense"** (Lehrer).
2. Dann **pro Screen** den jeweiligen Prompt (§6.1–§6.x). Schüler-Screens im calm-Stil,
   Lehrer-Screens im dense-Stil generieren.
3. Hell- **und** Dunkelmodus generieren lassen.
4. Danach **Layouts zurück an mich** (Screenshots **oder** Stitch-Code/HTML) → ich setze
   sie als React-Komponenten in `apps/web` um, verdrahte die API und ergänze Routing/Nav/Footer.

---

## 1. Designprinzipien & Tonalität

| | **Schülerseite (calm)** | **Lehrerseite (dense)** |
|---|---|---|
| Stimmung | ruhig, warm, ermutigend, viel Weissraum | sachlich, datenreich, kompakt |
| Layout | schmal zentriert (max ~720px), eine Sache zur Zeit | breit, Sidebar + Tabellen/Charts |
| Typografie | gross, freundlich | dichter, funktional |
| Mastery | sanftes % / Balken (Unterstufe: Sterne/versteckt) | Balken **+ Unsicherheitsband** |
| Aktion | lernen/antworten | verifizieren/eingreifen |

**Quer über beide:**
- **Vertrauens-/Safety-Signale:** Badge „🇨🇭 In CH/EU gehostet · DSG/DSGVO", „Mensch-im-Loop"-Hinweis, datenschutzfreundlich.
- **Alters-Varianten:** Default **Sekundarstufe** (Text, Tippfeld). Variante **Unterstufe** (weniger Text, Icons, grosse Tap-Targets, Mastery für das Kind **verborgen**).
- **Barrierefreiheit:** hoher Kontrast, grosse Klickflächen, Tastatur-Navigation, optionale Dyslexie-Schrift, Hell/Dunkel.
- **Palette (Vorschlag, in Stitch anpassbar):** ruhiges Indigo/Teal als Primär, warmes Bernstein/Koralle als Akzent, sanfte Neutraltöne; Erfolg = ruhiges Grün, Hinweis = Bernstein, Fehler = gedämpftes Rot. Keine grellen Farben.

---

## 2. Globale Struktur (Shell)

**Top-Nav – Schüler (schlank):** Logo links · Links „Heute", „Lernen", „Mein Fortschritt",
„Bibliothek", „Notizen" · rechts Sprache, Avatar/Name → Menü (Einstellungen, Abmelden).

**Sidebar – Lehrer (dicht):** Logo oben · Einträge „Übersicht", „Klassen", „Review-Queue",
„Curriculum", „Berichte", „Einstellungen" · unten Profilblock (Name, Rolle, Abmelden) ·
einklappbar.

**Footer (beide):** drei Spalten — *Produkt* (Über, Hilfe/FAQ, Was ist ein ITS?), *Rechtliches*
(Datenschutz, Impressum, Compliance/AVV), *Kontakt/Support* · darunter Zeile mit Badge
„🇨🇭 In CH/EU gehostet", Sprachumschalter (DE/FR/IT/EN), Versionsnummer, dezenter Satz
„Eine Lehrperson behält die Kontrolle — keine KI entscheidet allein."

---

## 3. Seitenkarte (Information Architecture)

**Schüler:** Login → **Heute (Home)** → **Lernsession** → **Mein Fortschritt** →
**Bibliothek** (Themen/Konzept-Detail) → **Notizen** → **Profil/Einstellungen** → Hilfe.

**Lehrer:** Login → **Dashboard/Übersicht** → **Klassen** → **Klassen-Detail** →
**Schüler-Detail (Open Learner Model)** → **Review-Queue** → **Curriculum** → **Berichte** →
**Profil/Einstellungen** → Hilfe.

**Gemeinsam/System:** Über/About, Datenschutz, Impressum, 404, globale Zustände
(Loading-Skeleton, Empty-State, Fehler-Toast, „zu wenige Lernende"-Hinweis).

---

## 4. Seiten im Detail

### Schüler

**S1 · Login / Anmeldung** — zentrierte Karte, Logo, Begrüssung, Anmeldebutton (später IdP),
Vertrauens-Badges, Footer.

**S2 · Heute (Home)** — Begrüssung „Hallo [Name] 👋"; grosse **„Weiterlernen"-Karte**
(zuletzt bearbeitetes Konzept + Mini-Fortschritt + CTA); **„Heutiges Ziel"** (z. B. „1 Konzept
üben", Fortschrittsring); **„Deine Fächer"** als Karten mit sanftem Gesamtfortschritt;
**„Als Nächstes empfohlen"** (aus dem Voraussetzungs-Graph); **Banner Lehrernotiz**, falls
vorhanden; optionaler sanfter Streak. Nav + Footer.

**S3 · Lernsession** (Kern) — schmal, ruhig. Breadcrumb „Mathe › Quadratische Ergänzung",
**„Konzept 2 von 5"**-Fortschritt. **Erklärungskarte** (Agent). **Aufgabe** gross + Antwortfeld
(Tippen oder Multiple-Choice je Item) + „Antwort absenden". **Feedback-Zustände**: richtig
(ruhiges Grün, ermutigend) / noch nicht (sanft, bietet Hinweis). **Helfer-Leiste** „Anders
erklären / Hinweis / Wozu?" → Antworten als Tutor-Bubbles (Thread). **MasteryBar** dezent
(Unterstufe: Sterne / verborgen). Fusszeile „Nächste Aufgabe / Session beenden". Dezenter
Lehrernotiz-Hinweis.

**S4 · Mein Fortschritt** — pro Fach Abschnitt; **Skill-Liste** mit sanftem Fortschritt
(Balken/% oder Sterne) und Zuständen *gemeistert / in Arbeit / neu*; optional
**„Lernpfad"-Visualisierung** (Voraussetzungs-Graph als sanfte Knotenkette: gemeistert=grün,
aktuell=Akzent, gesperrt=grau); „Zuletzt gemeistert" + „Empfohlen". **Keine Unsicherheit (P5).**

**S5 · Bibliothek (Themen) + Konzept-Detail** — Browsen der kuratierten Erklärungen pro
Fach/Thema; Themenkarten + Suche. Detail: Prosa-Erklärung, **„Verwandte Themen"** (Wikilinks),
CTA „Übung starten".

**S6 · Notizen** — Liste der Lehrernotizen über mich (Mensch-im-Loop sichtbar, P6); je Notiz:
Lehrperson, Skill-Bezug, Text, Datum.

**S7 · Profil & Einstellungen** — Name, Stufe, Sprache, **Darstellungsmodus
(Sekundar/Unterstufe)**, Schriftgrösse/Dyslexie-Font, Hell/Dunkel, Datenschutz-Link.

**S8 · Hilfe/FAQ.**

### Lehrer

**T1 · Login.**

**T2 · Dashboard / Übersicht** — **KPI-Reihe** (aktive Schüler:innen, Ø-Mastery der erlaubten
Kohorten, offene Reviews, Auffälligkeiten); **„Braucht Aufmerksamkeit"** (niedrige Mastery /
Stagnation / niedrige Grader-Konfidenz); **„Review-Queue"-Karte** (offene, nicht zementierte
Bewertungen, P6) mit CTA; **„Letzte Aktivität"-Feed**; Klassen-Schnellzugriff. Sidebar.

**T3 · Klassen** — Liste eigener Klassen (RLS); je Klasse: Anzahl, Ø, letzte Aktivität,
Heatmap-Vorschau.

**T4 · Klassen-Detail** — **Roster-Tabelle** (Name, Ø-Mastery, letzte Aktivität, Flags;
sortier-/filterbar); **Skill-Heatmap** (Schüler × Skill, Farbskala; Min-Cohort: Aggregat-Zeile
„zu wenige" bei n < k); **Verteilungs-Charts** pro Skill (Min-Cohort-geschützt → „zu wenige
Lernende" statt Zahlen).

**T5 · Schüler-Detail (Open Learner Model)** — Kopf (Name, Stufe, Klasse, letzte Aktivität);
**Skill-Tabelle mit Mastery + Unsicherheit** (Balken + Unsicherheitsband / „n Versuche", Trend);
**„Warum?"** je Skill aufklappbar → **Versuchs-Timeline** (Aufgabe, Antwort, korrekt?, Zeit) +
BKT-Schätzung erklärt; **Voraussetzungs-Graph** (was fehlt); **Interventions-Panel** (Notiz
schreiben → erscheint beim Schüler; Mastery überschreiben mit Begründung/Audit; „Für Follow-up
markieren"); optional Kohorten-Vergleich (Min-Cohort).

**T6 · Review-Queue (P6)** — Liste offener, niedrig-konfidenter Bewertungen (z. B. offene
History-Antworten); je Eintrag: Schüler, Aufgabe, Antwort, System-Vorschlag + Konfidenz, Rubric;
Aktionen **Bestätigen / Überschreiben / Notiz** — erst danach fliesst es ins Learner-Modell.

**T7 · Curriculum / Inhalte** — Domain-Modell sichtbar: **Skill-Graph** (Fächer › Skills ›
Voraussetzungen), Content-Notizen, **Items** (kuratierte Aufgaben + Answer-Keys, read-only);
zeigt transparent, *was* unterrichtet wird.

**T8 · Berichte** — Klassen-/Kohorten-Reports mit Zeitraum-Filter, Export (PDF/CSV),
**Min-Cohort durchgesetzt**.

**T9 · Profil & Einstellungen · T10 · Hilfe/Doku.**

### Gemeinsam/System
Über/About (die Prinzipien erklärt: kindersicher, Lehrer-im-Loop, CH/EU), Datenschutz
(verlinkt `docs/compliance.md`-Inhalte), Impressum, 404, Wartung/Fehler; globale Zustände:
Loading-Skeletons, Empty-States, Fehler-Toasts, Min-Cohort-Hinweis.

---

## 5. Komponenten-Bibliothek (wiederverwendbar)

Buttons (primär/sekundär/ghost) · Cards · **KPI/Stat-Card** · **DataTable** (sortier-/filterbar) ·
**Heatmap** · **Distribution/BarChart** · **MasteryMeter** in 3 Varianten (Schüler %/Balken ·
Lehrer Balken+Unsicherheitsband · Unterstufe Sterne/versteckt) · **Badges** (gemeistert/in
Arbeit/neu; Safety/CH-EU) · **Banner** (Lehrernotiz; Min-Cohort „zu wenige"; Info/Warnung) ·
**TutorBubble** (Erklärung/Hinweis) · **Timeline** (Versuche) · Breadcrumbs · Tabs · **Modal**
(Override mit Audit) · Toast · Empty/Loading/Skeleton/Error · Avatar · LanguageSwitcher ·
ThemeToggle · SearchInput.

---

## 6. Stitch-Prompts (zum Kopieren)

> Schreibstil: englische Struktur + **deutsche UI-Texte in Anführungszeichen** (damit Stitch die
> echten Labels rendert). Generiere zuerst 6.0, dann die Screens.

### 6.0 · Design-System (zuerst!)
```
Design a web design system for "ITS" — a privacy-first intelligent tutoring platform
for schools (minors) in Switzerland/EU. Two coexisting moods: a CALM, warm, spacious
student experience and a DENSE, data-rich teacher experience that share one brand.
Palette: calm indigo/teal primary, warm amber/coral accent, soft neutral grays;
success = calm green, warning = amber, error = muted red. Friendly rounded geometric
sans typography, generous spacing, 12px radius cards, soft shadows. Provide light and
dark themes. Components: top nav, collapsible sidebar, footer with a "🇨🇭 In CH/EU
gehostet · DSG/DSGVO" trust badge and a line "Eine Lehrperson behält die Kontrolle —
keine KI entscheidet allein.", primary/secondary/ghost buttons, cards, KPI stat cards,
sortable data table, heatmap, bar/distribution chart, a "mastery meter" (a gentle
percent bar AND a variant with an uncertainty band), badges, info/warning banners,
chat-style tutor bubbles, timeline, modal, toast, empty/loading/error states. Tone:
trustworthy, kind, calm; never flashy. Accessibility: high contrast, large tap targets,
keyboard friendly, optional dyslexia font.
```

### 6.1 · Schüler – Heute (Home) `[calm]`
```
Design the student HOME screen "Heute" for the ITS platform (calm mood, centered max
~960px, slim top nav with links "Heute", "Lernen", "Mein Fortschritt", "Bibliothek",
"Notizen"). Sections: a warm greeting "Hallo Mia 👋"; a large "Weiterlernen" card showing
the last concept (title "Quadratische Ergänzung", a gentle progress bar, big CTA
"Weiterlernen"); a "Heutiges Ziel" card with a progress ring ("1 von 1 Konzept geübt");
a "Deine Fächer" row of subject cards (Mathematik, Sprache, Geschichte) each with a soft
overall progress; an "Als Nächstes empfohlen" list of 2–3 suggested skills; a dismissible
amber banner "Notiz von Frau Meier: Schön, dass du dranbleibst!". Footer with CH/EU trust
badge. Encouraging, lots of whitespace, large friendly type.
```

### 6.2 · Schüler – Lernsession `[calm]`
```
Design the student LEARN SESSION screen (calm, narrow centered ~720px). Top: breadcrumb
"Mathe › Quadratische Ergänzung" and a subtle step indicator "Konzept 2 von 5". An
explanation card from the tutor (soft indigo background). A large question "Multipliziere
aus: (x + 1)²" with a text answer field and a primary button "Antwort absenden". Below, a
secondary helper button row: "Anders erklären", "Hinweis", "Wozu?". Show a chat-style tutor
bubble thread for explanations/hints. A gentle mastery bar at the top labeled "Quadratische
Ergänzung: 60%" (NO uncertainty). A success feedback state (calm green "Richtig! 🎉") and a
soft "noch nicht" state that offers a hint. Footer-of-session buttons "Nächste Aufgabe" and
"Session beenden". Calm, encouraging, one thing at a time.
```

### 6.3 · Schüler – Mein Fortschritt `[calm]`
```
Design the student "Mein Fortschritt" screen (calm). Per subject section ("Mathematik")
with a skill list; each skill row shows name and a gentle progress bar with a state chip
"gemeistert" / "in Arbeit" / "neu" — NO uncertainty numbers. Include a soft "Lernpfad"
visualization: a horizontal chain of prerequisite skill nodes (mastered = green, current =
accent, locked = gray) e.g. "Lineare Gleichungen → Quadratische Ergänzung → Lösungsformel".
A "Zuletzt gemeistert" and "Als Nächstes empfohlen" panel. Reassuring, not competitive.
```

### 6.4 · Schüler – Bibliothek + Konzept-Detail `[calm]`
```
Design two student screens: (1) "Bibliothek" — a searchable grid of topic cards grouped by
subject, each card a concept title + one-line summary. (2) Concept detail — a clean reading
view with the prose explanation, a "Verwandte Themen" chip row (linked concepts), and a CTA
"Übung starten". Calm, book-like, comfortable reading width.
```

### 6.5 · Lehrer – Dashboard/Übersicht `[dense]`
```
Design the teacher DASHBOARD for the ITS platform (dense mood, collapsible left sidebar with
"Übersicht", "Klassen", "Review-Queue", "Curriculum", "Berichte", "Einstellungen"). Top: a
row of 4 KPI stat cards ("Aktive Schüler:innen 24", "Ø Mastery 68%", "Offene Reviews 3",
"Auffälligkeiten 2"). A "Braucht Aufmerksamkeit" table (student, subject, signal: low mastery
/ stagnation / low grader confidence). A "Review-Queue" card with count + CTA "Jetzt prüfen".
A "Letzte Aktivität" feed. A class quick-switch. Information-dense but scannable, data-vis
friendly.
```

### 6.6 · Lehrer – Klassen-Detail `[dense]`
```
Design the teacher CLASS DETAIL screen (dense). A sortable/filterable roster data table
(Name, Ø-Mastery, Letzte Aktivität, Flags). A skill heatmap (rows = students, columns =
skills, color scale = mastery) where an aggregate row shows "zu wenige" when a cohort is
below the privacy threshold. A per-skill distribution bar chart; if the cohort is too small,
show a neutral note "Zu wenige Lernende für eine anonyme Auswertung." instead of numbers.
Compact, analytical.
```

### 6.7 · Lehrer – Schüler-Detail (Open Learner Model) `[dense]`
```
Design the teacher STUDENT DETAIL "Open Learner Model" screen (dense). Header: student name,
grade, class, last active. A skill table where each row shows mastery AND an uncertainty band
(a bar with a lighter ± range) plus attempts count and a trend arrow. Each skill row is
expandable to a "Warum?" panel with an attempts timeline (question, answer, correct?, time)
and a short note explaining the estimate. A prerequisite graph showing missing prerequisites.
A right-side "Intervention" panel: a note textarea ("erscheint beim Schüler"), an override
mastery control with a reason field (audited), and a "Für Follow-up markieren" toggle.
Transparent, trustworthy, shows the WHY behind the estimate.
```

### 6.8 · Lehrer – Review-Queue `[dense]`
```
Design the teacher REVIEW QUEUE screen (dense), the human-in-the-loop gate. A list of pending
low-confidence assessments; each item card shows the student, the question, the student's
answer, the system's suggested verdict with a confidence meter, and the grading rubric.
Actions per item: "Bestätigen", "Überschreiben" (correct/incorrect toggle), "Notiz". A header
note explains "Erst nach Bestätigung fliesst das Ergebnis ins Lernmodell." Focused, decisive.
```

### 6.9 · Lehrer – Curriculum `[dense]`
```
Design the teacher CURRICULUM screen (dense): a visual skill graph (subjects → skills →
prerequisite edges), a side list of content notes, and a panel listing curated assessment
items (prompt + answer key, read-only) with a badge "kuratiert". Shows transparently what is
taught and assessed.
```

---

## 7. Entscheidungen, die du (in Stitch) anpassen kannst
- **Primäre Altersstufe:** Default Sekundarstufe; Unterstufe als Variante (weniger Text,
  Mastery für das Kind verborgen).
- **Palette & Verspieltheit:** Vorschlag Indigo/Teal + Bernstein, freundlich-sachlich; gern
  spielerischer für Schüler, nüchterner für Lehrer.
- **Dark Mode:** ja (beide).
- **Charts:** Heatmap + Balken vorgeschlagen; falls zu komplex, erst Tabellen.

---

## 8. Was nach dem Design passiert (Umsetzung durch mich)

Wenn du die Layouts zurückgibst (Screenshots **oder** Stitch-Code/HTML), setze ich sie als
React-Komponenten in `apps/web` um: **react-router** für echtes Multipage-Routing, Nav +
Sidebar + Footer als Shell, die Seiten als Routen, alles an die API verdrahtet und
prinzipientreu (P5-Trennung, Min-Cohort-Hinweise, Lehrernotiz beim Schüler).

**Nötige Backend-Ergänzungen** (kleine, klar abgegrenzte Endpoints — baue ich mit):
- Schüler: `GET /student/home` (Zusammenfassung), `GET /student/subjects`,
  `GET /student/notes` (Lehrernotizen), Content-Browsing `GET /content/notes`,
  `GET /content/note/{id}`.
- Lehrer: `GET /teacher/classes`, `GET /teacher/class/{id}/roster`,
  `GET /teacher/class/{id}/overview` (Heatmap/Verteilung, Min-Cohort),
  `GET /teacher/review-queue`, `POST /teacher/review/{id}/confirm`,
  `GET /teacher/student/{id}/attempts` (Timeline), `GET /curriculum` (Skill-Graph + Items).

Reihenfolge der Umsetzung: Shell (Nav/Footer/Routing) → Schüler-Screens → Lehrer-Screens →
neue Endpoints parallel. Bestehende Tests/CI bleiben grün; neue Endpoints kommen mit Tests.
