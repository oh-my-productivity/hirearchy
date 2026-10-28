"""The change ladder of 08 4.4 (design section 3): seven rungs, cheapest first."""

from __future__ import annotations

from hirearchy.retro._ladder import RUNGS, rung_line


def test_the_seven_rungs_cheapest_first() -> None:
    assert RUNGS == ("clarify", "adjust the standard", "add slack", "add a checker or integrator", "split", "add a layer", "merge or retire")
    assert rung_line("service", 2, "a one-off task has no contract") == "service (rung 2 of 7, adjust the standard: a one-off task has no contract)"
    assert rung_line("retire", 7, "nothing cheaper applies") == "retire (rung 7 of 7, merge or retire: nothing cheaper applies)"
    assert rung_line("reclaim", 0, "") == "reclaim (no rung: it moves budget, not structure)"
