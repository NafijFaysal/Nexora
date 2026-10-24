"""Explanations are templated from the real numbers."""

from app.engine import Constraint, Operator, analyze, explain
from app.engine.explain import RELATIVE_SCORES_NOTE
from tests.helpers import laptop_model


def text_for(model) -> str:
    return " ".join(explain(analyze(model)))


def test_names_the_leader_score_and_top_contributor() -> None:
    text = text_for(laptop_model())
    assert "B ranks first with a score of 0.60" in text
    assert "Quality (0.60)" in text


def test_margin_over_runner_up_matches_the_scores() -> None:
    # B 0.60 vs A 0.50 -> 0.10
    assert "It leads A by 0.10 points." in text_for(laptop_model())


def test_tie_for_first_is_reported_as_a_tie() -> None:
    text = text_for(laptop_model(price_weight=5, quality_weight=5))
    assert "A, B, C tie for first place" in text
    assert "ranks first" not in text


def test_ineligible_option_reason_is_shown() -> None:
    text = text_for(laptop_model([Constraint("Price", Operator.AT_MOST, 900)]))
    assert "A ranks first with a score of 0.60" in text
    assert "B is not ranked. Price is 1000, but must be at most 900." in text


def test_no_eligible_option_is_explained() -> None:
    text = text_for(laptop_model([Constraint("Price", Operator.AT_MOST, 100)]))
    assert "No option satisfies every hard constraint" in text


def test_relative_scores_note_is_always_last() -> None:
    assert explain(analyze(laptop_model()))[-1] == RELATIVE_SCORES_NOTE
