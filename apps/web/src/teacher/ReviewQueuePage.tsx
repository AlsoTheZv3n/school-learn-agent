import { Icon } from "../components/Icon";

export default function ReviewQueuePage() {
  return (
    <>
      <div>
        <h2 className="font-title-md text-title-md text-on-surface mb-xs">Review-Queue</h2>
        <p className="font-body-md text-body-md text-on-surface-variant max-w-2xl">
          Niedrig-konfidente Bewertungen warten hier auf deine Freigabe, bevor sie ins Lernmodell
          fliessen — der Mensch im Loop ist Sicherheitsarchitektur, kein Reporting (P6).
        </p>
      </div>
      <div className="bg-surface-container-lowest rounded-xl p-xl shadow-ambient border border-outline-variant/10 flex flex-col items-center text-center gap-md">
        <div className="w-16 h-16 rounded-full bg-secondary-container flex items-center justify-center text-on-secondary-container">
          <Icon name="fact_check" filled className="text-3xl" />
        </div>
        <h3 className="font-title-md text-title-md text-primary">Keine offenen Bewertungen</h3>
        <p className="font-body-md text-body-md text-on-surface-variant max-w-md">
          Sobald der Tutor eine Antwort nur mit geringer Konfidenz bewertet (z. B. offene
          Geschichts-Antworten), erscheint sie hier zur Bestätigung. Bewertungen mit hoher
          Konfidenz (z. B. symbolisch geprüfte Mathe-Aufgaben) fliessen automatisch ein.
        </p>
      </div>
    </>
  );
}
