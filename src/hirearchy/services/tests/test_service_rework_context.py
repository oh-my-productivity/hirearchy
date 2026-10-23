"""``ServiceReworkContext``: the service fields and the tier a rework task inherits, over disk and over memory, and the contract suite of ``dispatch``'s port."""

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
    test_a_tier_is_human_or_relayed,
    test_root_never_gets_a_tier,
    test_the_answer_holds_only_the_service_fields_and_the_tier,
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


# ------------------------------------------------------------------------------ the tier of the work the agent is doing in that case (P4, design 7.6)

TRACE = "20260101T000000000001-root-aaaa"


def received(w: ServicesWorld, source: str | None, trace: str | None = TRACE, **kw: object) -> Message:
    """A task of root's that the lead ``ceo`` received (a request of the service, or a rework of it), in the case ``trace``."""
    return w.d.post(Message(sender="root", to="ceo", type="task", body="b", title="T", service="weekly-brief", source=source, trace=trace, **kw))  # type: ignore[arg-type]


def worker_task(w: ServicesWorld, trace: str | None = TRACE) -> Message:
    """The lead's task to the writer: no service, no tier."""
    return w.d.post(Message(sender="ceo", to="ceo/eng", type="task", body="write", title="Write", trace=trace))


def test_a_non_service_revised_task_with_a_trace_gives_only_source(w: ServicesWorld) -> None:
    received(w, "relayed")
    task = worker_task(w)
    assert dict(w.rework.fields_for("ceo", task.id)) == {"source": "relayed"}


def test_a_revised_task_without_a_trace_gives_no_source(w: ServicesWorld) -> None:
    task = worker_task(w, trace=None)  # sent before the lead had any task in hand: the runtime found no case for it
    received(w, "human")
    assert task.trace is None and dict(w.rework.fields_for("ceo", task.id)) == {}


def test_a_received_task_with_a_final_result_is_skipped(w: ServicesWorld) -> None:
    received(w, "relayed")
    done = received(w, "human")
    task = worker_task(w)
    assert dict(w.rework.fields_for("ceo", task.id)) == {"source": "human"}  # the newest open task of that case
    answer(w, done)
    assert dict(w.rework.fields_for("ceo", task.id)) == {"source": "relayed"}


def test_a_blocked_result_is_not_final(w: ServicesWorld) -> None:
    received(w, "relayed")
    blocked = received(w, "human")
    task = worker_task(w)
    answer(w, blocked, status="blocked")
    assert dict(w.rework.fields_for("ceo", task.id)) == {"source": "human"}


def test_a_failed_result_is_final(w: ServicesWorld) -> None:
    received(w, "relayed")
    failed = received(w, "human")
    task = worker_task(w)
    answer(w, failed, status="failed")
    assert dict(w.rework.fields_for("ceo", task.id)) == {"source": "relayed"}


def test_the_tier_comes_from_the_case_of_the_revised_task_only(w: ServicesWorld) -> None:
    received(w, "human", trace="20260101T000000000002-root-bbbb")
    received(w, "relayed")
    assert dict(w.rework.fields_for("ceo", worker_task(w).id)) == {"source": "relayed"}


def test_a_task_without_a_tier_or_from_the_runtime_gives_no_source(w: ServicesWorld) -> None:
    received(w, None)  # the request itself: not stamped
    w.d.post(Message(sender="runtime", to="ceo", type="task", body="b", title="T", source="human", trace=TRACE))
    assert dict(w.rework.fields_for("ceo", worker_task(w).id)) == {}


def test_a_task_that_is_not_the_actors_gives_no_tier(w: ServicesWorld) -> None:
    received(w, "human")
    task = worker_task(w)
    assert dict(w.rework.fields_for("ceo/eng", task.id)) == {}
    assert dict(w.rework.fields_for("root", task.id)) == {}


def test_a_service_request_keeps_its_case_and_root_gets_no_tier(w: ServicesWorld) -> None:
    define(w)
    first = request(w)
    received(w, "human", trace=first.trace)
    assert dict(w.rework.fields_for("root", first.id)) == {"service": "weekly-brief", "contract": 1, "playbook": 0}


def test_a_leads_rework_of_a_service_request_keeps_the_case_and_gets_the_tier(w: ServicesWorld) -> None:
    define(w)
    sent = w.d.post(Message(sender="ceo", to="ceo/eng", type="task", body="b", title="T", service="weekly-brief", contract=1, trace=TRACE))
    received(w, "human")
    assert dict(w.rework.fields_for("ceo", sent.id)) == {"service": "weekly-brief", "contract": 1, "playbook": 0, "source": "human"}
