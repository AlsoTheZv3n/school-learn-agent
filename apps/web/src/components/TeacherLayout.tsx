import { Link, NavLink, Outlet } from "react-router-dom";

import Footer from "./Footer";
import { Icon } from "./Icon";
import { NavActions } from "./NavMenus";

const NAV = [
  { to: "/teacher", icon: "dashboard", label: "Dashboard", end: true },
  { to: "/teacher/classes", icon: "group", label: "Klassen", end: false },
  { to: "/teacher/review", icon: "fact_check", label: "Review-Queue", end: false },
  { to: "/teacher/settings", icon: "settings", label: "Einstellungen", end: false },
];

export default function TeacherLayout() {
  return (
    <div className="bg-background text-on-background min-h-screen flex flex-col lg:flex-row">
      <nav className="hidden lg:flex flex-col w-64 h-screen p-md gap-sm bg-surface-container-low border-r border-outline-variant/10 sticky left-0 top-0">
        <div className="mb-xl px-sm">
          <h1 className="font-headline-lg-mobile text-headline-lg-mobile text-primary">Institution Portal</h1>
          <p className="font-caption text-caption text-on-surface-variant mt-xs">Teacher View</p>
        </div>
        <ul className="flex flex-col gap-xs flex-grow">
          {NAV.map((i) => (
            <li key={i.to}>
              <NavLink
                to={i.to}
                end={i.end}
                className={({ isActive }) =>
                  `flex items-center gap-md px-md py-sm rounded-lg transition-all ${
                    isActive
                      ? "bg-surface-container-high text-secondary font-bold border-l-4 border-secondary"
                      : "text-on-surface-variant hover:bg-surface-container-high"
                  }`
                }
              >
                <Icon name={i.icon} />
                <span className="font-label-sm text-label-sm">{i.label}</span>
              </NavLink>
            </li>
          ))}
        </ul>
        <div className="mt-auto flex flex-col gap-xs border-t border-outline-variant/20 pt-sm">
          <Link
            to="/"
            className="flex items-center gap-md px-md py-sm rounded-lg text-secondary hover:bg-surface-container-high transition-all"
          >
            <Icon name="switch_account" />
            <span className="font-label-sm text-label-sm">Schüler-Ansicht</span>
          </Link>
          <Link
            to="/datenschutz"
            className="flex items-center gap-md px-md py-sm rounded-lg text-on-surface-variant hover:bg-surface-container-high transition-all"
          >
            <Icon name="shield" />
            <span className="font-label-sm text-label-sm">Privacy Center</span>
          </Link>
        </div>
      </nav>

      <div className="flex-1 flex flex-col min-w-0">
        <header className="flex justify-between items-center px-gutter md:px-xl w-full sticky top-0 z-50 bg-surface shadow-ambient py-md">
          <div className="flex items-center gap-md lg:hidden">
            <span className="font-headline-lg text-headline-lg font-bold text-primary">EduSovereign</span>
          </div>
          <div className="hidden lg:block" />
          <NavActions role="teacher" />
        </header>
        <main className="flex-1 p-gutter md:p-xl space-y-xl">
          <Outlet />
        </main>
        <Footer />
      </div>
    </div>
  );
}
