import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { api } from "../api/client";
import type { Intent, Item } from "../api/client";
import { Icon } from "../components/Icon";
import { useSession } from "../lib/session";

interface Bubble {
  role: "student" | "tutor";
  text: string;
  state?: "correct" | "incorrect" | "neutral";
}

export default function SessionPage() {
  const { studentToken } = useSession();
  const [items, setItems] = useState<Item[]>([]);
  const [idx, setIdx] = useState(0);
  const [skillName, setSkillName] = useState("Quadratische Ergänzung");
  const [mastery, setMastery] = useState(0.2);
  const [answer, setAnswer] = useState("");
  const [thread, setThread] = useState<Bubble[]>([]);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!studentToken) return;
    api.overview(studentToken).then((o) => {
      const skill = o.current?.skill_key ?? "complete-the-square";
      if (o.current) {
        setSkillName(o.current.skill_name);
        setMastery(o.current.mastery);
      }
      api.items(skill).then((its) => {
        setItems(its.length ? its : []);
      });
    });
    // Fallback: ensure there is always at least one item to practice.
    api.items("complete-the-square").then((its) => {
      setItems((cur) => (cur.length ? cur : its));
    });
  }, [studentToken]);

  const item = items[idx];
  const pct = Math.round(Math.max(0, Math.min(1, mastery)) * 100);

  async function send(intent: Intent, withAnswer = false) {
    if (!item || busy) return;
    setBusy(true);
    if (withAnswer) {
      setThread((t) => [...t, { role: "student", text: answer }]);
    }
    try {
      const res = await api.turn(
        {
          subject_key: item.subject_key,
          skill_key: item.skill_key,
          intent,
          answer: withAnswer ? answer : undefined,
          item_ref: withAnswer ? item.item_ref : undefined,
        },
        studentToken,
      );
      if (res.grade) {
        setThread((t) => [
          ...t,
          { role: "tutor", text: res.grade!.feedback, state: res.grade!.correct ? "correct" : "incorrect" },
        ]);
      }
      if (res.explanation) {
        setThread((t) => [...t, { role: "tutor", text: res.explanation!, state: "neutral" }]);
      }
      if (typeof res.mastery === "number") setMastery(res.mastery);
      if (withAnswer) setAnswer("");
    } catch {
      setThread((t) => [...t, { role: "tutor", text: "Etwas ist schiefgelaufen. Versuch es gleich nochmal.", state: "neutral" }]);
    } finally {
      setBusy(false);
    }
  }

  function nextItem() {
    if (items.length) setIdx((i) => (i + 1) % items.length);
    setThread([]);
  }

  return (
    <div className="w-full max-w-[720px] mx-auto flex flex-col gap-lg">
      {/* Header: breadcrumb + step + mastery */}
      <header className="flex flex-col gap-sm">
        <div className="flex justify-between items-center text-on-surface-variant font-label-sm text-label-sm">
          <Link to="/" className="flex items-center gap-xs hover:text-primary transition-colors">
            <Icon name="arrow_back" className="text-[18px]" /> Mathe › {skillName}
          </Link>
          <span className="text-outline">
            {items.length ? `Aufgabe ${idx + 1} von ${items.length}` : "Aufgabe"}
          </span>
        </div>
        <div className="flex flex-col gap-xs mt-sm">
          <div className="flex justify-between font-label-sm text-label-sm">
            <span className="text-secondary">{skillName}</span>
            <span className="text-secondary font-bold">{pct}%</span>
          </div>
          <div className="w-full h-2 bg-surface-variant rounded-full overflow-hidden">
            <div className="h-full bg-gradient-to-r from-secondary to-primary rounded-full transition-all duration-500" style={{ width: `${pct}%` }} />
          </div>
        </div>
      </header>

      <section className="flex flex-col gap-md">
        {/* Tutor intro card */}
        <div className="bg-primary-fixed flex items-start gap-md p-md rounded-xl shadow-ambient">
          <div className="w-10 h-10 rounded-full bg-primary flex items-center justify-center shrink-0">
            <Icon name="psychology" filled className="text-on-primary" />
          </div>
          <div className="flex flex-col gap-sm">
            <h3 className="font-title-md text-title-md text-on-primary-fixed-variant">Lass uns üben!</h3>
            <p className="font-body-md text-body-md text-on-surface">
              Schreibe deine Antwort in das Feld. Du kannst jederzeit einen Hinweis anfordern oder dir das Konzept anders erklären lassen.
            </p>
          </div>
        </div>

        {/* Question card */}
        <div className="bg-surface-container-lowest border border-outline-variant/30 p-lg rounded-xl shadow-ambient flex flex-col gap-lg">
          <h2 className="font-headline-lg-mobile text-headline-lg-mobile md:font-headline-lg md:text-headline-lg text-primary text-center py-md">
            {item ? item.prompt : "Lade Aufgabe …"}
          </h2>
          <input
            value={answer}
            onChange={(e) => setAnswer(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && void send("answer", true)}
            placeholder="Deine Antwort hier eingeben …"
            className="w-full bg-surface border border-outline-variant rounded-lg px-md py-sm font-body-lg text-body-lg text-on-surface focus:outline-none focus:ring-2 focus:ring-tertiary-fixed-dim focus:border-transparent transition-all placeholder:text-outline-variant text-center"
          />
          <button
            disabled={busy || !item || !answer}
            onClick={() => void send("answer", true)}
            className="w-full bg-primary hover:bg-surface-tint text-on-primary font-label-sm text-label-sm py-md rounded-lg transition-colors shadow-md disabled:opacity-50"
          >
            Antwort absenden
          </button>
        </div>

        {/* Helper actions */}
        <div className="flex flex-wrap justify-center gap-sm mt-sm">
          {[
            { intent: "explain" as Intent, icon: "autorenew", label: "Anders erklären" },
            { intent: "hint" as Intent, icon: "lightbulb", label: "Hinweis" },
            { intent: "why" as Intent, icon: "help_center", label: "Wozu?" },
          ].map((h) => (
            <button
              key={h.intent}
              disabled={busy}
              onClick={() => void send(h.intent)}
              className="flex items-center gap-xs px-md py-sm rounded-full border border-outline-variant text-on-surface-variant font-label-sm text-label-sm hover:bg-surface-container-low transition-colors disabled:opacity-50"
            >
              <Icon name={h.icon} className="text-[18px]" />
              {h.label}
            </button>
          ))}
        </div>

        {/* Thread */}
        {thread.length > 0 && (
          <div className="mt-lg flex flex-col gap-md">
            {thread.map((b, i) =>
              b.role === "student" ? (
                <div key={i} className="flex justify-end">
                  <div className="bg-surface-container-high text-on-surface font-body-md text-body-md p-md rounded-xl rounded-tr-none max-w-[80%]">
                    {b.text}
                  </div>
                </div>
              ) : (
                <div key={i} className="flex items-start gap-md">
                  <div className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 mt-1 ${b.state === "correct" ? "bg-secondary" : "bg-primary"}`}>
                    <Icon name={b.state === "correct" ? "check_circle" : "psychology"} filled className="text-on-primary text-[16px]" />
                  </div>
                  <div className={`font-body-md text-body-md p-md rounded-xl rounded-tl-none max-w-[80%] ${b.state === "correct" ? "bg-secondary-container text-on-secondary-container" : "bg-primary-fixed text-on-primary-fixed-variant"}`}>
                    {b.text}
                  </div>
                </div>
              ),
            )}
          </div>
        )}
      </section>

      <footer className="mt-xl flex flex-col sm:flex-row justify-between gap-md pt-lg border-t border-outline-variant/20">
        <Link to="/" className="px-lg py-sm rounded-lg text-primary hover:bg-primary-fixed/50 font-label-sm text-label-sm transition-colors text-center">
          Session beenden
        </Link>
        <button
          onClick={nextItem}
          className="px-lg py-sm rounded-lg bg-secondary text-on-secondary hover:bg-secondary/90 font-label-sm text-label-sm transition-colors shadow-sm flex items-center justify-center gap-xs"
        >
          Nächste Aufgabe <Icon name="arrow_forward" className="text-[18px]" />
        </button>
      </footer>
    </div>
  );
}
