import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { api } from "../api/client";
import type { TeacherOverview } from "../api/client";
import { Icon } from "../components/Icon";
import { useSession } from "../lib/session";

function Kpi({
  label,
  value,
  sub,
  tone = "primary",
  bar,
}: {
  label: string;
  value: string;
  sub?: string;
  tone?: "primary" | "secondary" | "error" | "tertiary";
  bar?: number | null;
}) {
  const color = {
    primary: "text-primary",
    secondary: "text-secondary",
    error: "text-error",
    tertiary: "text-tertiary-container",
  }[tone];
  return (
    <div className="bg-surface-container-lowest rounded-xl p-md shadow-ambient border border-outline-variant/10">
      <p className="font-caption text-caption text-on-surface-variant mb-sm">{label}</p>
      <p className={`font-display-lg text-display-lg ${color}`}>
        {value}
        {sub && <span className="font-title-md text-title-md text-outline ml-xs">{sub}</span>}
      </p>
      {bar != null && (
        <div className="w-full bg-surface-container mt-sm rounded-full h-1.5">
          <div className="bg-secondary h-1.5 rounded-full" style={{ width: `${Math.round(bar * 100)}%` }} />
        </div>
      )}
    </div>
  );
}

export default function DashboardPage() {
  const { teacherToken } = useSession();
  const [ov, setOv] = useState<TeacherOverview | null>(null);

  useEffect(() => {
    if (!teacherToken) return;
    api.classes(teacherToken).then((cs) => {
      const cid = cs[0]?.class_id ?? null;
      api.teacherOverview(cid, teacherToken).then(setOv).catch(() => setOv(null));
    });
  }, [teacherToken]);

  const k = ov?.kpis;

  return (
    <>
      <div>
        <h2 className="font-title-md text-title-md text-on-surface mb-xs">Guten Tag 👋</h2>
        <p className="font-body-md text-body-md text-on-surface-variant">
          Übersicht für {ov?.class_name ?? "deine Klasse"}
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-md">
        <Kpi label="Aktive Schüler:innen" value={`${k?.active ?? "–"}`} sub={`/${k?.total ?? "–"}`} />
        <Kpi
          label="Ø Mastery (Klasse)"
          value={k?.avg_mastery != null ? `${Math.round(k.avg_mastery * 100)}` : "—"}
          sub={k?.avg_mastery != null ? "%" : undefined}
          tone="secondary"
          bar={k?.avg_mastery ?? null}
        />
        <Kpi label="Offene Reviews" value={`${k?.open_reviews ?? 0}`} tone="error" />
        <Kpi label="Auffälligkeiten" value={`${k?.alerts ?? 0}`} tone="tertiary" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-xl">
        <div className="lg:col-span-2 space-y-xl">
          <div className="bg-surface-container-lowest rounded-xl shadow-ambient border border-outline-variant/10 overflow-hidden">
            <div className="p-md border-b border-outline-variant/20 flex items-center gap-sm bg-surface-bright">
              <Icon name="warning" className="text-error" />
              <h3 className="font-title-md text-title-md text-on-surface">Braucht Aufmerksamkeit</h3>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="bg-surface-container-low text-on-surface-variant font-label-sm text-label-sm border-b border-outline-variant/20">
                    <th className="p-md font-medium">Schüler:in</th>
                    <th className="p-md font-medium">Thema</th>
                    <th className="p-md font-medium">Signal</th>
                    <th className="p-md font-medium text-right">Aktion</th>
                  </tr>
                </thead>
                <tbody className="font-body-md text-body-md divide-y divide-outline-variant/10">
                  {(ov?.attention ?? []).map((a) => (
                    <tr key={a.student_id} className="hover:bg-surface-container-low transition-colors">
                      <td className="p-md">
                        <div className="flex items-center gap-sm">
                          <div className="w-8 h-8 rounded-full bg-primary-container text-on-primary-container flex items-center justify-center font-bold text-sm">
                            {a.initials}
                          </div>
                          {a.name}
                        </div>
                      </td>
                      <td className="p-md text-on-surface-variant">{a.topic}</td>
                      <td className="p-md">
                        <span className="inline-flex items-center gap-xs px-2 py-1 rounded bg-error-container/50 text-on-error-container font-label-sm text-label-sm">
                          <Icon name="trending_down" className="text-sm" /> Niedrige Mastery
                        </span>
                      </td>
                      <td className="p-md text-right">
                        <Link to={`/teacher/student/${a.student_id}`} className="text-secondary hover:underline font-label-sm text-label-sm">
                          Details
                        </Link>
                      </td>
                    </tr>
                  ))}
                  {ov && ov.attention.length === 0 && (
                    <tr>
                      <td colSpan={4} className="p-md text-on-surface-variant">Keine Auffälligkeiten 🎉</td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        <div className="space-y-xl">
          <Link to="/teacher/review" className="block bg-primary-container rounded-xl p-lg shadow-md relative overflow-hidden min-h-[180px]">
            <div className="absolute -right-8 -top-8 opacity-10">
              <Icon name="fact_check" filled className="text-9xl" />
            </div>
            <h3 className="font-title-md text-title-md text-on-primary-container mb-xs">Review-Queue</h3>
            <p className="font-body-md text-body-md text-primary-fixed-dim">KI-Bewertungen zur Freigabe</p>
            <div className="mt-xl flex items-end justify-between">
              <div className="text-on-primary-container font-display-lg text-display-lg leading-none">{k?.open_reviews ?? 0}</div>
              <span className="bg-surface-container-lowest text-primary px-lg py-sm rounded-lg font-label-sm text-label-sm font-bold">Jetzt prüfen</span>
            </div>
          </Link>

          <div className="bg-surface-container-lowest rounded-xl p-md shadow-ambient border border-outline-variant/10">
            <h3 className="font-title-md text-title-md text-on-surface mb-md">Letzte Aktivität</h3>
            {(ov?.activity ?? []).length === 0 ? (
              <p className="font-body-md text-body-md text-on-surface-variant">Keine aktuelle Aktivität.</p>
            ) : (
              <div className="space-y-md">
                {ov!.activity.map((e, i) => (
                  <div key={i} className="flex gap-sm">
                    <Icon name="check_circle" className="text-secondary text-lg mt-1" />
                    <div>
                      <p className="font-label-sm text-label-sm text-on-surface">{e.text}</p>
                      <p className="font-caption text-caption text-outline">{e.when}</p>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </>
  );
}
