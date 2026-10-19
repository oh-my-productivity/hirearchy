"""The fakes a consumer's test uses instead of an organization: each answers what it is told to and keeps what it was asked."""

from __future__ import annotations

from orgmcp.attention import HumanQueue, OpenWork, Waiting, WaitingOnUser
from orgmcp.attention.testing import FixedOpenWork, FixedWaiting, ListHumanQueue

from ._support import RED


def test_the_fakes_are_the_ports() -> None:
    assert isinstance(FixedWaiting(), WaitingOnUser) and WaitingOnUser in FixedWaiting.__mro__
    assert isinstance(ListHumanQueue(), HumanQueue) and HumanQueue in ListHumanQueue.__mro__
    assert isinstance(FixedOpenWork(), OpenWork) and OpenWork in FixedOpenWork.__mro__


@RED
def test_fixed_waiting_answers_what_it_holds_and_records_the_question() -> None:
    held = Waiting("waiting on you: x", "Your options: y.", False)
    fake = FixedWaiting(held)
    assert fake.analyze() is held
    assert fake.analyze(running={"ceo"}, blocked=("eng",), can_start=False) is held
    assert fake.asked == [(None, (), True), ({"ceo"}, ("eng",), False)]
    fake.waiting = None
    assert fake.analyze() is None


@RED
def test_nothing_waits_by_default() -> None:
    assert FixedWaiting().analyze() is None


@RED
def test_the_list_queue_has_the_lines_of_its_entries() -> None:
    fake = ListHumanQueue([("m1", "Needs you: a"), ("m2", "Needs you: b")])
    assert fake.items() == [("m1", "Needs you: a"), ("m2", "Needs you: b")]
    assert fake.lines() == ["Needs you: a", "Needs you: b"]
    fake.entries.append(("m3", "Needs you: c"))
    assert fake.lines()[-1] == "Needs you: c"


@RED
def test_the_list_queue_hands_out_copies() -> None:
    fake = ListHumanQueue([("m1", "Needs you: a")])
    fake.items().clear()
    assert fake.items() == [("m1", "Needs you: a")]


@RED
def test_fixed_open_work_answers_what_it_holds() -> None:
    fake = FixedOpenWork()
    assert fake.nothing_to_do() is False
    fake.idle = True
    assert fake.nothing_to_do() is True
