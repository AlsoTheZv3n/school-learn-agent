import { useEffect, useState } from "react";

import { api } from "../api/client";
import type { TeacherSkillMastery } from "../api/client";
import InterventionControls from "./InterventionControls";

interface Props {
  token: string;
  studentId: string;
  classId: string;
}

// Open Learner Model (P5): shows mastery AND uncertainty per skill, so the teacher
// can see how reliable each estimate is — not a black box to trust blindly.
export default function LearnerModelPanel({ token, studentId, classId }: Props) {
  const [rows, setRows] = useState<TeacherSkillMastery[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    api
      .studentMastery(studentId, token)
      .then((data) => {
        if (active) {
          setRows(data);
        }
      })
      .catch(() => {
        if (active) {
          setError("Konnte den Lernstand nicht laden.");
        }
      });
    return () => {
      active = false;
    };
  }, [studentId, token]);

  return (
    <div className="learner-panel">
      <h3>Lernstand (Open Learner Model)</h3>
      {error && <p className="error">{error}</p>}
      {rows.length === 0 && !error && <p className="hint">Noch keine Daten.</p>}
      {rows.length > 0 && (
        <table>
          <thead>
            <tr>
              <th>Skill</th>
              <th>Mastery</th>
              <th>Unsicherheit</th>
              <th>Versuche</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.skill_id}>
                <td>{r.name}</td>
                <td>{Math.round(r.mastery * 100)}%</td>
                <td>
                  <span className="uncertainty" title="Verlässlichkeit der Schätzung">
                    ±{Math.round(r.uncertainty * 100)}%
                  </span>
                </td>
                <td>{r.attempts_count}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      <InterventionControls
        token={token}
        studentId={studentId}
        classId={classId}
        skills={rows.map((r) => ({ id: r.skill_id, name: r.name }))}
      />
    </div>
  );
}
