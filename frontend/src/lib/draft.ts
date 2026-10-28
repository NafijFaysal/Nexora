// The editable form state ("draft") and the pure functions that change it.
// No calculation happens here: the frontend only collects input. Scores come from the backend.

import type {
  AIDecisionDraft,
  ConstraintPayload,
  CriterionPayload,
  DecisionPayload,
  Direction,
  Operator,
  Template,
} from "./types";

export const LIMITS = {
  options: 20,
  criteria: 15,
  constraints: 50,
  name: 100,
  note: 2000,
  weight: 1000,
  value: 1e12,
} as const;

// Ids only identify rows while editing, so names can change freely. They are never shown.
let counter = 0;
const newId = () => `row${++counter}`;

export interface OptionDraft {
  id: string;
  name: string;
}
export interface CriterionDraft {
  id: string;
  name: string;
  direction: Direction;
  weight: string;
  unit: string;
}
export interface ConstraintDraft {
  id: string;
  criterionId: string;
  operator: Operator;
  threshold: string;
}
export interface Draft {
  title: string;
  description: string;
  options: OptionDraft[];
  criteria: CriterionDraft[];
  values: Record<string, Record<string, string>>; // values[optionId][criterionId]
  constraints: ConstraintDraft[];
}

function newCriterion(
  name = "",
  direction: Direction = "benefit",
  weight = "1",
  unit = "",
): CriterionDraft {
  return { id: newId(), name, direction, weight, unit };
}

export function emptyDraft(): Draft {
  return {
    title: "",
    description: "",
    options: [
      { id: newId(), name: "Option 1" },
      { id: newId(), name: "Option 2" },
    ],
    criteria: [newCriterion("Criterion 1")],
    values: {},
    constraints: [],
  };
}

// An illustrative example, not real data. Expected ranking: B, A, C (see docs/SCORING_MODEL.md).
export function exampleDraft(): Draft {
  const options = ["Laptop A", "Laptop B", "Laptop C"].map((name) => ({ id: newId(), name }));
  const price = newCriterion("Price", "cost", "4", "BDT");
  const quality = newCriterion("Quality rating", "benefit", "6", "1-10");
  const raw = [
    [800, 7],
    [1000, 9],
    [600, 5],
  ];
  const values: Draft["values"] = {};
  options.forEach((option, index) => {
    values[option.id] = { [price.id]: String(raw[index][0]), [quality.id]: String(raw[index][1]) };
  });
  return {
    title: "Which laptop? (example)",
    description: "Illustrative numbers only. Try adding the limit: Price at most 900.",
    options,
    criteria: [price, quality],
    values,
    constraints: [],
  };
}

export function applyTemplate(draft: Draft, template: Template): Draft {
  const criteria = template.criteria.map((c) =>
    newCriterion(c.name, c.direction, String(c.weight), c.unit),
  );
  return {
    ...draft,
    title: draft.title || template.name,
    criteria,
    values: {},
    constraints: [],
  };
}

function normalizeName(name: string): string {
  return name.trim().toLowerCase();
}

function mergeOptionList(existing: Draft["options"], incoming: string[]): Draft["options"] {
  const next = [...existing];
  const names = new Set(existing.map((option) => normalizeName(option.name)));
  for (const candidate of incoming) {
    const name = candidate.trim();
    if (!name || names.has(normalizeName(name))) continue;
    next.push({ id: newId(), name });
    names.add(normalizeName(name));
  }
  return next;
}

function mergeCriterionList(existing: Draft["criteria"], incoming: AIDecisionDraft["criteria"]): Draft["criteria"] {
  const next = [...existing];
  const byName = new Map(existing.map((criterion) => [normalizeName(criterion.name), criterion]));
  for (const candidate of incoming) {
    const name = candidate.name.trim();
    if (!name) continue;
    const normalized = normalizeName(name);
    const current = byName.get(normalized);
    if (current) {
      const merged = {
        ...current,
        weight: current.weight.trim() ? current.weight : candidate.weight == null ? current.weight : String(candidate.weight),
        unit: current.unit.trim() ? current.unit : (candidate.unit ?? current.unit),
      };
      const index = next.findIndex((criterion) => criterion.id === current.id);
      if (index >= 0) next[index] = merged;
      byName.set(normalized, merged);
      continue;
    }
    next.push(
      newCriterion(
        name,
        candidate.direction,
        candidate.weight == null ? "" : String(candidate.weight),
        candidate.unit ?? "",
      ),
    );
    byName.set(normalized, next[next.length - 1]);
  }
  return next;
}

function ensureCriterionForConstraint(
  draftCriteria: Draft["criteria"],
  criteriaByName: Map<string, CriterionDraft>,
  name: string,
): CriterionDraft {
  const trimmed = name.trim();
  if (!trimmed) {
    return draftCriteria[0] ?? newCriterion();
  }
  const normalized = normalizeName(trimmed);
  const existing = criteriaByName.get(normalized);
  if (existing) return existing;
  const placeholder = newCriterion(trimmed, "benefit", "", "");
  draftCriteria.push(placeholder);
  criteriaByName.set(normalized, placeholder);
  return placeholder;
}

export function hydrateDraftFromPayload(payload: DecisionPayload): Draft {
  const optionMap = new Map<string, string>();
  const options = payload.options.map((name) => {
    const optionId = newId();
    optionMap.set(name.trim(), optionId);
    return { id: optionId, name };
  });

  const criteria = payload.criteria.map((criterion) =>
    newCriterion(criterion.name, criterion.direction, String(criterion.weight), criterion.unit),
  );
  const criteriaByName = new Map(criteria.map((criterion) => [normalizeName(criterion.name), criterion]));

  const values: Draft["values"] = {};
  for (const option of payload.options) {
    const optionId = optionMap.get(option.trim()) ?? newId();
    values[optionId] = {};
    const row = payload.values[option] ?? {};
    for (const criterion of criteria) {
      values[optionId][criterion.id] = String(row[criterion.name] ?? "");
    }
  }

  const constraints = payload.constraints.map((constraint) => {
    const criterionName = constraint.criterion.trim();
    const criterion = criteriaByName.get(normalizeName(criterionName)) ?? ensureCriterionForConstraint(criteria, criteriaByName, criterionName);
    return {
      id: newId(),
      criterionId: criterion.id,
      operator: constraint.operator,
      threshold: String(constraint.threshold),
    };
  });

  return {
    title: payload.title,
    description: payload.description,
    options,
    criteria,
    values,
    constraints,
  };
}

export function mergeAIIntoDraft(draft: Draft, aiDraft: AIDecisionDraft): Draft {
  const nextOptions = mergeOptionList(draft.options, aiDraft.options);
  const nextCriteria = mergeCriterionList(draft.criteria, aiDraft.criteria);
  const criteriaByName = new Map(nextCriteria.map((criterion) => [normalizeName(criterion.name), criterion]));

  const values: Draft["values"] = { ...draft.values };
  for (const option of aiDraft.options) {
    const trimmedName = option.trim();
    if (!trimmedName) continue;
    const existingOption = draft.options.find((candidate) => normalizeName(candidate.name) === normalizeName(trimmedName));
    const optionId = existingOption?.id ?? nextOptions.find((candidate) => normalizeName(candidate.name) === normalizeName(trimmedName))?.id ?? newId();
    const row = { ...(values[optionId] ?? {}) };
    for (const criterion of aiDraft.criteria) {
      const trimmedCriterion = criterion.name.trim();
      if (!trimmedCriterion) continue;
      const target = criteriaByName.get(normalizeName(trimmedCriterion));
      if (!target) continue;
      const rawValue = aiDraft.values[trimmedName]?.[trimmedCriterion];
      if (rawValue === null || rawValue === undefined || Number.isNaN(Number(rawValue))) continue;
      if (row[target.id] !== undefined && row[target.id] !== "") continue;
      row[target.id] = String(rawValue);
    }
    values[optionId] = row;
  }

  const nextConstraints = [...draft.constraints];
  for (const constraint of aiDraft.constraints) {
    const criterionName = constraint.criterion.trim();
    if (!criterionName) continue;
    const existingConstraint = nextConstraints.find((current) => {
      const currentCriterion = draft.criteria.find((candidate) => candidate.id === current.criterionId)?.name ?? current.criterionId;
      return normalizeName(currentCriterion) === normalizeName(criterionName) && current.operator === constraint.operator && current.threshold === String(constraint.threshold);
    });
    if (existingConstraint) continue;

    const target = criteriaByName.get(normalizeName(criterionName)) ?? ensureCriterionForConstraint(nextCriteria, criteriaByName, criterionName);
    nextConstraints.push({
      id: newId(),
      criterionId: target.id,
      operator: constraint.operator,
      threshold: String(constraint.threshold),
    });
  }

  return {
    ...draft,
    title: aiDraft.title.trim() || draft.title,
    description: aiDraft.description.trim() || draft.description,
    options: nextOptions,
    criteria: nextCriteria,
    values,
    constraints: nextConstraints,
  };
}

// ---- Turning the draft into an API request, with friendly checks -------------------------

const NUMBER_PATTERN = /^[-+]?(\d+\.?\d*|\.\d+)(e[-+]?\d+)?$/i;

export function parseNumber(text: string): number | null {
  const trimmed = text.trim();
  if (!NUMBER_PATTERN.test(trimmed)) return null;
  const value = Number(trimmed);
  return Number.isFinite(value) ? value : null;
}

export type BuildResult = { ok: true; payload: DecisionPayload } | { ok: false; errors: string[] };

function checkNames(kind: string, names: string[], errors: string[]): void {
  const seen = new Set<string>();
  names.forEach((raw) => {
    const name = raw.trim();
    if (!name) {
      errors.push(`Every ${kind} needs a name.`);
    } else if (name.length > LIMITS.name) {
      errors.push(`A ${kind} name is longer than ${LIMITS.name} characters.`);
    } else if (seen.has(name.toLowerCase())) {
      errors.push(`Two ${kind}s are called "${name}". Names must be different.`);
    }
    seen.add(name.toLowerCase());
  });
}

export function buildPayload(draft: Draft): BuildResult {
  const errors: string[] = [];
  if (draft.options.length < 2) errors.push("Add at least two options to compare.");
  if (draft.criteria.length < 1) errors.push("Add at least one criterion.");
  checkNames("option", draft.options.map((o) => o.name), errors);
  checkNames("criterion", draft.criteria.map((c) => c.name), errors);

  const criteria: CriterionPayload[] = [];
  let weightTotal = 0;
  for (const c of draft.criteria) {
    const weight = parseNumber(c.weight);
    if (weight === null || weight < 0 || weight > LIMITS.weight) {
      const label = c.name.trim() || "a criterion";
      errors.push(`The weight of "${label}" must be a number from 0 to ${LIMITS.weight}.`);
      continue;
    }
    weightTotal += weight;
    criteria.push({ name: c.name.trim(), direction: c.direction, weight, unit: c.unit.trim() });
  }
  if (criteria.length === draft.criteria.length && criteria.length > 0 && weightTotal === 0) {
    errors.push("At least one criterion needs a weight above zero.");
  }

  const values: Record<string, Record<string, number>> = {};
  for (const option of draft.options) {
    const row: Record<string, number> = {};
    for (const c of draft.criteria) {
      const value = parseNumber(draft.values[option.id]?.[c.id] ?? "");
      if (value === null || Math.abs(value) > LIMITS.value) {
        const who = option.name.trim() || "an option";
        const what = c.name.trim() || "a criterion";
        errors.push(`Enter a number for "${who}" on "${what}".`);
      } else {
        row[c.name.trim()] = value;
      }
    }
    values[option.name.trim()] = row;
  }

  const constraints: ConstraintPayload[] = [];
  for (const k of draft.constraints) {
    const target = draft.criteria.find((c) => c.id === k.criterionId);
    const threshold = parseNumber(k.threshold);
    if (!target || threshold === null || Math.abs(threshold) > LIMITS.value) {
      errors.push("Every limit needs a criterion and a number. Fill it in or remove it.");
    } else {
      constraints.push({ criterion: target.name.trim(), operator: k.operator, threshold });
    }
  }

  if (errors.length > 0) return { ok: false, errors: [...new Set(errors)] };
  return {
    ok: true,
    payload: {
      title: draft.title.trim(),
      description: draft.description.trim(),
      options: draft.options.map((o) => o.name.trim()),
      criteria,
      values,
      constraints,
    },
  };
}

export function addOption(draft: Draft): Draft {
  if (draft.options.length >= LIMITS.options) return draft;
  const name = `Option ${draft.options.length + 1}`;
  return { ...draft, options: [...draft.options, { id: newId(), name }] };
}

export function removeOption(draft: Draft, optionId: string): Draft {
  const values = { ...draft.values };
  delete values[optionId];
  return { ...draft, options: draft.options.filter((o) => o.id !== optionId), values };
}

export function renameOption(draft: Draft, optionId: string, name: string): Draft {
  return { ...draft, options: draft.options.map((o) => (o.id === optionId ? { ...o, name } : o)) };
}

export function addCriterion(draft: Draft): Draft {
  if (draft.criteria.length >= LIMITS.criteria) return draft;
  const criterion = newCriterion(`Criterion ${draft.criteria.length + 1}`);
  return { ...draft, criteria: [...draft.criteria, criterion] };
}

export function removeCriterion(draft: Draft, criterionId: string): Draft {
  const values: Draft["values"] = {};
  for (const [optionId, row] of Object.entries(draft.values)) {
    const copy = { ...row };
    delete copy[criterionId];
    values[optionId] = copy;
  }
  return {
    ...draft,
    criteria: draft.criteria.filter((c) => c.id !== criterionId),
    values,
    constraints: draft.constraints.filter((c) => c.criterionId !== criterionId),
  };
}

export function updateCriterion(
  draft: Draft,
  criterionId: string,
  changes: Partial<Omit<CriterionDraft, "id">>,
): Draft {
  return {
    ...draft,
    criteria: draft.criteria.map((c) => (c.id === criterionId ? { ...c, ...changes } : c)),
  };
}

export function setValue(
  draft: Draft,
  optionId: string,
  criterionId: string,
  value: string,
): Draft {
  return {
    ...draft,
    values: { ...draft.values, [optionId]: { ...draft.values[optionId], [criterionId]: value } },
  };
}

export function addConstraint(draft: Draft): Draft {
  if (draft.constraints.length >= LIMITS.constraints || draft.criteria.length === 0) return draft;
  const constraint: ConstraintDraft = {
    id: newId(),
    criterionId: draft.criteria[0].id,
    operator: "<=",
    threshold: "",
  };
  return { ...draft, constraints: [...draft.constraints, constraint] };
}

export function updateConstraint(
  draft: Draft,
  constraintId: string,
  changes: Partial<Omit<ConstraintDraft, "id">>,
): Draft {
  return {
    ...draft,
    constraints: draft.constraints.map((c) => (c.id === constraintId ? { ...c, ...changes } : c)),
  };
}

export function removeConstraint(draft: Draft, constraintId: string): Draft {
  return { ...draft, constraints: draft.constraints.filter((c) => c.id !== constraintId) };
}
