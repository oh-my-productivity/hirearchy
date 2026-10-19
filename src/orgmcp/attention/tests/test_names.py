"""``names``: up to three agents by name, the others counted."""

from __future__ import annotations

import pytest

from orgmcp.attention._waiting import names

from ._support import RED


@RED
@pytest.mark.parametrize(
    ("addrs", "expected"),
    [
        ([], ""),
        (["a"], "a"),
        (["a", "b"], "a, b"),
        (["a", "b", "c"], "a, b, c"),
        (["a", "b", "c", "d"], "a, b, c and 1 more"),
        (["a", "b", "c", "d", "e", "f"], "a, b, c and 3 more"),
    ],
)
def test_three_are_named_and_the_rest_counted(addrs: list[str], expected: str) -> None:
    assert names(addrs) == expected
