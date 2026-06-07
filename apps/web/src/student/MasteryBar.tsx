interface Props {
  mastery: number; // 0..1
  label?: string;
  hidden?: boolean; // Unterstufe config: hide the % from young children (P5/age)
}

// Gentle view: a rounded percent + bar. Deliberately NO uncertainty (that is the
// teacher side). For younger learners the bar is hidden entirely.
export default function MasteryBar({ mastery, label, hidden }: Props) {
  if (hidden) {
    return null;
  }
  const pct = Math.round(Math.max(0, Math.min(1, mastery)) * 100);
  return (
    <div className="mastery">
      <div className="mastery-label">
        {label ?? "Fortschritt"}: {pct}%
      </div>
      <div className="mastery-track">
        <div className="mastery-fill" style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}
