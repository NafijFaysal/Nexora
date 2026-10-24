"""Input and result data structures for the decision engine.

Plain frozen dataclasses with no web, database, or AI dependencies. The API layer
(added later) validates external requests with Pydantic and converts them into these.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum


class Direction(StrEnum):
    """Whether a larger raw value is better (benefit) or worse (cost)."""

    BENEFIT = "benefit"
    COST = "cost"


class Operator(StrEnum):
    """Comparison used by a hard constraint, applied to the raw value."""

    AT_MOST = "<="
    AT_LEAST = ">="


@dataclass(frozen=True)
class Criterion:
    name: str
    direction: Direction
    weight: float  # raw importance; rescaled to sum to 1 during analysis
    unit: str = ""  # display only; the engine never converts units


@dataclass(frozen=True)
class Constraint:
    """A hard limit on one criterion's raw value. Violating it makes an option ineligible."""

    criterion: str
    operator: Operator
    threshold: float


@dataclass(frozen=True)
class DecisionModel:
    options: tuple[str, ...]
    criteria: tuple[Criterion, ...]
    # values[option_name][criterion_name] -> raw number. Every cell must be present.
    values: Mapping[str, Mapping[str, float]]
    constraints: tuple[Constraint, ...] = ()


@dataclass(frozen=True)
class OptionResult:
    name: str
    eligible: bool
    score: float | None  # None for ineligible options
    rank: int | None  # None for ineligible options; tied options share a rank
    tied: bool  # True when another eligible option shares this score
    normalized: dict[str, float]  # empty for ineligible options
    contributions: dict[str, float]  # weight * normalized, per criterion; sums to score
    violations: tuple[str, ...]  # plain-language reasons; empty when eligible


@dataclass(frozen=True)
class AnalysisResult:
    normalized_weights: dict[str, float]
    # Eligible options in rank order (ties keep input order), then ineligible options
    # in input order.
    options: tuple[OptionResult, ...]

    @property
    def ranked(self) -> tuple[OptionResult, ...]:
        return tuple(o for o in self.options if o.eligible)

    @property
    def ineligible(self) -> tuple[OptionResult, ...]:
        return tuple(o for o in self.options if not o.eligible)

    @property
    def has_tie_for_first(self) -> bool:
        return any(o.rank == 1 and o.tied for o in self.options)
