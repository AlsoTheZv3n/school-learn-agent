import { createContext, useContext, useEffect, useState } from "react";
import type { ReactNode } from "react";

import { api } from "../api/client";
import type { SeedInfo } from "../api/client";

// DEV identity: logs in as a real seeded student/teacher (AUTH_DEV_MODE on the API).
// Replaced by a real IdP login (FND-5) before production.
interface SessionValue {
  info: SeedInfo | null;
  loading: boolean;
  error: string | null;
  studentToken: string;
  teacherToken: string;
}

const Ctx = createContext<SessionValue | null>(null);

export function SessionProvider({ children }: { children: ReactNode }) {
  const [info, setInfo] = useState<SeedInfo | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .seedInfo()
      .then((d) => {
        if (!d?.student_id) {
          setError("Keine Mock-Daten gefunden. Bitte den Seeder ausführen (scripts/seed.py).");
        } else {
          setInfo(d);
        }
      })
      .catch(() => setError("Backend nicht erreichbar oder AUTH_DEV_MODE ist aus."));
  }, []);

  const value: SessionValue = {
    info,
    loading: !info && !error,
    error,
    studentToken: info ? `dev:student:${info.student_id}:${info.student_id}` : "",
    teacherToken: info ? `dev:teacher:${info.teacher_id}` : "",
  };
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useSession(): SessionValue {
  const v = useContext(Ctx);
  if (!v) {
    throw new Error("useSession must be used within a SessionProvider");
  }
  return v;
}
