"""``message_budget``: the runs of budget a message file carries, 0 for anything that is not a valid message."""

from __future__ import annotations

import pytest

from orgmcp.agents._budget import message_budget

from ._support import message


@pytest.mark.parametrize(
    ("text", "budget"),
    [
        (message(7), 7),
        (message("7"), 7),
        (message(-3), -3),
        (message(2.9), 2),
        (message(True), 1),
        (message(), 0),
        (message(7, extra="\nid: 20260101T000000-root-0001\ntitle: T\nwake: false"), 7),
        (message(7).replace("\n", "\r\n"), 7),
        (message(7).replace("\n", "\r"), 7),
        ("---\nfrom: root\nto: ceo\ntype: task\nbudget: seven\n---\nx\n", 0),
        ("---\nfrom: root\nto: ceo\ntype: task\nbudget: [1]\n---\nx\n", 0),
        ("---\nfrom: root\nto: ceo\ntype: task\nbudget: {a: 1}\n---\nx\n", 0),
        ("---\nfrom: root\nto: ceo\ntype: task\nbudget: .nan\n---\nx\n", 0),
        ("---\nto: ceo\ntype: task\nbudget: 7\n---\nx\n", 0),
        ("---\nfrom: root\ntype: task\nbudget: 7\n---\nx\n", 0),
        ("---\nfrom: root\nto: ceo\nbudget: 7\n---\nx\n", 0),
        ("---\nfrom: 0\nto: ceo\ntype: task\nbudget: 7\n---\nx\n", 0),
        ("budget: 7\nno frontmatter\n", 0),
        ("---\nbudget: [unclosed\n---\n", 0),
        ("---\n- a list\n---\nbody\n", 0),
        ("---\n---\nbody\n", 0),
        ("", 0),
    ],
)
def test_the_budget_of_a_valid_message_and_zero_for_the_rest(text: str, budget: int) -> None:
    assert message_budget(text) == budget


def test_an_infinite_budget_is_not_caught() -> None:
    """Like the check it came from: ``int(inf)`` is an ``OverflowError`` that nobody turned into a verdict."""
    with pytest.raises(OverflowError):
        message_budget("---\nfrom: root\nto: ceo\ntype: task\nbudget: .inf\n---\nx\n")
