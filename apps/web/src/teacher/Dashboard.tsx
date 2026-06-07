import { useState } from "react";

import { getSession } from "../auth";
import LearnerModelPanel from "./LearnerModelPanel";

// Class/student list -> detail. Only the teacher's own classes appear (enforced by
// RLS on the backend; the UI needs no filtering). Demo data stands in for a future
// /teacher/classes endpoint.
const DEMO_CLASS = {
  id: "demo-class",
  name: "Klasse 9a",
  students: [
    { id: "demo-student-1", name: "Schüler:in 1" },
    { id: "demo-student-2", name: "Schüler:in 2" },
  ],
};

export default function Dashboard() {
  const { token } = getSession();
  const [selected, setSelected] = useState<string | null>(null);

  return (
    <div className="teacher-dashboard">
      <aside>
        <h2>{DEMO_CLASS.name}</h2>
        <ul>
          {DEMO_CLASS.students.map((s) => (
            <li key={s.id}>
              <button
                className={selected === s.id ? "active" : ""}
                onClick={() => setSelected(s.id)}
              >
                {s.name}
              </button>
            </li>
          ))}
        </ul>
      </aside>
      <section>
        {selected ? (
          <LearnerModelPanel token={token} studentId={selected} classId={DEMO_CLASS.id} />
        ) : (
          <p className="hint">Wähle eine:n Schüler:in, um den Lernstand zu sehen.</p>
        )}
      </section>
    </div>
  );
}
