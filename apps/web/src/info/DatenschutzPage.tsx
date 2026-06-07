import { Icon } from "../components/Icon";

const POINTS = [
  {
    icon: "public",
    title: "Datenresidenz CH/EU",
    text: "Datenbank und – falls extern – die KI-Inferenz laufen in einer CH/EU-Region (revDSG/DSGVO). Mock- und Echtdaten teilen nie dieselbe Datenbank.",
  },
  {
    icon: "lock",
    title: "Isolation per Row-Level Security",
    text: "Wer eingeloggt ist, sieht ausschliesslich eigene Zeilen — erzwungen in der Datenbank, nicht durch App-Logik. Selbst eine fehlerhafte Abfrage liefert keine fremden Daten.",
  },
  {
    icon: "visibility_off",
    title: "PII-Minimierung",
    text: "Es werden nur nötige Daten gespeichert (kein Freitext-Profil). Vor jedem externen KI-Aufruf werden Namen, Daten und E-Mails entfernt; das Modell erhält nur IDs und Skill-Bezeichner.",
  },
  {
    icon: "groups",
    title: "Min-Cohort-Schwelle",
    text: "Klassen-Auswertungen werden erst ab 10 Lernenden angezeigt — kleinere Gruppen würden eine de-anonymisierte Einzelauskunft ermöglichen.",
  },
  {
    icon: "auto_delete",
    title: "Aufbewahrung & Löschung",
    text: "Definierte Aufbewahrungsfenster je Datenkategorie; ein Löschpfad pro Lernende:r entfernt alle personenbezogenen Spuren (Kaskadenlöschung im Schema vorbereitet).",
  },
  {
    icon: "handshake",
    title: "Auftragsverarbeitung",
    text: "Bei externer KI-Nutzung sind ein Auftragsverarbeitungsvertrag (AVV/DPA) und ein No-Training-Setting erforderlich — sonst läuft alles auf einem lokalen Modell.",
  },
];

export default function DatenschutzPage() {
  return (
    <>
      <section>
        <h1 className="font-display-lg text-display-lg text-primary tracking-tight">Datenschutz</h1>
        <p className="font-body-lg text-body-lg text-on-surface-variant mt-sm">
          Diese Plattform verarbeitet Daten über Minderjährige. Datensicherheit ist Voraussetzung,
          kein Zusatz. Die folgenden Punkte sind die Architektur-Leitplanken — kein Rechtsrat.
        </p>
      </section>
      <section className="grid grid-cols-1 md:grid-cols-2 gap-md">
        {POINTS.map((p) => (
          <div key={p.title} className="bg-surface-container-lowest rounded-xl p-md shadow-ambient border border-outline-variant/10">
            <div className="flex items-center gap-sm text-secondary mb-sm">
              <Icon name={p.icon} filled className="text-[20px]" />
              <h3 className="font-title-md text-title-md text-primary">{p.title}</h3>
            </div>
            <p className="font-body-md text-body-md text-on-surface-variant">{p.text}</p>
          </div>
        ))}
      </section>
      <p className="font-caption text-caption text-on-surface-variant">
        Demo-Hinweis: Vor einem Produktivbetrieb mit echten Schülerdaten ist eine fachliche/rechtliche
        Prüfung gegen aktuelle Quellen (revDSG/DSGVO, kantonale/schulische Vorgaben) erforderlich.
      </p>
    </>
  );
}
