"""Plain-language explanations built from templates and the real numbers. No AI is used."""

from app.engine.models import AnalysisResult, OptionResult

TOP_CONTRIBUTORS_SHOWN = 2

RELATIVE_SCORES_NOTE = (
    "Scores are relative to the options entered and are a decision aid, not a verdict. "
    "Adding or removing an option can change them."
)


def _top_contributors(option: OptionResult) -> str:
    positive = [(name, value) for name, value in option.contributions.items() if value > 0]
    positive.sort(key=lambda pair: -pair[1])
    top = positive[:TOP_CONTRIBUTORS_SHOWN]
    return ", ".join(f"{name} ({value:.2f})" for name, value in top)


def _leader_sentences(result: AnalysisResult) -> list[str]:
    ranked = result.ranked
    first = ranked[0]
    assert first.score is not None  # eligible options always have a score
    if result.has_tie_for_first:
        leaders = [o.name for o in ranked if o.rank == 1]
        return [
            f"{', '.join(leaders)} tie for first place with a score of {first.score:.2f}. "
            "The inputs do not separate them."
        ]
    sentences = [f"{first.name} ranks first with a score of {first.score:.2f} out of 1."]
    contributors = _top_contributors(first)
    if contributors:
        sentences.append(f"Its largest contributions come from {contributors}.")
    if len(ranked) > 1:
        runner_up = ranked[1]
        assert runner_up.score is not None
        margin = first.score - runner_up.score
        sentences.append(
            f"It leads {runner_up.name} by {margin:.2f} points. "
            "A small margin means the result could change with different weights."
        )
    return sentences


def explain(result: AnalysisResult) -> list[str]:
    """Return explanation sentences. Every number comes from the analysis result."""
    sentences: list[str] = []
    if result.ranked:
        sentences.extend(_leader_sentences(result))
    else:
        sentences.append("No option satisfies every hard constraint, so nothing is ranked.")
    for option in result.ineligible:
        sentences.append(f"{option.name} is not ranked. {' '.join(option.violations)}")
    sentences.append(RELATIVE_SCORES_NOTE)
    return sentences
