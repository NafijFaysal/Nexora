"""Builders shared by tests.

The laptop example is the hand-calculated reference from docs/SCORING_MODEL.md.
Expected numbers in the tests come from that document, not from running the code.
"""

from collections.abc import Mapping, Sequence

from app.engine import Constraint, Criterion, DecisionModel, Direction

LAPTOP_VALUES: dict[str, dict[str, float]] = {
    "A": {"Price": 800, "Quality": 7},
    "B": {"Price": 1000, "Quality": 9},
    "C": {"Price": 600, "Quality": 5},
}


def make_model(
    options: Sequence[str],
    criteria: Sequence[Criterion],
    values: Mapping[str, Mapping[str, float]],
    constraints: Sequence[Constraint] = (),
) -> DecisionModel:
    return DecisionModel(
        options=tuple(options),
        criteria=tuple(criteria),
        values=values,
        constraints=tuple(constraints),
    )


def laptop_criteria(
    price_weight: float = 4, quality_weight: float = 6, unit: str = ""
) -> list[Criterion]:
    return [
        Criterion("Price", Direction.COST, price_weight, unit),
        Criterion("Quality", Direction.BENEFIT, quality_weight),
    ]


def laptop_model(
    constraints: Sequence[Constraint] = (),
    price_weight: float = 4,
    quality_weight: float = 6,
    unit: str = "",
) -> DecisionModel:
    return make_model(
        ["A", "B", "C"],
        laptop_criteria(price_weight, quality_weight, unit),
        LAPTOP_VALUES,
        constraints,
    )
