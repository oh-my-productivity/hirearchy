"""Criteria as the callers write them: a list of strings, or one newline-separated string."""

from __future__ import annotations

from ..kernel import OrgError


def criteria_lines(value: object, what: str, *, required: bool) -> list[str]:
    """A list of criteria from a list or a newline-separated string: stripped, without a leading "- "."""
    raise NotImplementedError
