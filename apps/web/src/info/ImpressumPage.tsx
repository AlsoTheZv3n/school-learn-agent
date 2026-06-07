export default function ImpressumPage() {
  return (
    <>
      <section>
        <h1 className="font-display-lg text-display-lg text-primary tracking-tight">Rechtliches</h1>
        <p className="font-body-lg text-body-lg text-on-surface-variant mt-sm">
          Impressum & Nutzungsbedingungen.
        </p>
      </section>
      <section className="bg-surface-container-lowest rounded-xl p-lg shadow-ambient border border-outline-variant/10 flex flex-col gap-md">
        <div>
          <h3 className="font-title-md text-title-md text-primary mb-xs">Impressum</h3>
          <p className="font-body-md text-body-md text-on-surface-variant">
            EduSovereign ist eine Demo-/Prototyp-Anwendung eines Intelligent Tutoring Systems. Diese
            Installation dient der Erprobung und enthält ausschliesslich Mock-Daten. Verantwortliche
            Stelle, Kontakt und Hosting-Region sind vor einem Produktivbetrieb zu ergänzen.
          </p>
        </div>
        <div className="border-t border-outline-variant/20 pt-md">
          <h3 className="font-title-md text-title-md text-primary mb-xs">Nutzungsbedingungen</h3>
          <p className="font-body-md text-body-md text-on-surface-variant">
            Die Nutzung erfolgt im Rahmen der Erprobung. Es werden keine echten personenbezogenen
            Schülerdaten verarbeitet. Vor einem Einsatz mit echten Daten gelten die in den
            Datenschutz-Hinweisen genannten Voraussetzungen (CH/EU-Residenz, AVV, RLS-Garantien).
          </p>
        </div>
      </section>
    </>
  );
}
