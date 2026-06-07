import { Link, Outlet, useNavigate } from "react-router-dom";

import Footer from "./Footer";
import { Icon } from "./Icon";

// Lightweight chrome for the legal/info pages (Datenschutz, Über, Impressum) —
// reachable from both the student and teacher footers.
export default function InfoLayout() {
  const nav = useNavigate();
  return (
    <div className="bg-surface text-on-surface min-h-screen flex flex-col">
      <header className="bg-surface shadow-ambient flex justify-between items-center px-gutter md:px-xl w-full sticky top-0 z-50 py-md">
        <Link to="/" className="font-headline-lg text-headline-lg font-bold text-primary">EduSovereign</Link>
        <button
          onClick={() => nav(-1)}
          className="flex items-center gap-xs font-label-sm text-label-sm text-on-surface-variant hover:text-primary transition-colors"
        >
          <Icon name="arrow_back" className="text-[18px]" /> Zurück
        </button>
      </header>
      <main className="flex-1 w-full max-w-[800px] mx-auto px-gutter md:px-xl py-xl flex flex-col gap-lg">
        <Outlet />
      </main>
      <Footer />
    </div>
  );
}
