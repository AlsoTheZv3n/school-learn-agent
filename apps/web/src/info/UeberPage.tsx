import { Icon } from "../components/Icon";

const PRINCIPLES = [
  {
    icon: "child_care",
    title: "Kindersicher zuerst",
    text: "Bewertungen stützen sich auf einen kuratierten Antwortschlüssel — nicht auf freie KI-Generierung. Ein halluzinierter Schlüssel würde ein Kind falsch unterrichten.",
  },
  {
    icon: "supervisor_account",
    title: "Mensch im Loop",
    text: "Eine Lehrperson kann den Lernstand einsehen, verifizieren und eingreifen. Eine KI ist nicht die alleinige Instanz über den Lernweg eines Kindes.",
  },
  {
    icon: "insights",
    title: "Open Learner Model",
    text: "Der Lernstand ist interpretierbar — inklusive seiner Unsicherheit. Die Lehrperson sieht, warum das System eine Einschätzung trifft, und kann sie überschreiben.",
  },
  {
    icon: "shield",
    title: "Datenschutz als Fundament",
    text: "CH/EU-Residenz, PII-Anonymisierung und Zeilen-Isolation sind keine optionalen Features, sondern Voraussetzung.",
  },
];

export default function UeberPage() {
  return (
    <>
      <section>
        <h1 className="font-display-lg text-display-lg text-primary tracking-tight">Über EduSovereign</h1>
        <p className="font-body-lg text-body-lg text-on-surface-variant mt-sm">
          Ein Intelligent Tutoring System: Lernmaterial pro Stufe/Fach, ein individueller Lernstand
          pro Schüler:in, ein Agent, der erklärt und abfragt — und eine Lehrer:innen-Ansicht zur
          Kontrolle und Intervention, auf einer datenschutzkonformen Basis.
        </p>
      </section>
      <section className="grid grid-cols-1 md:grid-cols-2 gap-md">
        {PRINCIPLES.map((p) => (
          <div key={p.title} className="bg-surface-container-lowest rounded-xl p-md shadow-ambient border border-outline-variant/10">
            <div className="flex items-center gap-sm text-secondary mb-sm">
              <Icon name={p.icon} filled className="text-[20px]" />
              <h3 className="font-title-md text-title-md text-primary">{p.title}</h3>
            </div>
            <p className="font-body-md text-body-md text-on-surface-variant">{p.text}</p>
          </div>
        ))}
      </section>
      <section className="bg-secondary-container/40 rounded-xl p-lg border border-secondary/20">
        <div className="flex items-center gap-sm text-secondary mb-sm">
          <Icon name="verified" filled />
          <h3 className="font-title-md text-title-md text-on-surface">Ethical AI Commitment</h3>
        </div>
        <p className="font-body-md text-body-md text-on-surface-variant">
          Generative Freiheit ist auf Erklärungen beschränkt, wo Fehler geringfügig und sofort sichtbar
          sind. Das Lernmodell verbessert sich — nicht der Agent. Verhalten bleibt damit auditierbar,
          und eine Lehrperson behält die Kontrolle.
        </p>
      </section>
    </>
  );
}
