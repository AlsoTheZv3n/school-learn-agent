import { useEffect, useState } from "react";

import { api } from "../api/client";
import type { StudentSkillMastery } from "../api/client";
import { useSession } from "../lib/session";

function stateOf(mastery: number, attempts: number) {
  if (mastery >= 0.8) return { label: "gemeistert", cls: "bg-secondary-container text-on-secondary-container" };
  if (attempts > 0) return { label: "in Arbeit", cls: "bg-tertiary-fixed text-on-tertiary-fixed" };
  return { label: "neu", cls: "bg-surface-variant text-on-surface-variant" };
}

export default function ProgressPage() {
  const { studentToken } = useSession();
  const [rows, setRows] = useState<StudentSkillMastery[]>([]);

  useEffect(() => {
    if (studentToken) api.myMastery(studentToken).then(setRows).catch(() => setRows([]));
  }, [studentToken]);

  return (
    <>
      <section>
        <h2 className="font-display-lg text-display-lg text-primary tracking-tight">Mein Fortschritt</h2>
        <p className="font-body-lg text-body-lg text-on-surface-variant mt-sm max-w-2xl">
          Dein Lernstand pro Konzept — ruhig dargestellt, Schritt für Schritt.
        </p>
      </section>
      <section className="bg-surface-container-lowest rounded-2xl p-lg shadow-ambient border border-outline-variant/10 flex flex-col gap-lg">
        {rows.map((r) => {
          const pct = Math.round(r.mastery * 100);
          const st = stateOf(r.mastery, r.attempts_count);
          return (
            <div key={r.skill_id}>
              <div className="flex items-center justify-between mb-xs">
                <span className="font-title-md text-title-md text-primary">{r.name}</span>
                <span className={`font-label-sm text-label-sm px-sm py-xs rounded-full ${st.cls}`}>{st.label}</span>
              </div>
              <div className="flex items-center gap-sm">
                <div className="flex-1 bg-surface-container-high rounded-full h-2">
                  <div className="bg-gradient-to-r from-secondary to-primary h-2 rounded-full" style={{ width: `${pct}%` }} />
                </div>
                <span className="font-label-sm text-label-sm text-on-surface-variant w-10 text-right">{pct}%</span>
              </div>
            </div>
          );
        })}
        {rows.length === 0 && (
          <p className="font-body-md text-on-surface-variant">Noch keine Daten — starte eine Lernsession!</p>
        )}
      </section>
    </>
  );
}
