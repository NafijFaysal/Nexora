"""Min-max normalization for one criterion. See docs/SCORING_MODEL.md, step 3."""

from collections.abc import Sequence

from app.engine.models import Direction

# Used when a criterion cannot separate the options (all values equal). Neutral by design;
# it is not a claim that the options are "half good". Recorded as decision D-004.
CONSTANT_CRITERION_VALUE = 0.5


def normalize_criterion(values: Sequence[float], direction: Direction) -> list[float]:
    """Map raw values to 0..1 where 1 is best and 0 is worst among the given values.

    The result depends on which values are passed in. That is why scores are relative
    to the options entered.
    """
    if not values:
        return []
    low = min(values)
    high = max(values)
    if high == low:
        return [CONSTANT_CRITERION_VALUE] * len(values)
    span = high - low
    if direction is Direction.BENEFIT:
        return [(x - low) / span for x in values]
    return [(high - x) / span for x in values]
