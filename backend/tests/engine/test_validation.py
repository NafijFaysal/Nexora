"""Validation rejects bad models with clear messages and never crashes."""

import pytest

from app.engine import (
    Constraint,
    Criterion,
    Direction,
    ModelValidationError,
    Operator,
    validate_model,
)
from tests.helpers import LAPTOP_VALUES, laptop_criteria, laptop_model, make_model


def problems_for(model) -> tuple[str, ...]:
    with pytest.raises(ModelValidationError) as info:
        validate_model(model)
    return info.value.problems


def assert_problem(model, fragment: str) -> None:
    problems = problems_for(model)
    assert any(fragment in problem for problem in problems), problems


def test_reference_model_is_valid() -> None:
    validate_model(laptop_model())


def test_fewer_than_two_options_rejected() -> None:
    model = make_model(["A"], laptop_criteria(), {"A": LAPTOP_VALUES["A"]})
    assert_problem(model, "between 2 and 20 options")


def test_more_than_twenty_options_rejected() -> None:
    names = [f"Option {i}" for i in range(21)]
    values = {name: {"Q": 1.0} for name in names}
    model = make_model(names, [Criterion("Q", Direction.BENEFIT, 1)], values)
    assert_problem(model, "between 2 and 20 options")


def test_no_criteria_rejected() -> None:
    model = make_model(["A", "B"], [], {"A": {}, "B": {}})
    assert_problem(model, "between 1 and 15 criteria")


def test_duplicate_option_names_rejected_ignoring_case_and_spaces() -> None:
    model = make_model(["A", " a "], laptop_criteria(), {"A": LAPTOP_VALUES["A"], " a ": {}})
    assert_problem(model, "Duplicate option name")


def test_duplicate_criterion_names_rejected() -> None:
    criteria = [Criterion("Price", Direction.COST, 1), Criterion("price", Direction.COST, 1)]
    model = make_model(["A", "B"], criteria, {"A": {"Price": 1}, "B": {"Price": 2}})
    assert_problem(model, "Duplicate criterion name")


def test_empty_name_rejected() -> None:
    model = make_model(["A", "  "], laptop_criteria(), {"A": LAPTOP_VALUES["A"], "  ": {}})
    assert_problem(model, "non-empty name")


def test_overlong_name_rejected() -> None:
    long_name = "x" * 101
    values = {"A": LAPTOP_VALUES["A"], long_name: {}}
    model = make_model(["A", long_name], laptop_criteria(), values)
    assert_problem(model, "longer than 100")


def test_negative_weight_rejected() -> None:
    assert_problem(laptop_model(price_weight=-1), "cannot be negative")


def test_all_zero_weights_rejected() -> None:
    assert_problem(laptop_model(price_weight=0, quality_weight=0), "weight above zero")


def test_weight_above_limit_rejected() -> None:
    assert_problem(laptop_model(price_weight=1001), "weight of 'Price'")


def test_missing_value_rejected_not_treated_as_zero() -> None:
    values = {**LAPTOP_VALUES, "C": {"Price": 600}}
    model = make_model(["A", "B", "C"], laptop_criteria(), values)
    assert_problem(model, "Missing value: 'C' on 'Quality'")


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), float("-inf")])
def test_non_finite_values_rejected(bad: float) -> None:
    values = {**LAPTOP_VALUES, "C": {"Price": bad, "Quality": 5}}
    model = make_model(["A", "B", "C"], laptop_criteria(), values)
    assert_problem(model, "finite number")


def test_value_beyond_magnitude_limit_rejected() -> None:
    values = {**LAPTOP_VALUES, "C": {"Price": 1e13, "Quality": 5}}
    model = make_model(["A", "B", "C"], laptop_criteria(), values)
    assert_problem(model, "must be between")


@pytest.mark.parametrize("bad", ["12", True, None])
def test_non_numeric_values_rejected(bad: object) -> None:
    values = {**LAPTOP_VALUES, "C": {"Price": bad, "Quality": 5}}
    model = make_model(["A", "B", "C"], laptop_criteria(), values)
    assert_problem(model, "must be a number")


def test_extra_criterion_in_values_rejected() -> None:
    values = {**LAPTOP_VALUES, "C": {"Price": 600, "Quality": 5, "Colour": 1}}
    model = make_model(["A", "B", "C"], laptop_criteria(), values)
    assert_problem(model, "unknown criterion 'Colour'")


def test_values_for_unknown_option_rejected() -> None:
    values = {**LAPTOP_VALUES, "Z": {"Price": 1, "Quality": 1}}
    model = make_model(["A", "B", "C"], laptop_criteria(), values)
    assert_problem(model, "unknown option 'Z'")


def test_constraint_on_unknown_criterion_rejected() -> None:
    model = laptop_model([Constraint("Weight", Operator.AT_MOST, 2)])
    assert_problem(model, "unknown criterion 'Weight'")


def test_non_finite_constraint_threshold_rejected() -> None:
    model = laptop_model([Constraint("Price", Operator.AT_MOST, float("nan"))])
    assert_problem(model, "threshold")


def test_all_problems_are_reported_together() -> None:
    model = laptop_model([Constraint("Weight", Operator.AT_MOST, 2)], price_weight=-1)
    assert len(problems_for(model)) >= 2
