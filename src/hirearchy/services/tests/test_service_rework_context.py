"""``ServiceReworkContext``: the service fields a rework task inherits, over disk and over memory, and the contract suite of ``dispatch``'s port."""

from __future__ import annotations

from pathlib import Path

import pytest

from hirearchy.dispatch import ReworkContext
from hirearchy.kernel import Message
from hirearchy.services.testing import IMPLEMENTATIONS, ServicesWorld, fs_world, memory_world

# The suite that every ``ReworkContext`` passes: the same functions, run against this package's implementations.
from hirearchy.dispatch.tests.test_contract_rework_context import (  # noqa: F401  (imported to be collected here)
    test_an_ordinary_task_inherits_nothing,
    test_the_answer_for_a_task_is_the_same_every_time,
    test_the_answer_holds_only_the_service_fields,
    test_what_the_caller_does_with_the_answer_does_not_change_the_next_one,
)

from ._support import STEPS, answer, define, implementations, populated, request


@pytest.fixture(params=implementations(IMPLEMENTATIONS[ReworkContext]))
def context(request: pytest.FixtureRequest, tmp_path: Path) -> ReworkContext:
    made = request.param(tmp_path)
    assert isinstance(made, ReworkContext)
    return made


@pytest.fixture(params=[fs_world, memory_world], ids=lambda f: f.__name__)
def w(request: pytest.FixtureRequest, tmp_path: Path) -> ServicesWorld:
    return populated(request.param(tmp_path))


def test_a_rework_of_a_request_inherits_its_service_and_contract_and_the_playbook_of_now(w: ServicesWorld) -> None:
    define(w)
    first = request(w)
    answer(w, first)
    w.commands.revise_playbook("ceo", "weekly-brief", STEPS, "after the first request", [])
    w.commands.define_service("root", "ceo", "weekly-brief", budget=12)
    assert dict(w.rework.fields_for("root", first.id)) == {"service": "weekly-brief", "contract": 1, "playbook": 1}


def test_a_task_that_is_not_a_request_inherits_nothing(w: ServicesWorld) -> None:
    plain = w.d.post(Message(sender="root", to="ceo", type="task", body="plain", title="Plain", budget=2))
    assert dict(w.rework.fields_for("root", plain.id)) == {}


def test_a_task_that_is_unknown_or_was_sent_by_somebody_else_inherits_nothing(w: ServicesWorld) -> None:
    define(w)
    first = request(w)
    assert dict(w.rework.fields_for("root", "20200101T000000000001-root-0000")) == {}
    assert dict(w.rework.fields_for("ceo", first.id)) == {}


def test_a_note_is_not_a_task(w: ServicesWorld) -> None:
    note = w.d.post(Message(sender="root", to="ceo", type="note", body="n", service="weekly-brief"))
    assert dict(w.rework.fields_for("root", note.id)) == {}


def test_a_service_without_a_playbook_is_inherited_as_version_zero(w: ServicesWorld) -> None:
    define(w)
    first = request(w)
    assert dict(w.rework.fields_for("root", first.id)) == {"service": "weekly-brief", "contract": 1, "playbook": 0}


def test_the_playbook_of_an_owner_that_does_not_exist_is_version_zero(tmp_path: Path) -> None:
    w = populated(memory_world(tmp_path))
    sent = w.d.post(Message(sender="root", to="ghost", type="task", body="b", title="T", service="weekly-brief", contract=3))
    assert dict(w.rework.fields_for("root", sent.id)) == {"service": "weekly-brief", "contract": 3, "playbook": 0}
