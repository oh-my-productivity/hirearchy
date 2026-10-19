"""``MailRejectedServices``: which services of an agent the client rejected a delivery of, as its batch shows."""

from __future__ import annotations

from pathlib import Path

import pytest

from orgmcp.kernel import Message
from orgmcp.reflection._ports import RejectedServices
from orgmcp.reflection._sections import MailRejectedServices
from orgmcp.reflection.testing import ReflectionWorld, fs_world, memory_world

from ._support import SERVICE, ask, define, deliver, populated, rate


@pytest.fixture(params=[fs_world, memory_world], ids=lambda f: f.__name__)
def w(request: pytest.FixtureRequest, tmp_path: Path) -> ReflectionWorld:
    world = populated(request.param(tmp_path))
    define(world)
    return world


def test_it_is_a_rejected_services(w: ReflectionWorld) -> None:
    assert isinstance(w.rejections, RejectedServices) and isinstance(w.rejections, MailRejectedServices)


def test_a_reject_note_in_the_batch_names_the_service_of_the_task_it_answers(w: ReflectionWorld) -> None:
    task = ask(w)
    deliver(w, task)
    rate(w, task, "reject", "No.")
    assert w.rejections.among("ceo", w.s.d.inbox("ceo")) == {SERVICE}


def test_an_accept_is_not_a_rejection(w: ReflectionWorld) -> None:
    task = ask(w)
    deliver(w, task)
    rate(w, task, "accept")
    assert w.rejections.among("ceo", w.s.d.inbox("ceo")) == set()


def test_a_batch_without_notes_rejects_nothing(w: ReflectionWorld) -> None:
    ask(w)
    assert w.rejections.among("ceo", w.s.d.inbox("ceo")) == set()


def test_a_note_to_somebody_else_is_not_ours(w: ReflectionWorld) -> None:
    task = ask(w)
    deliver(w, task)
    note = rate(w, task, "reject", "No.")
    assert w.rejections.among("ops", [note]) == set()


def test_a_note_that_answers_no_service_task_names_no_service(w: ReflectionWorld) -> None:
    stray = Message(sender="root", to="ceo", type="note", body="b", feedback="reject", reply_to="no-such-task")
    assert w.rejections.among("ceo", [stray]) == set()
