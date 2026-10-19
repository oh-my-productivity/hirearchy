"""What an agent can hand down and how that is said: the arithmetic and the words of ``delegable`` and ``grant_hint`` (they are shown to agents)."""

from __future__ import annotations

import pytest

from orgmcp.budget._hint import grant_hint_text, most_delegable


@pytest.mark.parametrize(
    ("budget", "outstanding", "most"),
    [(3, 0, 2), (2, 1, 0), (3, 1, 1), (1, 0, 0), (0, 0, 0), (-2, 0, 0), (5, 3, 1), (4, 2, 1), (10, 0, 9)],
)
def test_one_run_is_kept_per_outstanding_delegation_and_one_for_the_next(budget: int, outstanding: int, most: int) -> None:
    assert most_delegable(budget, outstanding) == most


def test_with_room_the_hint_says_how_much_can_be_handed_down() -> None:
    assert grant_hint_text("ceo", 3, 1) == (
        "`ceo` now has 3 run(s) and 1 outstanding delegation(s); with one more delegation it can hand down at most 1 run(s)."
    )


@pytest.mark.parametrize(
    ("budget", "outstanding", "more", "needed"),
    [(2, 1, 1, 3), (0, 0, 2, 2), (1, 0, 1, 2), (3, 2, 1, 4), (-1, 0, 3, 2)],
)
def test_without_room_the_hint_says_how_much_more_is_needed(budget: int, outstanding: int, more: int, needed: int) -> None:
    assert grant_hint_text("ceo/ops", budget, outstanding) == (
        f"`ceo/ops` now has {budget} run(s) and {outstanding} outstanding delegation(s): with {budget} run(s) and {outstanding} outstanding "
        f"delegation(s) it cannot delegate anything; it can only process results or work itself - grant at least {more} more "
        f"(a budget of {needed}) to allow one delegation of 1 run."
    )
