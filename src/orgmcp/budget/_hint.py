"""What an agent can hand down, and how that is said (pure; the derived query and the fixed fake both use it). Skeleton: RED."""

from __future__ import annotations


def most_delegable(budget: int, outstanding: int) -> int:
    raise NotImplementedError


def grant_hint_text(addr: str, budget: int, outstanding: int) -> str:
    raise NotImplementedError
