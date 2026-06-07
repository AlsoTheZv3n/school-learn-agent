// Typed API client. Mirrors the backend Pydantic schemas (apps/api/.../api/schemas.py).
// Note the deliberate asymmetry: the student mastery type has NO uncertainty (P5).

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

export interface StudentSkillMastery {
  skill_id: string;
  name: string;
  mastery: number;
  attempts_count: number;
}

export interface TeacherSkillMastery extends StudentSkillMastery {
  uncertainty: number; // open learner model — teacher side only
}

export interface CohortStat {
  n: number;
  avg_mastery: number;
}

export interface TurnInput {
  subject_key: string;
  skill_key: string;
  intent: Intent;
  answer?: string;
  item_ref?: string;
}

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly body: string,
  ) {
    super(`HTTP ${status}`);
  }
}

async function request<T>(path: string, init: RequestInit, token: string): Promise<T> {
  const response = await fetch(`${BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
      ...(init.headers ?? {}),
    },
  });
  if (!response.ok) {
    throw new ApiError(response.status, await response.text().catch(() => ""));
  }
  return (await response.json()) as T;
}

export const api = {
  turn: (body: TurnInput, token: string) =>
    request<TurnResponse>("/student/turn", { method: "POST", body: JSON.stringify(body) }, token),
  myMastery: (token: string) =>
    request<StudentSkillMastery[]>("/student/mastery", { method: "GET" }, token),
  studentMastery: (studentId: string, token: string) =>
    request<TeacherSkillMastery[]>(`/teacher/student/${studentId}/mastery`, { method: "GET" }, token),
  distribution: (classId: string, skillId: string, token: string) =>
    request<CohortStat>(
      `/teacher/class/${classId}/skill/${skillId}/distribution`,
      { method: "GET" },
      token,
    ),
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
};
