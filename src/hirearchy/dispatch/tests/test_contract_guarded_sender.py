"""Contract of ``GuardedSender``: the sender the ``Org`` facade hands out. A ``MessageSender`` that refuses the shapes only the rule classes may send for root
(a service task, a rework) and delivers every other message exactly as the sender it guards would.

One implementation (``GuardedRootSender``), over any ``MessageSender``: it runs here over the recording fake and over the checking sender of a world
(``PURE`` in ``testing.py``: the guard has no fake of its own). The rule itself, and its texts: ``test_root_send``."""

from __future__ import annotations

from pathlib import Path

import pytest

from hirearchy.dispatch import GuardedSender, MessageSender
from hirearchy.dispatch._guarded import GuardedRootSender
from hirearchy.dispatch.testing import DispatchWorld, fs_world, memory_world, recording_world
from hirearchy.kernel import OrgError

from ._support import populated


@pytest.fixture(params=[fs_world, memory_world, recording_world], ids=lambda f: f.__name__)
def w(request: pytest.FixtureRequest, tmp_path: Path) -> DispatchWorld:
    return populated(request.param(tmp_path))


def test_it_is_a_message_sender(w: DispatchWorld) -> None:
    guard = GuardedRootSender(w.sender)
    assert isinstance(guard, GuardedSender) and isinstance(guard, MessageSender)


def test_a_message_it_does_not_refuse_is_delivered_like_the_inner_sender_would(w: DispatchWorld) -> None:
    guard = GuardedRootSender(w.sender)
    note = guard.send("root", "ceo", "hello", title="Hi", budget=3)
    task = guard.send("root", "ceo", "one-off work", type="task", title="Work")
    assert [m.id for m in w.inbox("ceo")] == [note.id, task.id] and (note.budget, task.type) == (3, "task")


def test_a_refused_message_is_not_delivered(w: DispatchWorld) -> None:
    guard = GuardedRootSender(w.sender)
    with pytest.raises(OrgError, match="^refused: a root task for a service, or a rework"):
        guard.send("root", "ceo", "a request", type="task", service="weekly-brief")
    with pytest.raises(OrgError, match="^refused: a root task for a service, or a rework"):
        guard.send("root", "ceo", "again", type="task", revises="20260101T000000000001-root-aaaa")
    assert w.inbox("ceo") == []


@pytest.mark.parametrize("make", [fs_world, memory_world], ids=lambda f: f.__name__)
def test_the_refusals_of_the_inner_sender_still_apply(make, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    with pytest.raises(OrgError, match="no such agent: ghost"):
        GuardedRootSender(populated(make(tmp_path)).sender).send("root", "ghost", "hello")
