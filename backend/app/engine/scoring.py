"""Weighted-sum scoring, ranking, and tie handling. See docs/SCORING_MODEL.md."""

from app.engine.constraints import find_violations
from app.engine.models import AnalysisResult, DecisionModel, OptionResult
from app.engine.normalize import normalize_criterion
from app.engine.validation import validate_model

# Scores closer than this are treated as equal. Floating-point sums of the same
# contributions in a different order can differ by about 1e-16, so ties need a tolerance.
TIE_TOLERANCE = 1e-9


def normalize_weights(model: DecisionModel) -> dict[str, float]:
    """Rescale raw weights so they sum to 1. Assumes the model is already validated."""
    total = sum(float(c.weight) for c in model.criteria)
    return {c.name: float(c.weight) / total for c in model.criteria}


def _assign_ranks(
    scored: list[tuple[str, float]], tolerance: float
) -> dict[str, tuple[int, bool]]:
    """Competition ranking ("1, 1, 3"). Returns {name: (rank, tied)}.

    `scored` must already be sorted by descending score. Each score is compared with the
    first score of its group, not with its neighbour, so a long chain of tiny steps
    cannot drift into one giant tie.
    """
    ranks: dict[str, tuple[int, bool]] = {}
    group_start = 0
    for position in range(len(scored)):
        if position > 0 and abs(scored[group_start][1] - scored[position][1]) > tolerance:
            group_start = position
        ranks[scored[position][0]] = (group_start + 1, False)
    group_sizes: dict[int, int] = {}
    for rank, _ in ranks.values():
        group_sizes[rank] = group_sizes.get(rank, 0) + 1
    return {name: (rank, group_sizes[rank] > 1) for name, (rank, _) in ranks.items()}


def analyze(model: DecisionModel, tolerance: float = TIE_TOLERANCE) -> AnalysisResult:
    """Validate, apply hard constraints, normalize, score, and rank a decision model.

    Raises ModelValidationError if the model breaks any rule.
    """
    validate_model(model)
    weights = normalize_weights(model)

    violations = {option: find_violations(model, option) for option in model.options}
    eligible = [option for option in model.options if not violations[option]]

    # Normalize over eligible options only (decision D-002).
    normalized: dict[str, dict[str, float]] = {option: {} for option in eligible}
    for criterion in model.criteria:
        raw = [model.values[option][criterion.name] for option in eligible]
        scaled = normalize_criterion(raw, criterion.direction)
        for option, value in zip(eligible, scaled, strict=True):
            normalized[option][criterion.name] = value

    contributions = {
        option: {name: weights[name] * value for name, value in normalized[option].items()}
        for option in eligible
    }
    # The score is the sum of the contributions, so the charts add up exactly.
    scores = {option: sum(contributions[option].values()) for option in eligible}

    by_score = sorted(eligible, key=lambda option: -scores[option])
    ranks = _assign_ranks([(option, scores[option]) for option in by_score], tolerance)
    # Within a tie, restore the order the user entered the options. Sorting by score alone
    # could reorder tied options because of floating-point noise around 1e-16.
    entry_position = {option: index for index, option in enumerate(model.options)}
    ordered = sorted(eligible, key=lambda option: (ranks[option][0], entry_position[option]))

    ranked_results = tuple(
        OptionResult(
            name=option,
            eligible=True,
            score=scores[option],
            rank=ranks[option][0],
            tied=ranks[option][1],
            normalized=normalized[option],
            contributions=contributions[option],
            violations=(),
        )
        for option in ordered
    )
    excluded_results = tuple(
        OptionResult(
            name=option,
            eligible=False,
            score=None,
            rank=None,
            tied=False,
            normalized={},
            contributions={},
            violations=violations[option],
        )
        for option in model.options
        if violations[option]
    )
    return AnalysisResult(
        normalized_weights=weights, options=ranked_results + excluded_results
    )
