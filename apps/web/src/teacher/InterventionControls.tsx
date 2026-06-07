import { useState } from "react";

import { api, ApiError } from "../api/client";

interface Skill {
  id: string;
  name: string;
}

interface Props {
  token: string;
  studentId: string;
  classId: string;
  skills: Skill[];
}

// Human-in-the-loop is safety architecture, not reporting (P6): leave a note and
// optionally override the estimate. The cohort view makes the min-cohort threshold
// visible — a 403 becomes "too few learners", never raw numbers.
export default function InterventionControls({ token, studentId, classId, skills }: Props) {
  const [body, setBody] = useState("");
  const [skillId, setSkillId] = useState("");
  const [override, setOverride] = useState("");
  const [status, setStatus] = useState<string | null>(null);
  const [dist, setDist] = useState<string | null>(null);

  async function saveNote(): Promise<void> {
    try {
      await api.addNote(
        studentId,
        {
          body,
          skill_id: skillId || undefined,
          override_mastery: override ? Number(override) : undefined,
        },
        token,
      );
      setStatus("Notiz gespeichert.");
      setBody("");
    } catch {
      setStatus("Speichern fehlgeschlagen.");
    }
  }

  async function loadDistribution(): Promise<void> {
    if (!skillId) {
      setDist("Bitte zuerst einen Skill wählen.");
      return;
    }
    try {
      const d = await api.distribution(classId, skillId, token);
      setDist(`Klassendurchschnitt: ${Math.round(d.avg_mastery * 100)}% (n = ${d.n})`);
    } catch (e) {
      if (e instanceof ApiError && e.status === 403) {
        setDist("Zu wenige Lernende für eine anonyme Auswertung.");
      } else {
        setDist("Konnte die Verteilung nicht laden.");
      }
    }
  }

  return (
    <div className="intervention">
      <h4>Intervention</h4>
      <select value={skillId} onChange={(e) => setSkillId(e.target.value)}>
        <option value="">— Skill (optional) —</option>
        {skills.map((s) => (
          <option key={s.id} value={s.id}>
            {s.name}
          </option>
        ))}
      </select>
      <textarea
        value={body}
        onChange={(e) => setBody(e.target.value)}
        placeholder="Notiz an die:den Schüler:in …"
        rows={2}
      />
      <input
        value={override}
        onChange={(e) => setOverride(e.target.value)}
        placeholder="Mastery überschreiben (0–1, optional)"
      />
      <div className="actions">
        <button disabled={!body} onClick={() => void saveNote()}>
          Notiz speichern
        </button>
        <button className="ghost" onClick={() => void loadDistribution()}>
          Klassenverteilung
        </button>
      </div>
      {status && <p className="status">{status}</p>}
      {dist && <p className="dist">{dist}</p>}
    </div>
  );
}
