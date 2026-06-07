import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { api } from "../api/client";
import type { AttemptRow, TeacherSkillMastery } from "../api/client";
import { Icon } from "../components/Icon";
import { useSession } from "../lib/session";

export default function StudentDetailPage() {
  const { id = "" } = useParams();
  const { teacherToken } = useSession();
  const [skills, setSkills] = useState<TeacherSkillMastery[]>([]);
  const [attempts, setAttempts] = useState<AttemptRow[]>([]);
  const [name, setName] = useState("Schüler:in");
  const [expanded, setExpanded] = useState<string | null>(null);
  const [note, setNote] = useState("");
  const [override, setOverride] = useState("");
  const [reason, setReason] = useState("");
  const [status, setStatus] = useState<string | null>(null);

  useEffect(() => {
    if (!teacherToken || !id) return;
    api.studentMastery(id, teacherToken).then(setSkills).catch(() => setSkills([]));
    api.studentAttempts(id, teacherToken).then(setAttempts).catch(() => setAttempts([]));
    api.classes(teacherToken).then((cs) => {
      const cid = cs[0]?.class_id ?? null;
      api.teacherOverview(cid, teacherToken).then((o) => {
        const r = o.roster.find((x) => x.student_id === id) ?? o.attention.find((x) => x.student_id === id);
        if (r) setName(r.name);
      });
    });
  }, [teacherToken, id]);

  async function save() {
    try {
      await api.addNote(
        id,
        { body: note, override_mastery: override ? Number(override) / 100 : undefined },
        teacherToken,
      );
      setStatus("Intervention gespeichert.");
      setNote("");
      setReason("");
      setOverride("");
    } catch {
      setStatus("Speichern fehlgeschlagen.");
    }
  }

  return (
    <div className="bg-surface-container-lowest -m-gutter md:-m-xl p-gutter md:p-xl min-h-full">
      <div className="mb-lg">
        <div className="flex items-center gap-sm mb-xs">
          <Link to="/teacher" className="text-on-surface-variant hover:text-primary transition-colors">
            <Icon name="arrow_back" className="text-[20px]" />
          </Link>
          <h1 className="font-headline-lg text-headline-lg text-on-surface">{name}</h1>
          <span className="bg-surface-container-high px-sm py-xs rounded-md font-label-sm text-label-sm text-on-surface-variant border border-outline-variant/30">
            Open Learner Model
          </span>
        </div>
        <p className="font-body-md text-body-md text-on-surface-variant flex items-center gap-xs">
          <span className="w-2 h-2 rounded-full bg-secondary" /> {attempts.length} Versuche erfasst
        </p>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-lg">
        {/* Left: OLM table */}
        <div className="xl:col-span-2 flex flex-col gap-md">
          <h2 className="font-title-md text-title-md text-on-surface border-b border-outline-variant/20 pb-xs">
            Mastery-Profil (Open Learner Model)
          </h2>
          <div className="bg-surface rounded-xl border border-outline-variant/10 shadow-ambient overflow-hidden">
            <div className="grid grid-cols-12 gap-sm p-sm border-b border-outline-variant/20 bg-surface-container-lowest font-label-sm text-label-sm text-on-surface-variant">
              <div className="col-span-5">Konzept</div>
              <div className="col-span-5">Mastery-Schätzung &amp; Unsicherheit</div>
              <div className="col-span-2 text-center">Versuche</div>
            </div>
            {skills.map((s) => {
              const m = Math.round(s.mastery * 100);
              const u = Math.round(s.uncertainty * 100);
              const bandLeft = Math.max(0, Math.min(100, m - u));
              const bandWidth = Math.min(100 - bandLeft, u * 2);
              const open = expanded === s.skill_id;
              const tl = attempts.filter((a) => a.skill_name === s.name);
              return (
                <div key={s.skill_id} className="border-b border-outline-variant/10">
                  <button
                    onClick={() => setExpanded(open ? null : s.skill_id)}
                    className="w-full grid grid-cols-12 gap-sm p-sm items-center cursor-pointer hover:bg-surface-container-low transition-colors text-left"
                  >
                    <div className="col-span-5 flex items-center gap-xs font-body-md text-body-md text-on-surface">
                      <Icon name="chevron_right" className={`text-[18px] text-on-surface-variant transition-transform ${open ? "rotate-90" : ""}`} />
                      {s.name}
                    </div>
                    <div className="col-span-5 flex items-center gap-sm">
                      <div className="flex-1 h-3 bg-surface-container-high rounded-full relative overflow-hidden">
                        <div className="absolute top-0 bottom-0 bg-secondary/20 rounded-full" style={{ left: `${bandLeft}%`, width: `${bandWidth}%` }} />
                        <div className="absolute top-0 bottom-0 left-0 bg-gradient-to-r from-primary-container to-secondary rounded-full" style={{ width: `${m}%` }} />
                      </div>
                      <span className="font-label-sm text-label-sm text-on-surface w-16 text-right">{m}% ±{u}%</span>
                    </div>
                    <div className="col-span-2 text-center font-body-md text-body-md text-on-surface-variant">{s.attempts_count}</div>
                  </button>
                  {open && (
                    <div className="p-md bg-surface-container-low/50 border-t border-outline-variant/10 pl-10">
                      <h3 className="font-label-sm text-label-sm text-primary mb-sm flex items-center gap-xs">
                        <Icon name="psychology" className="text-[16px]" /> Erklärung der Schätzung
                      </h3>
                      <p className="text-sm text-on-surface-variant mb-md bg-surface p-sm rounded-lg border border-outline-variant/20">
                        Die Schätzung beruht auf {s.attempts_count} Versuchen. Das Unsicherheitsband (±{u}%)
                        spiegelt, wie stark die jüngsten Antworten gestreut haben — je mehr konsistente Versuche,
                        desto schmaler das Band.
                      </p>
                      <h4 className="font-label-sm text-label-sm text-on-surface mb-xs">Letzte Versuche</h4>
                      <div className="flex flex-col gap-xs">
                        {tl.slice(0, 6).map((a, i) => (
                          <div key={i} className="flex items-center gap-sm p-xs bg-surface rounded border border-outline-variant/10 text-sm">
                            <Icon name={a.is_correct ? "check" : "close"} className={`text-[16px] ${a.is_correct ? "text-secondary" : "text-error"}`} />
                            <span className="text-on-surface-variant w-40 truncate">{a.created_at}</span>
                            <span className="text-on-surface font-mono flex-1 truncate">{a.item_ref}</span>
                          </div>
                        ))}
                        {tl.length === 0 && <p className="text-sm text-on-surface-variant">Keine Versuche zu diesem Konzept.</p>}
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
            {skills.length === 0 && <p className="p-md font-body-md text-on-surface-variant">Lade Lernstand …</p>}
          </div>
        </div>

        {/* Right: Intervention */}
        <div className="xl:col-span-1">
          <div className="bg-surface rounded-xl border border-outline-variant/10 shadow-ambient p-md sticky top-24">
            <h2 className="font-title-md text-title-md text-on-surface mb-md flex items-center gap-xs">
              <Icon name="build" className="text-[20px]" /> Intervention
            </h2>
            <div className="mb-md">
              <label className="block font-label-sm text-label-sm text-on-surface mb-xs flex items-center gap-xs">
                <Icon name="chat_bubble" className="text-[16px]" /> Notiz an die:den Schüler:in
                <span className="text-xs text-on-surface-variant font-normal">(erscheint beim Schüler)</span>
              </label>
              <textarea
                value={note}
                onChange={(e) => setNote(e.target.value)}
                className="w-full h-24 p-sm border border-outline-variant/50 rounded-lg bg-surface-bright focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary text-body-md font-body-md resize-none"
                placeholder="z. B. Toll dranbleiben! Wir schauen uns das Kürzen nächste Stunde gemeinsam an."
              />
            </div>
            <div className="border-t border-outline-variant/20 pt-md">
              <label className="block font-label-sm text-label-sm text-on-surface mb-xs flex items-center gap-xs">
                <Icon name="admin_panel_settings" className="text-[16px]" /> Mastery überschreiben
                <span className="text-xs text-on-surface-variant font-normal">(auditiert)</span>
              </label>
              <p className="font-caption text-caption text-on-surface-variant mb-sm leading-tight">
                Passe die KI-Schätzung anhand deiner Beobachtung im Unterricht an. Diese Aktion wird protokolliert.
              </p>
              <div className="flex items-center gap-sm mb-sm">
                <input
                  type="number"
                  min={0}
                  max={100}
                  value={override}
                  onChange={(e) => setOverride(e.target.value)}
                  placeholder="—"
                  className="w-20 p-xs border border-outline-variant/50 rounded-md bg-surface-bright text-center text-body-md font-body-md focus:outline-none focus:border-primary"
                />
                <span className="text-on-surface-variant">%</span>
              </div>
              <textarea
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                className="w-full h-16 p-sm border border-outline-variant/50 rounded-lg bg-surface-bright focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary text-sm resize-none mb-sm"
                placeholder="Grund für die Korrektur (empfohlen) …"
              />
              <button
                onClick={() => void save()}
                disabled={!note && !override}
                className="w-full bg-primary text-on-primary py-sm rounded-lg font-label-sm text-label-sm hover:bg-primary/90 transition-colors disabled:opacity-50"
              >
                Intervention speichern
              </button>
              {status && <p className="font-caption text-caption text-secondary mt-sm">{status}</p>}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
