"""Convert between API models and engine models."""

from app.api.schemas import AnalysisOut, DecisionIn, OptionOut
from app.engine import AnalysisResult, Constraint, Criterion, DecisionModel, explain

METHOD_NOTE = (
    "Weighted-sum model with min-max normalization over eligible options only. "
    "Scores are relative to the options entered; see docs/SCORING_MODEL.md."
)


def to_engine_model(payload: DecisionIn) -> DecisionModel:
    return DecisionModel(
        options=tuple(payload.options),
        criteria=tuple(
            Criterion(c.name, c.direction, c.weight, c.unit) for c in payload.criteria
        ),
        values={option: dict(row) for option, row in payload.values.items()},
        constraints=tuple(
            Constraint(c.criterion, c.operator, c.threshold) for c in payload.constraints
        ),
    )


def to_response(result: AnalysisResult) -> AnalysisOut:
    return AnalysisOut(
        normalized_weights=result.normalized_weights,
        options=[
            OptionOut(
                name=o.name,
                eligible=o.eligible,
                score=o.score,
                rank=o.rank,
                tied=o.tied,
                normalized=o.normalized,
                contributions=o.contributions,
                violations=list(o.violations),
            )
            for o in result.options
        ],
        has_tie_for_first=result.has_tie_for_first,
        explanation=explain(result),
        method=METHOD_NOTE,
    )
