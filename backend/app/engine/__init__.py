"""Decision-analysis logic.

Architecture rule: nothing in this package may import the web framework, the database,
or the AI module. That keeps the math testable on its own.
"""

from app.engine.explain import explain
from app.engine.models import (
    AnalysisResult,
    Constraint,
    Criterion,
    DecisionModel,
    Direction,
    Operator,
    OptionResult,
)
from app.engine.scoring import analyze
from app.engine.validation import ModelValidationError, validate_model

__all__ = [
    "AnalysisResult",
    "Constraint",
    "Criterion",
    "DecisionModel",
    "Direction",
    "ModelValidationError",
    "Operator",
    "OptionResult",
    "analyze",
    "explain",
    "validate_model",
]
