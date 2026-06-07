import { Link } from "react-router-dom";

export default function Footer() {
  return (
    <footer className="bg-surface-dim w-full py-xl border-t border-outline-variant/20 flex flex-col items-center justify-center gap-md text-center px-gutter mt-auto">
      <div>
        <p className="font-caption text-caption text-on-surface-variant">
          © 2026 EduSovereign. 🇨🇭 In CH/EU gehostet
        </p>
        <Link
          to="/ueber"
          className="inline-block font-label-sm text-label-sm mt-xs underline decoration-secondary text-primary hover:text-secondary transition-colors"
        >
          Eine Lehrperson behält die Kontrolle
        </Link>
      </div>
      <div className="flex flex-wrap items-center justify-center gap-md">
        <Link to="/datenschutz" className="font-caption text-caption text-on-surface-variant hover:text-primary transition-colors">
          Datenschutz
        </Link>
        <span className="text-outline-variant">•</span>
        <Link to="/impressum" className="font-caption text-caption text-on-surface-variant hover:text-primary transition-colors">
          Nutzungsbedingungen
        </Link>
        <span className="text-outline-variant">•</span>
        <Link to="/ueber" className="font-caption text-caption text-on-surface-variant hover:text-primary transition-colors">
          Ethical AI Commitment
        </Link>
      </div>
    </footer>
  );
}
