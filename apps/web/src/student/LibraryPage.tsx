import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { api } from "../api/client";
import type { Curriculum } from "../api/client";
import { Icon } from "../components/Icon";

export default function LibraryPage() {
  const [cur, setCur] = useState<Curriculum | null>(null);
  const [q, setQ] = useState("");

  useEffect(() => {
    api.curriculum().then(setCur).catch(() => setCur(null));
  }, []);

  const skills = (cur?.skills ?? []).filter((s) => s.name.toLowerCase().includes(q.toLowerCase()));

  return (
    <>
      <section>
        <h2 className="font-display-lg text-display-lg text-primary tracking-tight">Bibliothek</h2>
        <p className="font-body-lg text-body-lg text-on-surface-variant mt-sm max-w-2xl">
          Stöbere durch die Konzepte und ihre Zusammenhänge.
        </p>
      </section>
      <input
        value={q}
        onChange={(e) => setQ(e.target.value)}
        placeholder="Konzept suchen …"
        className="w-full max-w-md bg-surface-container-lowest border border-outline-variant rounded-lg px-md py-sm font-body-md text-body-md focus:outline-none focus:ring-2 focus:ring-tertiary-fixed-dim"
      />
      <section className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-md">
        {skills.map((s) => {
          const prereqs = (cur?.edges ?? []).filter((e) => e.to_key === s.key && e.kind === "prerequisite");
          return (
            <div key={s.skill_id} className="bg-surface-container-lowest rounded-xl p-md shadow-sm border border-outline-variant/10 flex flex-col gap-sm hover:-translate-y-1 transition-transform">
              <div className="flex items-center gap-sm text-secondary">
                <Icon name="functions" filled className="text-[18px]" />
                <span className="font-label-sm text-label-sm uppercase tracking-wider">{s.subject_key}</span>
              </div>
              <h4 className="font-title-md text-title-md text-primary">{s.name}</h4>
              <p className="font-caption text-caption text-on-surface-variant">Stufe {s.grade_level}</p>
              {prereqs.length > 0 && (
                <p className="font-caption text-caption text-on-surface-variant">
                  Voraussetzung: {prereqs.map((p) => p.from_key).join(", ")}
                </p>
              )}
              <Link to="/lernen" className="mt-auto inline-flex items-center gap-xs font-label-sm text-label-sm text-secondary hover:underline">
                Übung starten <Icon name="chevron_right" className="text-sm" />
              </Link>
            </div>
          );
        })}
        {cur && skills.length === 0 && (
          <p className="font-body-md text-on-surface-variant">Keine Treffer.</p>
        )}
      </section>
    </>
  );
}
