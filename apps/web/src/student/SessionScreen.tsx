import { useState } from "react";

import { getSession } from "../auth";
import MasteryBar from "./MasteryBar";
import TutorThread from "./TutorThread";

// One concept at a time, calm and encouraging. In a full session the current item
// comes from the agent's next-item selection; here a demo concept stands in.
const DEMO = {
  subjectKey: "math",
  skillKey: "complete-the-square",
  itemRef: "expand-x-plus-1-squared",
  prompt: "Multipliziere aus: (x + 1)²",
  label: "Quadratische Ergänzung",
};

export default function SessionScreen() {
  const { token } = getSession();
  const [mastery, setMastery] = useState(0.2);
  // Toggle for the Unterstufe variant (less text, mastery hidden from the child).
  const youngerLearner = false;

  return (
    <div className="student-screen">
      <header>
        <h1>Lernen</h1>
      </header>
      <main>
        <MasteryBar mastery={mastery} label={DEMO.label} hidden={youngerLearner} />
        <TutorThread
          token={token}
          subjectKey={DEMO.subjectKey}
          skillKey={DEMO.skillKey}
          itemRef={DEMO.itemRef}
          prompt={DEMO.prompt}
          onMastery={setMastery}
          teacherNote={null}
        />
      </main>
    </div>
  );
}
