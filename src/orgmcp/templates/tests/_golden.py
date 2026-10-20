"""Helpers shared by the contract suites: the expected bytes of a case, and the call of a case on an implementation."""

from __future__ import annotations

from ._cases import EXPECTED, Case


def expected(name: str, suffix: str = ".txt") -> str:
    """The text captured before the move, decoded without any newline translation."""
    return (EXPECTED / f"{name}{suffix}").read_bytes().decode("utf-8")


def render(implementation: object, case: Case) -> str:
    """Call ``case.method`` of ``implementation`` with the case's arguments."""
    method = getattr(implementation, case.method)
    result = method(*case.args, **case.kwargs)
    assert isinstance(result, str)
    return result
