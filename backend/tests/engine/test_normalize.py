"""Min-max normalization, checked against hand calculations."""

import pytest

from app.engine import Direction
from app.engine.normalize import CONSTANT_CRITERION_VALUE, normalize_criterion


def test_cost_direction_matches_hand_calculation() -> None:
    # (1000 - x) / 400 for prices 800, 1000, 600
    result = normalize_criterion([800, 1000, 600], Direction.COST)
    assert result == pytest.approx([0.5, 0.0, 1.0])


def test_benefit_direction_matches_hand_calculation() -> None:
    # (x - 5) / 4 for ratings 7, 9, 5
    result = normalize_criterion([7, 9, 5], Direction.BENEFIT)
    assert result == pytest.approx([0.5, 1.0, 0.0])


def test_all_equal_values_give_neutral_value() -> None:
    assert normalize_criterion([3, 3, 3], Direction.BENEFIT) == [CONSTANT_CRITERION_VALUE] * 3
    assert normalize_criterion([3, 3, 3], Direction.COST) == [CONSTANT_CRITERION_VALUE] * 3


def test_negative_and_decimal_values() -> None:
    # Cost criterion: low -5.5, high 0.5, span 6.
    result = normalize_criterion([-5.5, -2.5, 0.5], Direction.COST)
    assert result == pytest.approx([1.0, 0.5, 0.0])


def test_extreme_allowed_magnitudes() -> None:
    result = normalize_criterion([1e12, -1e12], Direction.BENEFIT)
    assert result == pytest.approx([1.0, 0.0])


def test_results_stay_between_zero_and_one() -> None:
    for direction in Direction:
        result = normalize_criterion([0.1, 7.3, -2.2, 100.0, 55.5], direction)
        assert all(0.0 <= value <= 1.0 for value in result)


def test_empty_input_gives_empty_output() -> None:
    assert normalize_criterion([], Direction.BENEFIT) == []
