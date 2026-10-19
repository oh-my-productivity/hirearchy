"""Criteria as the callers write them: a list of strings, or one newline-separated string."""

from __future__ import annotations

from ..kernel import OrgError


def criteria_lines(value: object, what: str, *, required: bool) -> list[str]:
    """A list of criteria from a list or a newline-separated string: stripped, without a leading "- "."""
    if value is None:
        items: list[object] = []
    elif isinstance(value, str):
        items = [value]
    elif isinstance(value, (list, tuple)):
        items = list(value)
    else:
        raise OrgError(f"{what} must be a list of strings (or one newline-separated string)")
    out: list[str] = []
    for item in items:
        if not isinstance(item, str):
            raise OrgError(f"{what} must contain only strings (got {item!r})")
        for line in item.splitlines():
            line = line.strip()
            if line.startswith(("- ", "* ")):
                line = line[2:].strip()
            if line and line not in ("-", "*"):
                out.append(line)
    if required and not out:
        raise OrgError(
            f"{what} needs at least one non-empty criterion: concrete, checkable conditions the delivery must meet"
        )
    return out
