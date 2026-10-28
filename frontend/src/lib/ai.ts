import type { AIChatMessage, AIChatResponse, AIStatus, AIDecisionDraft, DecisionPayload, Direction } from "./types";

export async function getAIStatus(): Promise<AIStatus> {
  const response = await fetch("/api/ai/status");
  if (!response.ok) {
    throw new Error("AI status could not be loaded.");
  }
  return (await response.json()) as AIStatus;
}

export async function chatWithAI(messages: AIChatMessage[]): Promise<AIChatResponse> {
  const response = await fetch("/api/ai/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ messages }),
  });
  if (!response.ok) {
    const detail = (await response.json().catch(() => ({ detail: { problems: ["AI request failed."] } }))) as {
      detail?: { problems?: string[] };
    };
    const problems = detail.detail?.problems ?? ["AI request failed."];
    throw new Error(problems.join(" "));
  }
  return (await response.json()) as AIChatResponse;
}

export function draftFromAI(aiDraft: AIDecisionDraft): DecisionPayload {
  const options = aiDraft.options.map((option) => option.trim()).filter(Boolean);
  const criteria = aiDraft.criteria
    .map((criterion) => ({
      name: criterion.name.trim(),
      direction: criterion.direction,
      weight: criterion.weight == null ? null : Number(criterion.weight),
      unit: criterion.unit ?? "",
    }))
    .filter((criterion) => criterion.name.length > 0);
  const values: Record<string, Record<string, number>> = {};
  for (const option of options) {
    const row: Record<string, number> = {};
    for (const criterion of criteria) {
      const raw = aiDraft.values[option]?.[criterion.name];
      if (raw === null || raw === undefined || Number.isNaN(Number(raw))) {
        continue;
      }
      row[criterion.name] = Number(raw);
    }
    values[option] = row;
  }
  return {
    title: aiDraft.title.trim(),
    description: aiDraft.description.trim(),
    options,
    criteria: criteria
      .filter((criterion) => criterion.weight !== null)
      .map((criterion) => ({
        name: criterion.name,
        direction: criterion.direction,
        weight: criterion.weight ?? 0,
        unit: criterion.unit,
      })),
    values,
    constraints: aiDraft.constraints.map((constraint) => ({
      criterion: constraint.criterion,
      operator: constraint.operator,
      threshold: Number(constraint.threshold),
    })),
  };
}

export function aiDraftToDraftShape(aiDraft: AIDecisionDraft): {
  title: string;
  description: string;
  options: string[];
  criteria: Array<{ name: string; direction: Direction; weight: string; unit: string }>;
  values: Record<string, Record<string, string>>;
  constraints: Array<{ criterion: string; operator: "<=" | ">="; threshold: string }>;
} {
  const options = aiDraft.options.map((option) => option.trim()).filter(Boolean);
  const criteria = aiDraft.criteria.map((criterion) => ({
    name: criterion.name.trim(),
    direction: criterion.direction,
    weight: criterion.weight == null ? "" : String(criterion.weight),
    unit: criterion.unit ?? "",
  }));
  const values: Record<string, Record<string, string>> = {};
  for (const option of options) {
    const row: Record<string, string> = {};
    for (const criterion of criteria) {
      const raw = aiDraft.values[option]?.[criterion.name];
      row[criterion.name] = raw == null ? "" : String(raw);
    }
    values[option] = row;
  }
  return {
    title: aiDraft.title,
    description: aiDraft.description,
    options,
    criteria,
    values,
    constraints: aiDraft.constraints.map((constraint) => ({
      criterion: constraint.criterion,
      operator: constraint.operator,
      threshold: String(constraint.threshold),
    })),
  };
}
