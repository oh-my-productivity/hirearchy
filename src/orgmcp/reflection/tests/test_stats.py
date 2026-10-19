"""``summarize`` and ``stats_by_version``: pure functions over cases."""

from __future__ import annotations

import pytest

from orgmcp.kernel import Message
from orgmcp.reflection import Case, Stats, Verdict, stats_by_version, summarize

pytestmark = pytest.mark.xfail(strict=True, reason="red: C-reflection")


def verdict(kind: str) -> Verdict:
    note = Message(sender="root", to="ceo", type="note", body="b", feedback=kind)
    return Verdict(kind, "", None, "T", 0, note)


def case(state: str = "done", *, used: int = 0, runs: int = 2, reworks: int = 0, verdicts: tuple[str, ...] = ()) -> Case:
    return Case(
        id="C", service="s", owner="ceo", tasks=[Message(sender="root", to="ceo", type="task", body="b")], result=None, state=state, playbook=0,
        used=used, reworks=reworks, budget=5, runs=runs, lessons=[], verdicts=[verdict(v) for v in verdicts], started=None, finished=None,
    )


def test_nothing_summarizes_to_nothing() -> None:
    assert summarize([]) == Stats()


def test_a_blocked_case_counts_as_open() -> None:
    assert summarize([case("open"), case("blocked"), case("done"), case("failed")]) == Stats(requests=4, done=1, failed=1, open=2, finished_runs=4)


def test_only_finished_cases_add_their_runs() -> None:
    assert summarize([case("done", runs=3), case("failed", runs=4), case("open", runs=9), case("blocked", runs=9)]).finished_runs == 7


def test_a_reworked_case_counts_once() -> None:
    assert summarize([case(reworks=3), case(reworks=0)]).reworked == 1


def test_the_final_verdict_of_each_case_is_what_counts() -> None:
    stats = summarize([case(verdicts=("reject", "accept")), case(verdicts=("accept",)), case(verdicts=("accept", "reject")), case()])
    assert (stats.accept, stats.reject, stats.accept_after_reject) == (2, 1, 1)


def test_cases_are_grouped_by_the_version_in_force_when_they_were_first_answered() -> None:
    by = stats_by_version([case(used=2), case(used=0), case("open", used=2), case(used=1)])
    assert list(by) == [0, 1, 2] and by[2].requests == 2 and by[2].open == 1 and by[0].done == 1


def test_no_cases_have_no_versions() -> None:
    assert stats_by_version([]) == {}
