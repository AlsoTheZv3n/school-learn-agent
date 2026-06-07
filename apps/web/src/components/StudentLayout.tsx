import { Link, NavLink, Outlet } from "react-router-dom";

import Footer from "./Footer";
import { Icon } from "./Icon";

const LINKS = [
  { to: "/", label: "Heute", end: true },
  { to: "/lernen", label: "Lernen", end: false },
  { to: "/fortschritt", label: "Mein Fortschritt", end: false },
  { to: "/bibliothek", label: "Bibliothek", end: false },
  { to: "/notizen", label: "Notizen", end: false },
];

const BOTTOM = [
  { to: "/", icon: "home", label: "Heute", end: true },
  { to: "/fortschritt", icon: "auto_graph", label: "Fortschritt", end: false },
  { to: "/lernen", icon: "school", label: "Lernen", end: false },
  { to: "/notizen", icon: "chat_bubble", label: "Notizen", end: false },
];

export default function StudentLayout() {
  return (
    <div className="bg-surface text-on-surface min-h-screen flex flex-col">
      <header className="bg-surface shadow-ambient flex justify-between items-center px-gutter md:px-xl w-full sticky top-0 z-50 py-md">
        <div className="flex items-center gap-xl">
          <Link to="/" className="font-headline-lg text-headline-lg font-bold text-primary">
            EduSovereign
          </Link>
          <nav className="hidden lg:flex items-center gap-lg">
            {LINKS.map((l) => (
              <NavLink
                key={l.to}
                to={l.to}
                end={l.end}
                className={({ isActive }) =>
                  `font-title-md text-title-md pb-1 transition-colors ${
                    isActive
                      ? "text-primary border-b-2 border-primary"
                      : "text-on-surface-variant hover:text-primary"
                  }`
                }
              >
                {l.label}
              </NavLink>
            ))}
          </nav>
        </div>
        <div className="flex items-center gap-sm md:gap-md">
          <Link
            to="/teacher"
            className="hidden sm:flex items-center gap-xs font-label-sm text-label-sm text-secondary border border-secondary/40 rounded-full px-sm py-xs hover:bg-secondary-container/40 transition-colors"
          >
            <Icon name="switch_account" className="text-[18px]" /> Lehrer-Ansicht
          </Link>
          <button className="text-on-surface-variant hover:text-primary p-xs rounded-full hover:bg-surface-container-low">
            <Icon name="security" />
          </button>
          <button className="text-on-surface-variant hover:text-primary p-xs rounded-full hover:bg-surface-container-low relative">
            <Icon name="notifications" />
            <span className="absolute top-1 right-1 w-2 h-2 bg-error rounded-full" />
          </button>
          <button className="text-on-surface-variant hover:text-primary p-xs rounded-full hover:bg-surface-container-low">
            <Icon name="account_circle" />
          </button>
        </div>
      </header>

      <main className="flex-1 w-full max-w-[1024px] mx-auto px-gutter md:px-xl py-xl flex flex-col gap-xl pb-32 lg:pb-xl">
        <Outlet />
      </main>

      <nav className="lg:hidden fixed bottom-0 left-0 w-full z-50 flex justify-around items-center px-md bg-surface-container-lowest shadow-[0px_-4px_20px_rgba(45,76,126,0.08)] rounded-t-xl py-sm">
        {BOTTOM.map((b) => (
          <NavLink
            key={b.to + b.label}
            to={b.to}
            end={b.end}
            className={({ isActive }) =>
              `flex flex-col items-center justify-center rounded-xl p-sm ${
                isActive ? "bg-primary-container text-on-primary-container" : "text-on-surface-variant"
              }`
            }
          >
            <Icon name={b.icon} />
            <span className="font-label-sm text-label-sm mt-xs">{b.label}</span>
          </NavLink>
        ))}
      </nav>

      <Footer />
    </div>
  );
}
