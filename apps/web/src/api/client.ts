// Typed API client. Mirrors the backend schemas. The student mastery type deliberately
// has NO uncertainty (P5); the teacher type does. Answer keys are never sent to the client.

const BASE: string = import.meta.env.VITE_API_BASE ?? "";

export type Intent = "answer" | "explain" | "hint" | "why" | "next";

export interface Grade {
  correct: boolean;
  feedback: string;
  confidence: number;
}
export interface TurnResponse {
  grade?: Grade | null;
  mastery?: number | null;
  explanation?: string | null;
  route_reason?: string | null;
}
export interface TurnInput {
  subject_key: string;
  skill_key: string;
  intent: Intent;
  answer?: string;
  item_ref?: string;
}
export interface StudentSkillMastery {
  skill_id: string;
  name: string;
  mastery: number;
  attempts_count: number;
}
export interface TeacherSkillMastery extends StudentSkillMastery {
  uncertainty: number;
}
export interface CohortStat {
  n: number;
  avg_mastery: number;
}
export interface Item {
  item_ref: string;
  prompt: string;
  skill_key: string;
  subject_key: string;
}
export interface StudentOverview {
  subjects: { key: string; name: string; mastery: number }[];
  current: {
    subject_key: string;
    subject_name: string;
    skill_key: string;
    skill_name: string;
    mastery: number;
    item_ref: string | null;
    prompt: string | null;
  } | null;
  recommendations: { skill_key: string; name: string; subject_name: string }[];
  note: { body: string } | null;
}
export interface StudentNote {
  body: string;
  skill_name: string | null;
  created_at: string;
}
export interface TeacherClass {
  class_id: string;
  name: string;
  student_count: number;
}
export interface TeacherOverview {
  class_name: string | null;
  kpis: {
    active: number;
    total: number;
    avg_mastery: number | null;
    open_reviews: number;
    alerts: number;
  };
  attention: { student_id: string; name: string; initials: string; topic: string; mastery: number }[];
  roster: { student_id: string; name: string; initials: string; avg_mastery: number; skills: number }[];
  activity: { kind: string; text: string; when: string }[];
}
export interface AttemptRow {
  item_ref: string;
  skill_name: string;
  is_correct: boolean;
  created_at: string;
}
export interface Curriculum {
  subjects: { key: string; name: string }[];
  skills: { skill_id: string; key: string; name: string; subject_key: string; grade_level: number }[];
  edges: { from_key: string; to_key: string; kind: string }[];
  items: Item[];
}
export interface SeedInfo {
  class_id: string;
  teacher_id: string;
  student_id: string;
  student_name: string;
}

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly body: string,
  ) {
    super(`HTTP ${status}`);
  }
}

async function request<T>(path: string, init: RequestInit, token?: string): Promise<T> {
  const headers: Record<string, string> = { "Content-Type": "application/json", ...(init.headers as Record<string, string>) };
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }
  const response = await fetch(`${BASE}${path}`, { ...init, headers });
  if (!response.ok) {
    throw new ApiError(response.status, await response.text().catch(() => ""));
  }
  return (await response.json()) as T;
}

export const api = {
  seedInfo: () => request<SeedInfo>("/dev/seed-info", { method: "GET" }),

  // ── student ──
  turn: (body: TurnInput, token: string) =>
    request<TurnResponse>("/student/turn", { method: "POST", body: JSON.stringify(body) }, token),
  overview: (token: string) => request<StudentOverview>("/student/overview", { method: "GET" }, token),
  myMastery: (token: string) =>
    request<StudentSkillMastery[]>("/student/mastery", { method: "GET" }, token),
  myNotes: (token: string) => request<StudentNote[]>("/student/notes", { method: "GET" }, token),

  // ── teacher ──
  classes: (token: string) => request<TeacherClass[]>("/teacher/classes", { method: "GET" }, token),
  teacherOverview: (classId: string | null, token: string) =>
    request<TeacherOverview>(
      `/teacher/overview${classId ? `?class_id=${classId}` : ""}`,
      { method: "GET" },
      token,
    ),
  studentMastery: (studentId: string, token: string) =>
    request<TeacherSkillMastery[]>(`/teacher/student/${studentId}/mastery`, { method: "GET" }, token),
  studentAttempts: (studentId: string, token: string) =>
    request<AttemptRow[]>(`/teacher/student/${studentId}/attempts`, { method: "GET" }, token),
  distribution: (classId: string, skillId: string, token: string) =>
    request<CohortStat>(`/teacher/class/${classId}/skill/${skillId}/distribution`, { method: "GET" }, token),
  addNote: (
    studentId: string,
    body: { body: string; skill_id?: string; override_mastery?: number },
    token: string,
  ) =>
    request<{ status: string }>(
      `/teacher/student/${studentId}/note`,
      { method: "POST", body: JSON.stringify(body) },
      token,
    ),

  // ── content (shared, no auth) ──
  items: (skillKey?: string) =>
    request<Item[]>(`/content/items${skillKey ? `?skill_key=${skillKey}` : ""}`, { method: "GET" }),
  curriculum: () => request<Curriculum>("/curriculum", { method: "GET" }),
};
