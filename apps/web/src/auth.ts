// Dev auth stub. Real JWT/IdP integration is a FND-5 follow-up; the role drives
// which view renders (the same separation RLS keys off on the backend).

export type Role = "student" | "teacher";

export interface Session {
  token: string;
  role: Role;
}

export function getSession(): Session {
  const role: Role = window.location.pathname.startsWith("/teacher") ? "teacher" : "student";
  // Placeholder token; replaced by a real bearer token once auth is wired (FND-5).
  return { token: "dev-token", role };
}
