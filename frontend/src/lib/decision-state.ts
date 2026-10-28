export type DraftShape = {
  title: string;
  description: string;
  options: Array<{ name: string }>;

  criteria: Array<{ name: string; direction: string; weight: string; unit: string }>;
  values: Record<string, Record<string, string>>;
  constraints: Array<{ criterionId: string; operator: "<=" | ">="; threshold: string }>;

  // Add an optional ID field
  id?: string;
};

export type PayloadShape = {
  title: string;
  description: string;
  options: string[];
  criteria: Array<{ name: string; direction: string; weight: number; unit: string }>;

  // Change values to be number instead of string
  values: Record<string, Record<string, number>>;
  constraints: Array<{ criterion: string; operator: "<=" | ">="; threshold: number }>;
};

export function createDraftSignature(draft: DraftShape): string {
  return JSON.stringify({
    title: draft.title,
    description: draft.description,
    options: draft.options.map((option) => option.name),
    criteria: draft.criteria.map((criterion) => ({
      name: criterion.name,
      direction: criterion.direction,
      weight: criterion.weight,
      unit: criterion.unit,
    })),
    values: draft.values,
    constraints: draft.constraints.map((constraint) => ({
      criterionId: constraint.criterionId,
      operator: constraint.operator,
      threshold: constraint.threshold,
    })),
  });
}

export function createDraftSignatureFromPayload(payload: PayloadShape): string {
  return createDraftSignature({
    title: payload.title,
    description: payload.description,
    options: payload.options.map((name) => ({ name })),
    criteria: payload.criteria.map((criterion) => ({
      name: criterion.name,
      direction: criterion.direction,
      weight: String(criterion.weight),
      unit: criterion.unit,
    })),
    values: Object.fromEntries(
      Object.entries(payload.values).map(([option, row]) => [
        option,
        Object.fromEntries(Object.entries(row).map(([criterion, value]) => [criterion, String(value)])),
      ]),
    ),
    constraints: payload.constraints.map((constraint) => ({
      criterionId: constraint.criterion,
      operator: constraint.operator,
      threshold: String(constraint.threshold),
    })),
  });
}

export function hasStaleResult(resultDraftSignature: string | null | undefined, draftSignature: string): boolean {
  return Boolean(resultDraftSignature) && resultDraftSignature !== draftSignature;
}

export function getAIErrorMessage(message: string): string {
  const retryable = /429|rate-limited|temporarily overloaded|temporarily unavailable|try again later|overloaded|503/i.test(message);
  return retryable
    ? `${message} Manual Setup stays available, and you can try again when the service is ready.`
    : message;
}
