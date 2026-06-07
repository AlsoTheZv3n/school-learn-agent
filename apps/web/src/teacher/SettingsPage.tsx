import { Icon } from "../components/Icon";

export default function SettingsPage() {
  return (
    <>
      <div>
        <h2 className="font-title-md text-title-md text-on-surface mb-xs">Einstellungen</h2>
        <p className="font-body-md text-body-md text-on-surface-variant">Plattform- und Datenschutz-Einstellungen.</p>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-md">
        <div className="bg-surface-container-lowest rounded-xl p-md shadow-ambient border border-outline-variant/10">
          <div className="flex items-center gap-sm text-primary mb-sm">
            <Icon name="shield" />
            <h3 className="font-title-md text-title-md">Datenschutz</h3>
          </div>
          <p className="font-body-md text-body-md text-on-surface-variant">
            Daten in CH/EU gehostet (revDSG/DSGVO). PII wird vor jedem LLM-Aufruf entfernt; Lernende
            sehen nur eigene Daten (RLS). Aggregate erst ab {">="} 10 Lernenden.
          </p>
        </div>
        <div className="bg-surface-container-lowest rounded-xl p-md shadow-ambient border border-outline-variant/10">
          <div className="flex items-center gap-sm text-primary mb-sm">
            <Icon name="accessibility_new" />
            <h3 className="font-title-md text-title-md">Barrierefreiheit</h3>
          </div>
          <p className="font-body-md text-body-md text-on-surface-variant">
            Hoher Kontrast, grosse Klickflächen, Tastatur-Navigation; optionale Dyslexie-Schrift.
            <span className="block mt-xs font-caption text-caption text-outline">In Vorbereitung.</span>
          </p>
        </div>
      </div>
    </>
  );
}
