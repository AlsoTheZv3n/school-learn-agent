import { useEffect, useState } from "react";

import { api } from "../api/client";
import type { StudentNote } from "../api/client";
import { Icon } from "../components/Icon";
import { useSession } from "../lib/session";

export default function NotesPage() {
  const { studentToken } = useSession();
  const [notes, setNotes] = useState<StudentNote[]>([]);

  useEffect(() => {
    if (studentToken) api.myNotes(studentToken).then(setNotes).catch(() => setNotes([]));
  }, [studentToken]);

  return (
    <>
      <section>
        <h2 className="font-display-lg text-display-lg text-primary tracking-tight">Notizen</h2>
        <p className="font-body-lg text-body-lg text-on-surface-variant mt-sm max-w-2xl">
          Nachrichten von deiner Lehrperson. Ein Mensch begleitet deinen Lernweg.
        </p>
      </section>
      <section className="flex flex-col gap-md">
        {notes.map((n, i) => (
          <div key={i} className="bg-surface-container-lowest rounded-xl p-md shadow-sm border border-outline-variant/10 flex items-start gap-md">
            <div className="w-10 h-10 rounded-full bg-tertiary-fixed flex items-center justify-center text-on-tertiary-fixed shrink-0">
              <Icon name="campaign" filled />
            </div>
            <div>
              <p className="font-body-md text-body-md text-on-surface">{n.body}</p>
              <p className="font-caption text-caption text-on-surface-variant mt-xs">
                {n.skill_name ? `Zu: ${n.skill_name}` : "Allgemeine Notiz"}
              </p>
            </div>
          </div>
        ))}
        {notes.length === 0 && (
          <p className="font-body-md text-on-surface-variant">Keine Notizen — alles im grünen Bereich.</p>
        )}
      </section>
    </>
  );
}
