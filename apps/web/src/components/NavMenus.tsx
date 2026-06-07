import { useEffect, useRef, useState } from "react";
import type { ReactNode } from "react";
import { Link, useNavigate } from "react-router-dom";

import { api } from "../api/client";
import { useSession } from "../lib/session";
import { Icon } from "./Icon";

const ITEM =
  "flex items-center gap-sm px-sm py-sm rounded-lg hover:bg-surface-container-low text-on-surface font-label-sm text-label-sm transition-colors w-full text-left";

function initialsOf(name: string): string {
  const parts = name.replace(/[:]/g, " ").split(/\s+/).filter(Boolean);
  return ((parts[0]?.[0] ?? "") + (parts[1]?.[0] ?? "")).toUpperCase() || "?";
}

/** Generic icon-button dropdown that closes on outside click / Escape. */
function Menu({
  icon,
  label,
  dot = false,
  width = "w-80",
  render,
}: {
  icon: string;
  label: string;
  dot?: boolean;
  width?: string;
  render: (close: () => void) => ReactNode;
}) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    function onDoc(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") setOpen(false);
    }
    document.addEventListener("mousedown", onDoc);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDoc);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  return (
    <div className="relative" ref={ref}>
      <button
        onClick={() => setOpen((o) => !o)}
        aria-label={label}
        aria-expanded={open}
        className="text-on-surface-variant hover:text-primary transition-colors p-xs rounded-full hover:bg-surface-container-low relative"
      >
        <Icon name={icon} />
        {dot && <span className="absolute top-1 right-1 w-2 h-2 bg-error rounded-full" />}
      </button>
      {open && (
        <div className={`absolute right-0 mt-sm ${width} bg-surface-container-lowest rounded-xl shadow-ambient border border-outline-variant/20 z-[60] overflow-hidden`}>
          {render(() => setOpen(false))}
        </div>
      )}
    </div>
  );
}

// ── 🛡️ Privacy shield ─────────────────────────────────────────────────────────
const SHIELD = [
  { icon: "public", text: "In CH/EU gehostet (revDSG/DSGVO)" },
  { icon: "lock", text: "Zeilen-Isolation per Row-Level Security" },
  { icon: "visibility_off", text: "PII wird vor jedem KI-Aufruf entfernt" },
  { icon: "groups", text: "Aggregate erst ab 10 Lernenden" },
  { icon: "supervisor_account", text: "Eine Lehrperson behält die Kontrolle" },
];

function PrivacyMenu() {
  return (
    <Menu
      icon="security"
      label="Datenschutz-Status"
      width="w-80"
      render={(close) => (
        <div>
          <div className="p-md border-b border-outline-variant/20 bg-secondary-container/40 flex items-center gap-sm">
            <Icon name="verified_user" filled className="text-secondary" />
            <div>
              <p className="font-title-md text-title-md text-on-surface">Privacy Shield</p>
              <p className="font-caption text-caption text-secondary">Aktiv</p>
            </div>
          </div>
          <ul className="p-sm flex flex-col gap-xs">
            {SHIELD.map((s) => (
              <li key={s.text} className="flex items-center gap-sm px-sm py-xs font-label-sm text-label-sm text-on-surface-variant">
                <Icon name={s.icon} className="text-[18px] text-secondary" />
                {s.text}
              </li>
            ))}
          </ul>
          <Link
            to="/datenschutz"
            onClick={close}
            className="block p-md border-t border-outline-variant/20 font-label-sm text-label-sm text-primary hover:bg-surface-container-low transition-colors"
          >
            Zur Datenschutzerklärung →
          </Link>
        </div>
      )}
    />
  );
}

// ── 🔔 Notifications ───────────────────────────────────────────────────────────
interface Notif {
  icon: string;
  title: string;
  body: string;
  to: string;
}

function NotificationsMenu({ role, token }: { role: "student" | "teacher"; token: string }) {
  const [items, setItems] = useState<Notif[]>([]);
  const nav = useNavigate();

  useEffect(() => {
    if (!token) return;
    let active = true;
    if (role === "student") {
      api
        .myNotes(token)
        .then((ns) =>
          active &&
          setItems(
            ns.map((n) => ({
              icon: "campaign",
              title: "Notiz von deiner Lehrperson",
              body: n.body,
              to: "/notizen",
            })),
          ),
        )
        .catch(() => {});
    } else {
      api
        .classes(token)
        .then((cs) => {
          const cid = cs[0]?.class_id ?? null;
          return api.teacherOverview(cid, token);
        })
        .then((o) => {
          if (!active) return;
          const reviews: Notif[] =
            o.kpis.open_reviews > 0
              ? [{ icon: "fact_check", title: `${o.kpis.open_reviews} offene Reviews`, body: "Zur Freigabe bereit", to: "/teacher/review" }]
              : [];
          const att: Notif[] = o.attention.map((a) => ({
            icon: "trending_down",
            title: `${a.name} braucht Aufmerksamkeit`,
            body: a.topic,
            to: `/teacher/student/${a.student_id}`,
          }));
          setItems([...reviews, ...att]);
        })
        .catch(() => {});
    }
    return () => {
      active = false;
    };
  }, [role, token]);

  return (
    <Menu
      icon="notifications"
      label="Benachrichtigungen"
      dot={items.length > 0}
      width="w-96"
      render={(close) => (
        <div>
          <div className="p-md border-b border-outline-variant/20 flex items-center justify-between">
            <p className="font-title-md text-title-md text-on-surface">Benachrichtigungen</p>
            <span className="font-caption text-caption text-on-surface-variant bg-surface-container-high px-sm py-xs rounded-full">{items.length}</span>
          </div>
          <div className="max-h-80 overflow-y-auto">
            {items.length === 0 && (
              <p className="p-md font-body-md text-body-md text-on-surface-variant">Keine neuen Benachrichtigungen.</p>
            )}
            {items.map((n, i) => (
              <button
                key={i}
                onClick={() => {
                  close();
                  nav(n.to);
                }}
                className="w-full text-left p-md flex items-start gap-sm hover:bg-surface-container-low transition-colors border-b border-outline-variant/10 last:border-0"
              >
                <Icon name={n.icon} className="text-[20px] text-secondary mt-0.5" />
                <div className="min-w-0">
                  <p className="font-label-sm text-label-sm text-on-surface">{n.title}</p>
                  <p className="font-caption text-caption text-on-surface-variant truncate">{n.body}</p>
                </div>
              </button>
            ))}
          </div>
        </div>
      )}
    />
  );
}

// ── 👤 Profile ─────────────────────────────────────────────────────────────────
function ProfileMenu({ role, name }: { role: "student" | "teacher"; name: string }) {
  const [readable, setReadable] = useState(() => localStorage.getItem("readable") === "1");

  useEffect(() => {
    document.documentElement.classList.toggle("readable", readable);
    localStorage.setItem("readable", readable ? "1" : "0");
  }, [readable]);

  return (
    <Menu
      icon="account_circle"
      label="Profil"
      width="w-72"
      render={(close) => (
        <div>
          <div className="p-md border-b border-outline-variant/20 flex items-center gap-md">
            <div className="w-10 h-10 rounded-full bg-primary-container text-on-primary-container flex items-center justify-center font-bold">
              {initialsOf(name)}
            </div>
            <div className="min-w-0">
              <p className="font-title-md text-title-md text-on-surface truncate">{name || "Konto"}</p>
              <span className="font-caption text-caption text-secondary">
                {role === "teacher" ? "Lehrperson" : "Schüler:in"}
              </span>
            </div>
          </div>
          <div className="p-xs flex flex-col">
            <Link to={role === "teacher" ? "/" : "/teacher"} onClick={close} className={ITEM}>
              <Icon name="switch_account" className="text-[18px] text-on-surface-variant" />
              {role === "teacher" ? "Zur Schüler-Ansicht" : "Zur Lehrer-Ansicht"}
            </Link>
            <button onClick={() => setReadable((r) => !r)} className={`${ITEM} justify-between`}>
              <span className="flex items-center gap-sm">
                <Icon name="accessibility_new" className="text-[18px] text-on-surface-variant" />
                Dyslexie-Schrift
              </span>
              <span className={`w-9 h-5 rounded-full relative transition-colors ${readable ? "bg-primary" : "bg-surface-container-highest"}`}>
                <span className={`absolute top-0.5 w-4 h-4 rounded-full bg-white transition-all ${readable ? "left-[18px]" : "left-0.5"}`} />
              </span>
            </button>
            {role === "teacher" && (
              <Link to="/teacher/settings" onClick={close} className={ITEM}>
                <Icon name="settings" className="text-[18px] text-on-surface-variant" />
                Einstellungen
              </Link>
            )}
            <button onClick={() => (window.location.href = "/")} className={`${ITEM} text-error`}>
              <Icon name="logout" className="text-[18px]" />
              Abmelden
            </button>
          </div>
        </div>
      )}
    />
  );
}

// ── composed actions for the nav bars ──────────────────────────────────────────
export function NavActions({ role }: { role: "student" | "teacher" }) {
  const { info, studentToken, teacherToken } = useSession();
  const token = role === "student" ? studentToken : teacherToken;
  const name = role === "student" ? info?.student_name ?? "Schüler:in" : "Demo-Lehrperson";
  return (
    <div className="flex items-center gap-sm md:gap-md">
      <PrivacyMenu />
      <NotificationsMenu role={role} token={token} />
      <ProfileMenu role={role} name={name} />
    </div>
  );
}
