"""``Retired`` is data: a named tuple of the address, the runs that went back and who got them; it compares like the tuple it always was."""

from __future__ import annotations

from hirearchy.hierarchy import Retired


def test_retired_has_its_three_fields_in_order() -> None:
    assert Retired._fields == ("addr", "refunded", "refunded_to")


def test_retired_compares_with_a_plain_tuple() -> None:
    assert Retired("ceo", 0, None) == ("ceo", 0, None)
    addr, refunded, to = Retired("ceo/mgr", 7, "ceo")
    assert (addr, refunded, to) == ("ceo/mgr", 7, "ceo")
