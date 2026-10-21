"""``MailRejectedServices``: which services of an agent the client rejected a delivery of, as its batch shows, and the tier of the verdict."""

from __future__ import annotations

from pathlib import Path

import pytest

from hirearchy.kernel import Message
from hirearchy.reflection._ports import RejectedServices
from hirearchy.reflection._sections import MailRejectedServices
from hirearchy.reflection.testing import ReflectionWorld, fs_world, memory_world

from ._support import SERVICE, ask, define, deliver, nested, populated, rate


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
    assert w.rejections.among("ceo", w.s.d.inbox("ceo")) == {SERVICE: "human"}


def test_an_accept_is_not_a_rejection(w: ReflectionWorld) -> None:
    task = ask(w)
    deliver(w, task)
    rate(w, task, "accept")
    assert w.rejections.among("ceo", w.s.d.inbox("ceo")) == {}


def test_a_batch_without_notes_rejects_nothing(w: ReflectionWorld) -> None:
    ask(w)
    assert w.rejections.among("ceo", w.s.d.inbox("ceo")) == {}


def test_a_note_to_somebody_else_is_not_ours(w: ReflectionWorld) -> None:
    task = ask(w)
    deliver(w, task)
    note = rate(w, task, "reject", "No.")
    assert w.rejections.among("ops", [note]) == {}


def test_a_note_that_answers_no_service_task_names_no_service(w: ReflectionWorld) -> None:
    stray = Message(sender="root", to="ceo", type="note", body="b", feedback="reject", reply_to="no-such-task")
    assert w.rejections.among("ceo", [stray]) == {}


def test_rejected_services_returns_the_strongest_tier_per_service(w: ReflectionWorld) -> None:
    relayed, human = ask(w, "a"), ask(w, "b")
    deliver(w, relayed)
    deliver(w, human)
    rate(w, relayed, "reject", "The assistant's reading.", source="relayed")
    assert w.rejections.among("ceo", w.s.d.inbox("ceo")) == {SERVICE: "relayed"}
    rate(w, human, "reject", "The user's words.")
    assert w.rejections.among("ceo", w.s.d.inbox("ceo")) == {SERVICE: "human"}  # human > relayed, whatever the order


def test_an_agent_clients_rejection_is_of_the_agent_tier(w: ReflectionWorld) -> None:
    result = nested(w)
    w.s.commands.feedback("ceo", result.reply_to or "", "reject", "Thin.")
    assert w.rejections.among("ceo/eng", w.s.d.inbox("ceo/eng")) == {"inner": "agent"}


def test_a_relayed_rejection_still_triggers_reflect(w: ReflectionWorld) -> None:
    task = ask(w)
    deliver(w, task, lessons="L.")
    rate(w, task, "reject", "The assistant finds it long.", source="relayed")
    assert SERVICE in w.sections.prompt_sections("ceo", w.s.d.inbox("ceo")).split("# Reflect before you start: ")[1]
