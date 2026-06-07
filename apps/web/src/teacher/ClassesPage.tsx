import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { api } from "../api/client";
import type { TeacherClass, TeacherOverview } from "../api/client";
import { Icon } from "../components/Icon";
import { useSession } from "../lib/session";

export default function ClassesPage() {
  const { teacherToken } = useSession();
  const [classes, setClasses] = useState<TeacherClass[]>([]);
  const [ov, setOv] = useState<TeacherOverview | null>(null);

  useEffect(() => {
    if (!teacherToken) return;
    api.classes(teacherToken).then((cs) => {
      setClasses(cs);
      const cid = cs[0]?.class_id ?? null;
      api.teacherOverview(cid, teacherToken).then(setOv).catch(() => setOv(null));
    });
  }, [teacherToken]);

  return (
    <>
      <div>
        <h2 className="font-title-md text-title-md text-on-surface mb-xs">Klassen</h2>
        <p className="font-body-md text-body-md text-on-surface-variant">
          Nur deine eigenen Klassen sind sichtbar (durch RLS erzwungen).
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-md">
        {classes.map((c) => (
          <div key={c.class_id} className="bg-surface-container-lowest rounded-xl p-md shadow-ambient border border-outline-variant/10">
            <div className="flex items-center gap-sm text-secondary mb-sm">
              <Icon name="group" filled className="text-[18px]" />
              <span className="font-label-sm text-label-sm uppercase tracking-wider">Klasse</span>
            </div>
            <h3 className="font-title-md text-title-md text-primary">{c.name}</h3>
            <p className="font-body-md text-body-md text-on-surface-variant">{c.student_count} Schüler:innen</p>
          </div>
        ))}
        {classes.length === 0 && <p className="font-body-md text-on-surface-variant">Lade Klassen …</p>}
      </div>

      <div className="bg-surface-container-lowest rounded-xl shadow-ambient border border-outline-variant/10 overflow-hidden">
        <div className="p-md border-b border-outline-variant/20 bg-surface-bright">
          <h3 className="font-title-md text-title-md text-on-surface">
            Schüler:innen{ov?.class_name ? ` — ${ov.class_name}` : ""}
          </h3>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-surface-container-low text-on-surface-variant font-label-sm text-label-sm border-b border-outline-variant/20">
                <th className="p-md font-medium">Name</th>
                <th className="p-md font-medium">Ø Mastery</th>
                <th className="p-md font-medium">Konzepte</th>
                <th className="p-md font-medium text-right">Aktion</th>
              </tr>
            </thead>
            <tbody className="font-body-md text-body-md divide-y divide-outline-variant/10">
              {(ov?.roster ?? []).map((r) => {
                const p = Math.round(r.avg_mastery * 100);
                return (
                  <tr key={r.student_id} className="hover:bg-surface-container-low transition-colors">
                    <td className="p-md">
                      <div className="flex items-center gap-sm">
                        <div className="w-8 h-8 rounded-full bg-secondary-container text-on-secondary-container flex items-center justify-center font-bold text-sm">
                          {r.initials}
                        </div>
                        {r.name}
                      </div>
                    </td>
                    <td className="p-md">
                      <div className="flex items-center gap-sm">
                        <div className="w-24 bg-surface-container-high rounded-full h-1.5">
                          <div className="bg-secondary h-1.5 rounded-full" style={{ width: `${p}%` }} />
                        </div>
                        <span className="font-label-sm text-label-sm text-on-surface-variant">{p}%</span>
                      </div>
                    </td>
                    <td className="p-md text-on-surface-variant">{r.skills}</td>
                    <td className="p-md text-right">
                      <Link to={`/teacher/student/${r.student_id}`} className="text-secondary hover:underline font-label-sm text-label-sm">
                        Lernstand
                      </Link>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </>
  );
}
