"""``NoteBudgetReclaimer``: it moves the runs by one delivered note, and takes the amount from the budget query it is given."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from hirearchy.budget._reclaim import NoteBudgetReclaimer
from hirearchy.budget.testing import BudgetWorld, FixedBudget, fixed_world, fs_world, memory_world
from hirearchy.delivery.testing import RecordingDelivery
from hirearchy.kernel import Message, OrgError
from hirearchy.kernel.testing import FakeClock, SequenceIdGenerator

from ._support import grant, make, populated

ENG = "ceo/eng"


@pytest.fixture(params=[fs_world, memory_world, fixed_world], ids=lambda factory: factory.__name__)
def w(request: pytest.FixtureRequest, tmp_path: Path) -> BudgetWorld:
    return make(request, tmp_path)


def recording(tmp_path: Path) -> tuple[RecordingDelivery, BudgetWorld, FixedBudget]:
    """A fixed world whose reclaimer delivers to a recording delivery."""
    w = populated(fixed_world(tmp_path))
    assert w.fixed is not None
    clock = FakeClock()
    delivery = RecordingDelivery(clock, SequenceIdGenerator(clock))
    return delivery, replace(w, reclaimer=NoteBudgetReclaimer(delivery, w.fixed, w.tasks, w.mail, w.agents)), w.fixed


def test_the_amount_is_taken_from_the_budget_query_it_is_given(tmp_path: Path) -> None:
    delivery, world, fixed = recording(tmp_path)
    fixed.held[ENG] = 4  # no message anywhere says so
    msg = world.reclaimer.reclaim("ceo", "eng", 3)
    assert msg.budget == 3 and "(1 left with it)" in msg.body
    assert delivery.messages == [msg]


def test_one_note_is_delivered_and_it_is_the_one_returned(tmp_path: Path) -> None:
    delivery, world, fixed = recording(tmp_path)
    fixed.held[ENG] = 2
    msg = world.reclaimer.reclaim("ceo", "eng")
    assert delivery.messages == [msg] and msg.type == "note" and msg.wake is False


def test_a_refusal_delivers_nothing(tmp_path: Path) -> None:
    delivery, world, _ = recording(tmp_path)
    with pytest.raises(OrgError):
        world.reclaimer.reclaim("ceo", "eng")
    assert delivery.messages == []


def test_nothing_is_minted_and_nothing_is_lost(w: BudgetWorld) -> None:
    grant(w, "root", "ceo", 12)
    grant(w, "ceo", ENG, 4)
    grant(w, "ceo", "ceo/qa", 3)
    for addr in (ENG, "ceo/qa"):
        w.begin_run(addr)
        w.end_run(addr)

    def held() -> int:
        return sum(w.query.budget(a) or 0 for a in ("ceo", ENG, "ceo/qa"))

    before = held()
    w.reclaimer.reclaim("ceo", "eng", 3)
    w.reclaimer.reclaim("ceo", "qa")
    assert held() == before == 12


def test_the_runtime_is_not_the_sender_of_the_note(w: BudgetWorld) -> None:
    grant(w, "ceo", ENG, 2)
    w.begin_run(ENG)
    w.end_run(ENG)
    msg: Message = w.reclaimer.reclaim("ceo", "eng")
    assert msg.sender == ENG and [m.id for m in w.sent(ENG) if m.title.startswith("budget reclaimed")] == [msg.id]
