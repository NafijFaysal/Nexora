"""Pydantic request and response models.

Limits mirror app/engine/validation.py. They are repeated here so bad input is rejected
before any engine code runs; the engine re-checks everything because it can be called
without the API.
"""

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from app.engine.models import Direction, Operator
from app.engine.validation import (
    MAX_ABS_VALUE,
    MAX_CRITERIA,
    MAX_NAME_LENGTH,
    MAX_OPTIONS,
    MAX_WEIGHT,
    MIN_OPTIONS,
)

Name = Annotated[str, StringConstraints(min_length=1, max_length=MAX_NAME_LENGTH)]
RawNumber = Annotated[float, Field(ge=-MAX_ABS_VALUE, le=MAX_ABS_VALUE, allow_inf_nan=False)]
MAX_NOTE_LENGTH = 2000
MAX_CONSTRAINTS = 50


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CriterionIn(_Strict):
    name: Name
    direction: Direction
    weight: Annotated[float, Field(ge=0, le=MAX_WEIGHT, allow_inf_nan=False)]
    unit: Annotated[str, StringConstraints(max_length=MAX_NAME_LENGTH)] = ""


class ConstraintIn(_Strict):
    criterion: Name
    operator: Operator
    threshold: RawNumber


class DecisionIn(_Strict):
    title: Annotated[str, StringConstraints(max_length=MAX_NAME_LENGTH)] = ""
    description: Annotated[str, StringConstraints(max_length=MAX_NOTE_LENGTH)] = ""
    options: Annotated[list[Name], Field(min_length=MIN_OPTIONS, max_length=MAX_OPTIONS)]
    criteria: Annotated[list[CriterionIn], Field(min_length=1, max_length=MAX_CRITERIA)]
    # values[option][criterion] -> raw number
    values: dict[Name, dict[Name, RawNumber]]
    constraints: Annotated[list[ConstraintIn], Field(max_length=MAX_CONSTRAINTS)] = []


class OptionOut(BaseModel):
    name: str
    eligible: bool
    score: float | None
    rank: int | None
    tied: bool
    normalized: dict[str, float]
    contributions: dict[str, float]
    violations: list[str]


class AnalysisOut(BaseModel):
    normalized_weights: dict[str, float]
    options: list[OptionOut]
    has_tie_for_first: bool
    explanation: list[str]
    method: str


class AIChatMessage(_Strict):
    role: Annotated[str, StringConstraints(min_length=1, max_length=32)]
    content: Annotated[str, StringConstraints(max_length=MAX_NOTE_LENGTH)]


class AICriterionDraft(_Strict):
    name: Name
    direction: Direction
    weight: float | None = None
    unit: Annotated[str, StringConstraints(max_length=MAX_NAME_LENGTH)] = ""


class AIConstraintDraft(_Strict):
    criterion: Name
    operator: Operator
    threshold: RawNumber


class AIDecisionDraft(_Strict):
    title: Annotated[str, StringConstraints(max_length=MAX_NAME_LENGTH)] = ""
    description: Annotated[str, StringConstraints(max_length=MAX_NOTE_LENGTH)] = ""
    options: Annotated[list[Name], Field(min_length=2, max_length=MAX_OPTIONS)] = []
    criteria: Annotated[list[AICriterionDraft], Field(min_length=1, max_length=MAX_CRITERIA)] = []
    values: dict[Name, dict[Name, RawNumber | None]] = {}
    constraints: Annotated[list[AIConstraintDraft], Field(max_length=MAX_CONSTRAINTS)] = []
    unknowns: Annotated[list[str], Field(max_length=MAX_OPTIONS)] = []
    notes: Annotated[str, StringConstraints(max_length=MAX_NOTE_LENGTH)] = ""


class AIChatRequest(_Strict):
    messages: Annotated[list[AIChatMessage], Field(min_length=1, max_length=20)]
    draft: AIDecisionDraft | None = None


class AIChatResponse(_Strict):
    available: bool
    message: str
    draft: AIDecisionDraft | None = None
    warnings: list[str] = []
    follow_up_questions: list[str] = []
    unknown_fields: list[str] = []


class TemplateOut(_Strict):
    id: Annotated[str, StringConstraints(pattern=r"^[a-z0-9-]{1,50}$")]
    name: Name
    description: Annotated[str, StringConstraints(max_length=MAX_NOTE_LENGTH)]
    illustrative: bool
    criteria: Annotated[list[CriterionIn], Field(min_length=1, max_length=MAX_CRITERIA)]
