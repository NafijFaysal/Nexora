"""Hard-constraint checking with plain-language reasons."""

from app.engine.models import Constraint, DecisionModel, Operator


def _format_number(value: float) -> str:
    return f"{value:g}"


def _with_unit(text: str, unit: str) -> str:
    return f"{text} {unit}" if unit else text


def check_constraint(constraint: Constraint, value: float, unit: str = "") -> str | None:
    """Return a violation message, or None when the value satisfies the constraint.

    A value exactly equal to the threshold passes. The comparison is on raw values
    with no tolerance, because users type exact limits such as a budget.
    """
    if constraint.operator is Operator.AT_MOST:
        if value <= constraint.threshold:
            return None
        relation = "at most"
    else:
        if value >= constraint.threshold:
            return None
        relation = "at least"
    actual = _with_unit(_format_number(value), unit)
    limit = _with_unit(_format_number(constraint.threshold), unit)
    return f"{constraint.criterion} is {actual}, but must be {relation} {limit}."


def find_violations(model: DecisionModel, option: str) -> tuple[str, ...]:
    """Every violated hard constraint for one option, in constraint order."""
    units = {c.name: c.unit for c in model.criteria}
    row = model.values[option]
    messages = []
    for constraint in model.constraints:
        message = check_constraint(
            constraint, row[constraint.criterion], units.get(constraint.criterion, "")
        )
        if message is not None:
            messages.append(message)
    return tuple(messages)
