import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { api } from "../api/client";
import type { StudentOverview } from "../api/client";
import { Icon } from "../components/Icon";
import { useSession } from "../lib/session";

const SUBJECT_ICON: Record<string, { icon: string; bg: string; fg: string }> = {
  math: { icon: "calculate", bg: "bg-primary-fixed", fg: "text-on-primary-fixed" },
  language: { icon: "menu_book", bg: "bg-secondary-fixed", fg: "text-on-secondary-fixed" },
  history: { icon: "history_edu", bg: "bg-tertiary-fixed", fg: "text-on-tertiary-fixed" },
};

export default function HomePage() {
  const { info, studentToken } = useSession();
  const [data, setData] = useState<StudentOverview | null>(null);
  const [showNote, setShowNote] = useState(true);

  useEffect(() => {
    if (studentToken) {
      api.overview(studentToken).then(setData).catch(() => setData(null));
    }
  }, [studentToken]);

  const name = info?.student_name ?? "";
  const current = data?.current;
  const pct = current ? Math.round(current.mastery * 100) : 0;

  return (
    <>
      {data?.note && showNote && (
        <div className="w-full bg-warning-amber-container text-warning-amber rounded-xl p-md flex items-center justify-between shadow-ambient">
          <div className="flex items-center gap-sm">
            <Icon name="campaign" filled className="text-warning-amber" />
            <p className="font-body-md font-medium">Notiz von deiner Lehrperson: {data.note.body}</p>
          </div>
          <button onClick={() => setShowNote(false)} className="text-warning-amber hover:opacity-70">
            <Icon name="close" />
          </button>
        </div>
      )}

      <section className="mt-sm">
        <h2 className="font-display-lg text-display-lg text-primary tracking-tight">Hallo {name} 👋</h2>
        <p className="font-body-lg text-body-lg text-on-surface-variant mt-sm max-w-2xl">
          Lass uns dort weitermachen, wo du aufgehört hast. Ein bisschen Übung jeden Tag macht den Meister.
        </p>
      </section>

      <section className="grid grid-cols-1 lg:grid-cols-3 gap-lg">
        {/* Weiterlernen */}
        <div className="lg:col-span-2 bg-surface-container-lowest rounded-2xl p-xl shadow-ambient border border-outline-variant/10 flex flex-col justify-between hover:-translate-y-1 transition-transform duration-300">
          <div>
            <div className="flex items-center gap-sm text-secondary mb-md">
              <Icon name="functions" filled className="text-secondary" />
              <span className="font-label-sm text-label-sm uppercase tracking-wider">
                {current?.subject_name ?? "Mathematik"}
              </span>
            </div>
            <h3 className="font-headline-lg text-headline-lg text-primary mb-sm">
              {current?.skill_name ?? "Quadratische Ergänzung"}
            </h3>
            <p className="font-body-md text-on-surface-variant mb-xl">
              Mach dort weiter, wo du aufgehört hast, und festige dein Können Schritt für Schritt.
            </p>
          </div>
          <div>
            <div className="flex justify-between items-end mb-sm">
              <span className="font-label-sm text-label-sm text-on-surface-variant">Dein Fortschritt in diesem Modul</span>
              <span className="font-title-md text-title-md text-primary">{pct}%</span>
            </div>
            <div className="w-full bg-surface-container-high rounded-full h-3 mb-xl overflow-hidden">
              <div className="bg-gradient-to-r from-secondary to-primary h-3 rounded-full" style={{ width: `${pct}%` }} />
            </div>
            <Link
              to="/lernen"
              className="inline-flex w-full md:w-auto bg-primary text-on-primary font-title-md text-title-md py-md px-xl rounded-xl hover:bg-primary-container hover:text-on-primary-container transition-colors items-center justify-center gap-sm"
            >
              Weiterlernen <Icon name="arrow_forward" />
            </Link>
          </div>
        </div>

        {/* Heutiges Ziel */}
        <div className="bg-surface-container-lowest rounded-2xl p-xl shadow-ambient border border-outline-variant/10 flex flex-col items-center justify-center text-center hover:-translate-y-1 transition-transform duration-300">
          <h3 className="font-title-md text-title-md text-primary mb-lg w-full text-left">Heutiges Ziel</h3>
          <div className="relative w-32 h-32 flex items-center justify-center mb-md">
            <svg className="w-full h-full -rotate-90" viewBox="0 0 36 36">
              <path className="text-surface-container-high" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" fill="none" stroke="currentColor" strokeWidth="3" />
              <path className="text-secondary" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" fill="none" stroke="currentColor" strokeDasharray="100, 100" strokeWidth="3" />
            </svg>
            <div className="absolute inset-0 flex items-center justify-center">
              <Icon name="star" filled className="text-secondary text-3xl" />
            </div>
          </div>
          <p className="font-title-md text-title-md text-primary">Geschafft!</p>
          <p className="font-body-md text-on-surface-variant mt-xs">1 von 1 Konzept geübt</p>
        </div>
      </section>

      {/* Deine Fächer */}
      <section>
        <div className="flex items-center justify-between mb-md">
          <h3 className="font-headline-lg text-headline-lg text-primary">Deine Fächer</h3>
          <Link to="/fortschritt" className="font-label-sm text-label-sm text-secondary hover:underline">
            Alle ansehen
          </Link>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-md">
          {(data?.subjects ?? []).map((s) => {
            const m = SUBJECT_ICON[s.key] ?? SUBJECT_ICON.math;
            const p = Math.round(s.mastery * 100);
            return (
              <div key={s.key} className="bg-surface-container-lowest rounded-xl p-md shadow-sm border border-outline-variant/10 flex items-center gap-md">
                <div className={`w-12 h-12 rounded-lg ${m.bg} flex items-center justify-center ${m.fg}`}>
                  <Icon name={m.icon} />
                </div>
                <div className="flex-1">
                  <h4 className="font-title-md text-title-md text-primary">{s.name}</h4>
                  <div className="flex items-center gap-sm mt-xs">
                    <div className="flex-1 bg-surface-container-high rounded-full h-1.5">
                      <div className="bg-secondary h-1.5 rounded-full" style={{ width: `${p}%` }} />
                    </div>
                    <span className="font-caption text-caption text-on-surface-variant">{p}%</span>
                  </div>
                </div>
              </div>
            );
          })}
          {!data && <p className="font-body-md text-on-surface-variant">Lade …</p>}
        </div>
      </section>

      {/* Als Nächstes empfohlen */}
      <section>
        <h3 className="font-headline-lg text-headline-lg text-primary mb-md">Als Nächstes empfohlen</h3>
        <div className="flex flex-col gap-sm">
          {(data?.recommendations ?? []).map((r) => (
            <div key={r.skill_key} className="bg-surface-container-lowest p-md rounded-xl shadow-sm border border-outline-variant/10 flex items-center justify-between group">
              <div className="flex items-center gap-md">
                <div className="w-10 h-10 rounded-full bg-surface-variant flex items-center justify-center text-on-surface-variant">
                  <Icon name="lightbulb" />
                </div>
                <div>
                  <h4 className="font-title-md text-title-md text-primary">{r.name}</h4>
                  <p className="font-body-md text-body-md text-on-surface-variant">{r.subject_name}</p>
                </div>
              </div>
              <Link to="/lernen" className="hidden md:flex items-center gap-xs font-label-sm text-label-sm text-secondary group-hover:bg-secondary-container group-hover:text-on-secondary-container px-sm py-xs rounded-lg transition-colors">
                Starten <Icon name="chevron_right" className="text-sm" />
              </Link>
            </div>
          ))}
          {data && data.recommendations.length === 0 && (
            <p className="font-body-md text-on-surface-variant">Aktuell keine Empfehlungen — gut gemacht!</p>
          )}
        </div>
      </section>
    </>
  );
}
