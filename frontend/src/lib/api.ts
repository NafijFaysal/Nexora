import type { AnalysisResponse, DecisionPayload, JournalEntry, Template } from "./types";

export class ApiError extends Error {
  problems: string[];

  constructor(problems: string[]) {
    super(problems.join(" "));
    this.problems = problems;
  }
}

const BACKEND_UNREACHABLE =
  "Could not reach the backend. Start it with scripts\\run-backend.cmd and try again.";

// The backend returns {detail: {problems: [...]}} for model problems, and a list of
// {loc, msg} objects for schema problems. Anything else gets a generic message.
async function readProblems(response: Response): Promise<string[]> {
  try {
    const body: unknown = await response.json();
    const detail = (body as { detail?: unknown }).detail;
    if (typeof detail === "string") return [detail];
    if (Array.isArray(detail)) {
      return detail.map((item: { loc?: unknown[]; msg?: string }) => {
        const where = (item.loc ?? []).slice(1).join(" > ");
        return where ? `${where}: ${item.msg ?? "invalid"}` : (item.msg ?? "Invalid input.");
      });
    }
    const problems = (detail as { problems?: unknown } | undefined)?.problems;
    if (Array.isArray(problems)) return problems.map(String);
  } catch {
    // fall through to the generic message
  }
  return [`The backend returned an error (status ${response.status}).`];
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(path, init);
  } catch {
    throw new ApiError([BACKEND_UNREACHABLE]);
  }
  if (!response.ok) throw new ApiError(await readProblems(response));
  return (await response.json()) as T;
}

export function analyzeDecision(payload: DecisionPayload): Promise<AnalysisResponse> {
  return request<AnalysisResponse>("/api/analyze", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export function listTemplates(): Promise<Template[]> {
  return request<Template[]>("/api/templates");
}

export async function listJournalEntries(): Promise<JournalEntry[]> {
  return request<JournalEntry[]>("/api/journal/decisions");
}

export async function saveJournalEntry(payload: Record<string, unknown>): Promise<JournalEntry> {
  return request<JournalEntry>("/api/journal/decisions", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export async function updateJournalEntry(
  id: string,
  payload: Record<string, unknown>,
): Promise<JournalEntry> {
  return request<JournalEntry>(`/api/journal/decisions/${id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export async function deleteJournalEntry(id: string): Promise<void> {
  await request<Record<string, unknown>>(`/api/journal/decisions/${id}`, { method: "DELETE" });
}
