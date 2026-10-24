"""Scoring, ranking, ties, and constraints, checked against docs/SCORING_MODEL.md."""

import pytest

from app.engine import Constraint, Criterion, Direction, ModelValidationError, Operator, analyze
from tests.helpers import laptop_model, make_model


def by_name(result):
    return {option.name: option for option in result.options}


# ---- Reference example (hand-calculated) -------------------------------------------------


def test_reference_scores_match_hand_calculation() -> None:
    options = by_name(analyze(laptop_model()))
    assert options["A"].score == pytest.approx(0.5)
    assert options["B"].score == pytest.approx(0.6)
    assert options["C"].score == pytest.approx(0.4)


def test_reference_ranking_is_b_a_c() -> None:
    result = analyze(laptop_model())
    assert [o.name for o in result.ranked] == ["B", "A", "C"]
    assert [o.rank for o in result.ranked] == [1, 2, 3]
    assert not any(o.tied for o in result.ranked)
    assert not result.has_tie_for_first


def test_reference_contributions_match_hand_calculation() -> None:
    options = by_name(analyze(laptop_model()))
    assert options["A"].contributions == pytest.approx({"Price": 0.20, "Quality": 0.30})
    assert options["B"].contributions == pytest.approx({"Price": 0.00, "Quality": 0.60})
    assert options["C"].contributions == pytest.approx({"Price": 0.40, "Quality": 0.00})


def test_contributions_sum_to_score_for_every_option() -> None:
    for option in analyze(laptop_model()).ranked:
        assert sum(option.contributions.values()) == pytest.approx(option.score)


def test_weights_are_rescaled_to_sum_to_one() -> None:
    weights = analyze(laptop_model()).normalized_weights
    assert weights == pytest.approx({"Price": 0.4, "Quality": 0.6})
    assert sum(weights.values()) == pytest.approx(1.0)


@pytest.mark.parametrize("price_weight, quality_weight", [(40, 60), (2, 3), (0.4, 0.6)])
def test_scale_invariance_of_weights(price_weight: float, quality_weight: float) -> None:
    model = laptop_model(price_weight=price_weight, quality_weight=quality_weight)
    options = by_name(analyze(model))
    assert options["A"].score == pytest.approx(0.5)
    assert options["B"].score == pytest.approx(0.6)
    assert options["C"].score == pytest.approx(0.4)


def test_result_does_not_depend_on_option_order() -> None:
    base = by_name(analyze(laptop_model()))
    reordered_model = make_model(
        ["C", "A", "B"], laptop_model().criteria, laptop_model().values
    )
    reordered = by_name(analyze(reordered_model))
    for name in "ABC":
        assert reordered[name].score == pytest.approx(base[name].score)
        assert reordered[name].rank == base[name].rank


def test_zero_weight_criterion_has_no_influence() -> None:
    result = analyze(laptop_model(price_weight=0, quality_weight=10))
    options = by_name(result)
    assert [o.name for o in result.ranked] == ["B", "A", "C"]
    assert options["B"].score == pytest.approx(1.0)
    assert options["A"].score == pytest.approx(0.5)
    assert options["C"].score == pytest.approx(0.0)
    assert all(o.contributions["Price"] == 0 for o in result.ranked)


def test_weight_change_reverses_the_ranking() -> None:
    # Price-heavy weights make C win, quality-heavy weights make B win (see SCORING_MODEL.md).
    price_heavy = analyze(laptop_model(price_weight=9, quality_weight=1))
    quality_heavy = analyze(laptop_model(price_weight=1, quality_weight=9))
    assert price_heavy.ranked[0].name == "C"
    assert quality_heavy.ranked[0].name == "B"


# ---- Ties ----------------------------------------------------------------------------------


def test_equal_weights_tie_all_options_at_rank_one() -> None:
    result = analyze(laptop_model(price_weight=5, quality_weight=5))
    assert [o.score for o in result.ranked] == pytest.approx([0.5, 0.5, 0.5])
    assert [o.rank for o in result.ranked] == [1, 1, 1]
    assert all(o.tied for o in result.ranked)
    assert result.has_tie_for_first


def test_tied_options_keep_the_order_they_were_entered() -> None:
    result = analyze(laptop_model(price_weight=5, quality_weight=5))
    assert [o.name for o in result.ranked] == ["A", "B", "C"]


def test_competition_ranking_skips_after_a_tie() -> None:
    criteria = [Criterion("Score", Direction.BENEFIT, 1)]
    values = {"X": {"Score": 10}, "Y": {"Score": 10}, "Z": {"Score": 0}}
    result = analyze(make_model(["X", "Y", "Z"], criteria, values))
    assert [(o.name, o.rank, o.tied) for o in result.ranked] == [
        ("X", 1, True),
        ("Y", 1, True),
        ("Z", 3, False),
    ]


def test_tolerance_controls_what_counts_as_a_tie() -> None:
    criteria = [Criterion("Score", Direction.BENEFIT, 1)]
    values = {"X": {"Score": 100}, "Y": {"Score": 95}, "Z": {"Score": 0}}
    model = make_model(["X", "Y", "Z"], criteria, values)
    assert [o.rank for o in analyze(model).ranked] == [1, 2, 3]
    assert [o.rank for o in analyze(model, tolerance=0.1).ranked] == [1, 1, 3]


def test_criterion_where_all_options_are_equal_does_not_change_the_order() -> None:
    criteria = [Criterion("Same", Direction.BENEFIT, 5), Criterion("Rating", Direction.BENEFIT, 5)]
    values = {"X": {"Same": 3, "Rating": 9}, "Y": {"Same": 3, "Rating": 1}}
    result = analyze(make_model(["X", "Y"], criteria, values))
    assert [o.name for o in result.ranked] == ["X", "Y"]
    assert by_name(result)["X"].normalized["Same"] == 0.5
    assert by_name(result)["Y"].normalized["Same"] == 0.5


# ---- Hard constraints -------------------------------------------------------------------------


def test_constraint_excludes_option_and_renormalizes_over_eligible_options() -> None:
    model = laptop_model([Constraint("Price", Operator.AT_MOST, 900)])
    result = analyze(model)
    options = by_name(result)
    # Eligible-only normalization (D-002): A = 0.6, C = 0.4, as worked out in SCORING_MODEL.md.
    assert [o.name for o in result.ranked] == ["A", "C"]
    assert options["A"].score == pytest.approx(0.6)
    assert options["C"].score == pytest.approx(0.4)
    assert [o.name for o in result.ineligible] == ["B"]
    assert options["B"].score is None
    assert options["B"].rank is None
    assert options["B"].violations == ("Price is 1000, but must be at most 900.",)


def test_ineligible_option_is_never_ranked_even_with_the_highest_raw_score() -> None:
    # B has the best quality and, without the constraint, the best score.
    assert analyze(laptop_model()).ranked[0].name == "B"
    constrained = analyze(laptop_model([Constraint("Price", Operator.AT_MOST, 900)]))
    assert "B" not in [o.name for o in constrained.ranked]


def test_value_exactly_equal_to_threshold_passes() -> None:
    result = analyze(laptop_model([Constraint("Price", Operator.AT_MOST, 800)]))
    assert [o.name for o in result.ranked] == ["A", "C"]
    result = analyze(laptop_model([Constraint("Quality", Operator.AT_LEAST, 7)]))
    assert [o.name for o in result.ranked] == ["B", "A"]


def test_all_violations_for_an_option_are_reported() -> None:
    constraints = [
        Constraint("Price", Operator.AT_MOST, 700),
        Constraint("Quality", Operator.AT_LEAST, 8),
    ]
    options = by_name(analyze(laptop_model(constraints)))
    assert options["A"].violations == (
        "Price is 800, but must be at most 700.",
        "Quality is 7, but must be at least 8.",
    )


def test_all_options_ineligible_gives_empty_ranking_not_a_crash() -> None:
    constraints = [
        Constraint("Price", Operator.AT_MOST, 700),
        Constraint("Quality", Operator.AT_LEAST, 8),
    ]
    result = analyze(laptop_model(constraints))
    assert result.ranked == ()
    assert [o.name for o in result.ineligible] == ["A", "B", "C"]
    assert not result.has_tie_for_first


def test_single_eligible_option_gets_neutral_scores_and_rank_one() -> None:
    result = analyze(laptop_model([Constraint("Price", Operator.AT_MOST, 700)]))
    assert [o.name for o in result.ranked] == ["C"]
    only = result.ranked[0]
    assert only.rank == 1
    assert not only.tied
    assert only.score == pytest.approx(0.5)  # every criterion is constant -> 0.5 (D-004)


def test_violation_message_includes_the_unit() -> None:
    model = laptop_model([Constraint("Price", Operator.AT_MOST, 900)], unit="BDT")
    options = by_name(analyze(model))
    assert options["B"].violations == ("Price is 1000 BDT, but must be at most 900 BDT.",)


# ---- Numerical edge cases ------------------------------------------------------------------


def test_negative_and_decimal_values_are_handled() -> None:
    criteria = [Criterion("Profit", Direction.BENEFIT, 1), Criterion("Cost", Direction.COST, 1)]
    values = {
        "X": {"Profit": -2.5, "Cost": 0.25},
        "Y": {"Profit": 7.5, "Cost": 0.75},
    }
    options = by_name(analyze(make_model(["X", "Y"], criteria, values)))
    # X: profit 0, cost 1 -> 0.5. Y: profit 1, cost 0 -> 0.5. An exact tie.
    assert options["X"].score == pytest.approx(0.5)
    assert options["Y"].score == pytest.approx(0.5)


def test_large_allowed_values_do_not_break_the_calculation() -> None:
    criteria = [Criterion("Size", Direction.BENEFIT, 1)]
    values = {"X": {"Size": 1e12}, "Y": {"Size": -1e12}}
    result = analyze(make_model(["X", "Y"], criteria, values))
    assert [o.name for o in result.ranked] == ["X", "Y"]
    assert result.ranked[0].score == pytest.approx(1.0)


def test_scores_stay_between_zero_and_one() -> None:
    for option in analyze(laptop_model()).ranked:
        assert 0.0 <= option.score <= 1.0


def test_invalid_model_raises_instead_of_producing_a_result() -> None:
    with pytest.raises(ModelValidationError):
        analyze(laptop_model(price_weight=-1))
