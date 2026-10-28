// Shapes of the backend API (backend/app/api/schemas.py). Written by hand for now.

export type Direction = "benefit" | "cost";
export type Operator = "<=" | ">=";

export interface CriterionPayload {
  name: string;
  direction: Direction;
  weight: number;
  unit: string;
}

export interface ConstraintPayload {
  criterion: string;
  operator: Operator;
  threshold: number;
}

export interface DecisionPayload {
  title: string;
  description: string;
  options: string[];
  criteria: CriterionPayload[];
  values: Record<string, Record<string, number>>;
  constraints: ConstraintPayload[];
}

export interface OptionResult {
  name: string;
  eligible: boolean;
  score: number | null;
  rank: number | null;
  tied: boolean;
  normalized: Record<string, number>;
  contributions: Record<string, number>;
  violations: string[];
}

export interface AnalysisResponse {
  normalized_weights: Record<string, number>;
  options: OptionResult[];
  has_tie_for_first: boolean;
  explanation: string[];
  method: string;
}

export interface AIChatMessage {
  role: "user" | "assistant" | "system";
  content: string;
}

export interface AIDecisionDraft {
  title: string;
  description: string;
  options: string[];
  criteria: Array<{ name: string; direction: Direction; weight: number | null; unit: string }>;
  values: Record<string, Record<string, number | null>>;
  constraints: ConstraintPayload[];
  unknowns: string[];
  notes: string;
}

export interface AIChatResponse {
  available: boolean;
  message: string;
  draft: AIDecisionDraft | null;
  warnings: string[];
  follow_up_questions: string[];
  unknown_fields: string[];
}

export interface AIStatus {
  available: boolean;
  provider: string;
  requires_configuration: boolean;
  message: string;
}

export interface Template {
  id: string;
  name: string;
  description: string;
  illustrative: boolean;
  criteria: CriterionPayload[];
}

export interface JournalEntry {
  id: string;
  title: string;
  description: string;
  decision: DecisionPayload;
  analysis: AnalysisResponse | null;
  notes: string;
  created_at: string;
  updated_at: string;
}
