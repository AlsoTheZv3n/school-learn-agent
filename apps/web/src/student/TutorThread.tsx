import { useState } from "react";

import { api } from "../api/client";
import type { Intent, TurnResponse } from "../api/client";

interface Props {
  token: string;
  subjectKey: string;
  skillKey: string;
  itemRef: string;
  prompt: string;
  onMastery: (mastery: number) => void;
  teacherNote?: string | null;
}

// The assessment path ("Antwort absenden") and the generative helper path
// ("Anders erklären / Hinweis / Wozu?") are clearly separated (P2).
export default function TutorThread(props: Props) {
  const [answer, setAnswer] = useState("");
  const [feedback, setFeedback] = useState<string | null>(null);
  const [explanation, setExplanation] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function send(intent: Intent, withAnswer = false): Promise<void> {
    setBusy(true);
    try {
      const res: TurnResponse = await api.turn(
        {
          subject_key: props.subjectKey,
          skill_key: props.skillKey,
          intent,
          answer: withAnswer ? answer : undefined,
          item_ref: withAnswer ? props.itemRef : undefined,
        },
        props.token,
      );
      if (res.grade) {
        setFeedback(res.grade.feedback);
      }
      if (res.explanation) {
        setExplanation(res.explanation);
      }
      if (typeof res.mastery === "number") {
        props.onMastery(res.mastery);
      }
    } catch {
      setFeedback("Etwas ist schiefgelaufen. Versuch es gleich nochmal.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="thread">
      {props.teacherNote && (
        <div className="note">Notiz von deiner Lehrperson: {props.teacherNote}</div>
      )}
      {explanation && <p className="explanation">{explanation}</p>}
      <p className="prompt">{props.prompt}</p>
      <textarea
        className="answer"
        value={answer}
        onChange={(e) => setAnswer(e.target.value)}
        placeholder="Deine Antwort …"
        rows={2}
      />
      <div className="actions">
        <button disabled={busy} onClick={() => void send("answer", true)}>
          Antwort absenden
        </button>
        <button disabled={busy} className="ghost" onClick={() => void send("explain")}>
          Anders erklären
        </button>
        <button disabled={busy} className="ghost" onClick={() => void send("hint")}>
          Hinweis
        </button>
        <button disabled={busy} className="ghost" onClick={() => void send("why")}>
          Wozu?
        </button>
      </div>
      {feedback && <p className="feedback">{feedback}</p>}
    </div>
  );
}
