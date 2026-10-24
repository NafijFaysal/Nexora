"""Domain validation for decision models.

Type-level request checks happen at the API layer. This module enforces the rules the
math depends on, so the engine is safe to call directly and is tested on its own.
All problems are collected and reported together instead of stopping at the first one.
"""

import math

from app.engine.models import Constraint, Criterion, DecisionModel, Direction, Operator

MIN_OPTIONS = 2
MAX_OPTIONS = 20
MIN_CRITERIA = 1
MAX_CRITERIA = 15
MAX_NAME_LENGTH = 100
# Bounds keep sums and differences far from float overflow and precision loss.
MAX_ABS_VALUE = 1e12
MAX_WEIGHT = 1000.0


class ModelValidationError(ValueError):
    """Raised when a decision model breaks a rule. `problems` lists every issue found."""

    def __init__(self, problems: list[str]) -> None:
        super().__init__("; ".join(problems))
        self.problems = tuple(problems)


def _is_number(value: object) -> bool:
    # bool is a subclass of int in Python; True/False must not pass as numbers.
    return isinstance(value, int | float) and not isinstance(value, bool)


def _check_number(label: str, value: object, limit: float, problems: list[str]) -> bool:
    if not _is_number(value):
        problems.append(f"{label} must be a number.")
        return False
    number = float(value)  # type: ignore[arg-type]
    if not math.isfinite(number):
        problems.append(f"{label} must be a finite number.")
        return False
    if abs(number) > limit:
        problems.append(f"{label} must be between -{limit:g} and {limit:g}.")
        return False
    return True


def _check_names(kind: str, names: tuple[str, ...], problems: list[str]) -> None:
    seen: set[str] = set()
    for name in names:
        if not isinstance(name, str) or not name.strip():
            problems.append(f"Every {kind} needs a non-empty name.")
            continue
        if len(name) > MAX_NAME_LENGTH:
            problems.append(f"The {kind} name '{name[:20]}...' is longer than {MAX_NAME_LENGTH}.")
        key = name.strip().casefold()
        if key in seen:
            problems.append(f"Duplicate {kind} name: '{name}'.")
        seen.add(key)


def _check_criteria(criteria: tuple[Criterion, ...], problems: list[str]) -> None:
    weights_ok = True
    total = 0.0
    for criterion in criteria:
        label = f"The weight of '{criterion.name}'"
        if not isinstance(criterion.direction, Direction):
            problems.append(f"The direction of '{criterion.name}' must be benefit or cost.")
        if not isinstance(criterion.unit, str) or len(criterion.unit) > MAX_NAME_LENGTH:
            problems.append(f"The unit of '{criterion.name}' must be short text.")
        if not _check_number(label, criterion.weight, MAX_WEIGHT, problems):
            weights_ok = False
        elif criterion.weight < 0:
            problems.append(f"{label} cannot be negative.")
            weights_ok = False
        else:
            total += float(criterion.weight)
    if weights_ok and criteria and total == 0:
        problems.append("At least one criterion needs a weight above zero.")


def _check_values(model: DecisionModel, problems: list[str]) -> None:
    for option in model.options:
        row = model.values.get(option)
        if row is None:
            problems.append(f"No values were given for option '{option}'.")
            continue
        for criterion in model.criteria:
            if criterion.name not in row:
                problems.append(f"Missing value: '{option}' on '{criterion.name}'.")
            else:
                _check_number(
                    f"The value of '{option}' on '{criterion.name}'",
                    row[criterion.name],
                    MAX_ABS_VALUE,
                    problems,
                )
        known = {c.name for c in model.criteria}
        for extra in row:
            if extra not in known:
                problems.append(f"'{option}' has a value for unknown criterion '{extra}'.")
    for name in model.values:
        if name not in model.options:
            problems.append(f"Values were given for unknown option '{name}'.")


def _check_constraints(
    constraints: tuple[Constraint, ...], criteria: tuple[Criterion, ...], problems: list[str]
) -> None:
    known = {c.name for c in criteria}
    for constraint in constraints:
        if constraint.criterion not in known:
            problems.append(f"A constraint refers to unknown criterion '{constraint.criterion}'.")
        if not isinstance(constraint.operator, Operator):
            problems.append("A constraint operator must be <= or >=.")
        _check_number(
            f"The threshold for '{constraint.criterion}'",
            constraint.threshold,
            MAX_ABS_VALUE,
            problems,
        )


def validate_model(model: DecisionModel) -> None:
    """Raise ModelValidationError listing every problem, or return None if the model is valid."""
    problems: list[str] = []

    if not MIN_OPTIONS <= len(model.options) <= MAX_OPTIONS:
        problems.append(f"A decision needs between {MIN_OPTIONS} and {MAX_OPTIONS} options.")
    if not MIN_CRITERIA <= len(model.criteria) <= MAX_CRITERIA:
        problems.append(f"A decision needs between {MIN_CRITERIA} and {MAX_CRITERIA} criteria.")

    _check_names("option", model.options, problems)
    _check_names("criterion", tuple(c.name for c in model.criteria), problems)
    _check_criteria(model.criteria, problems)
    _check_values(model, problems)
    _check_constraints(model.constraints, model.criteria, problems)

    if problems:
        raise ModelValidationError(problems)
