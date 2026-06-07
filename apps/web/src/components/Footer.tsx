export default function Footer() {
  return (
    <footer className="bg-surface-dim w-full py-xl border-t border-outline-variant/20 flex flex-col items-center justify-center gap-md text-center px-gutter mt-auto">
      <div>
        <p className="font-caption text-caption text-on-surface-variant">
          © 2026 EduSovereign. 🇨🇭 In CH/EU gehostet
        </p>
        <p className="font-label-sm text-label-sm mt-xs underline decoration-secondary text-primary">
          Eine Lehrperson behält die Kontrolle
        </p>
      </div>
      <div className="flex flex-wrap items-center justify-center gap-md">
        <a className="font-caption text-caption text-on-surface-variant hover:text-primary transition-colors" href="#">
          Datenschutz
        </a>
        <span className="text-outline-variant">•</span>
        <a className="font-caption text-caption text-on-surface-variant hover:text-primary transition-colors" href="#">
          Nutzungsbedingungen
        </a>
        <span className="text-outline-variant">•</span>
        <a className="font-caption text-caption text-on-surface-variant hover:text-primary transition-colors" href="#">
          Ethical AI Commitment
        </a>
      </div>
    </footer>
  );
}
