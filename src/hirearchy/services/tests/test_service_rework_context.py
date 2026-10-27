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
    test_root_never_gets_a_work_tier,
    test_a_work_tier_is_none_human_or_relayed_and_the_same_every_time,
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
    w.commands.revise_playbook("ceo", "weekly-brief", "first", "after the first request", [], text=STEPS)
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


# ------------------------------------------------------------------------------ a revised delegation with no trace: the tier through the run's batch (F-E5-7, D-E5-5)

BATCH = "20260101T000000000002-root-bbbb"


def human_task(w: ServicesWorld, trace: str, **kw: object) -> Message:
    """A human-tier task of root's that the lead ``ceo`` receives (it stays in the inbox until the lead's next run begins)."""
    return received(w, "human", trace=trace, **kw)


def run_of_lead(w: ServicesWorld) -> None:
    """The lead's run begins (what is in its inbox is now its batch, in ``inflight``)."""
    w.d.begin_run("ceo")


def delegation_with_no_trace(w: ServicesWorld) -> Message:
    """E5 s3: the lead holds memo 1's blocked task (case A, read in an earlier run) and the human task of memo 2 (case B); its delegation is stamped by
    neither the open-task rule (two cases) nor the batch rule (nothing in flight), so it carries no trace. The lead's next run is not begun."""
    blocked = human_task(w, TRACE)
    answer(w, blocked, status="blocked")
    run_of_lead(w)
    w.d.end_run("ceo")
    human_task(w, BATCH)
    task = worker_task(w, trace=None)
    assert task.trace is None
    return task


def test_a_delegation_with_no_trace_gets_the_tier_of_the_case_of_its_batch(w: ServicesWorld) -> None:
    """E5 s3 ``0a56``: the revising run's batch is root's human rework of memo 2 (case B), the one open task of the lead in that case."""
    task = delegation_with_no_trace(w)
    run_of_lead(w)
    assert dict(w.rework.fields_for("ceo", task.id)) == {"source": "human"}


def test_a_delegation_with_no_trace_gets_the_tier_when_the_batch_holds_only_a_result_of_the_case(w: ServicesWorld) -> None:
    """E5 s3 ``16f9``: the batch is the writer's result to the delegation (a result, not a task); the stamper's batch rule takes its trace too."""
    task = delegation_with_no_trace(w)
    run_of_lead(w)
    w.d.end_run("ceo")
    w.d.post(Message(sender="ceo/eng", to="ceo", type="result", status="done", reply_to=task.id, body="b", title="Result", trace=BATCH))
    run_of_lead(w)
    assert dict(w.rework.fields_for("ceo", task.id)) == {"source": "human"}


def test_a_delegation_with_no_trace_gets_no_tier_when_the_batch_holds_two_cases(w: ServicesWorld) -> None:
    task = delegation_with_no_trace(w)
    human_task(w, TRACE)  # a second human task of case A arrives: the next batch holds both cases
    run_of_lead(w)
    assert dict(w.rework.fields_for("ceo", task.id)) == {}


def test_a_delegation_with_no_trace_gets_no_tier_without_a_batch_or_when_it_has_no_trace(w: ServicesWorld) -> None:
    task = delegation_with_no_trace(w)
    run_of_lead(w)
    w.d.end_run("ceo")
    assert dict(w.rework.fields_for("ceo", task.id)) == {}  # no batch at all
    w.d.post(Message(sender="ceo/eng", to="ceo", type="note", body="b", title="N"))  # a message with no trace
    run_of_lead(w)
    assert dict(w.rework.fields_for("ceo", task.id)) == {}


def test_a_revised_task_with_a_trace_keeps_its_own_case_whatever_the_batch_holds(w: ServicesWorld) -> None:
    received(w, "relayed")  # the lead's open task of case A
    task = worker_task(w)  # sent with the trace of case A
    human_task(w, BATCH)
    run_of_lead(w)  # the batch holds only case B
    assert task.trace == TRACE and dict(w.rework.fields_for("ceo", task.id)) == {"source": "relayed"}


# ------------------------------------------------------------------------------ the tier of the work an agent does now, for a delegation without ``revises`` (F-E6-7, D-E6-5)


def test_the_lead_holding_roots_open_human_rework_in_one_trace_works_at_the_human_tier(w: ServicesWorld) -> None:
    received(w, "human")
    assert w.rework.work_tier("ceo") == "human"


def test_the_lead_holding_roots_open_relayed_rework_works_at_the_relayed_tier(w: ServicesWorld) -> None:
    received(w, "relayed")
    assert w.rework.work_tier("ceo") == "relayed"


def test_the_newest_open_task_of_the_one_trace_gives_the_work_tier(w: ServicesWorld) -> None:
    received(w, "relayed")
    done = received(w, "human")
    assert w.rework.work_tier("ceo") == "human"
    answer(w, done)
    assert w.rework.work_tier("ceo") == "relayed"


def test_a_closed_task_gives_no_work_tier(w: ServicesWorld) -> None:
    answer(w, received(w, "human"))
    assert w.rework.work_tier("ceo") is None


def test_a_blocked_task_is_still_open_for_the_work_tier(w: ServicesWorld) -> None:
    answer(w, received(w, "human"), status="blocked")
    assert w.rework.work_tier("ceo") == "human"


def test_an_accepted_blocked_task_is_no_longer_open_for_the_work_tier(w: ServicesWorld) -> None:
    """D-E7-2 F-E7-7 (E7 s3): the user's accept after the block moves its assigner past the human task (``mail.still_open``), so the one open trace is
    the fresh relayed task's and the work tier is its tier; without the accept the lead holds two traces, no batch, and no tier (as before)."""
    blocked = human_task(w, TRACE)
    answer(w, blocked, status="blocked")
    received(w, "relayed", trace=BATCH)
    assert w.rework.work_tier("ceo") is None  # two open traces, no batch
    w.d.post(Message(sender="root", to="ceo", type="note", body="accepted", title="Accept", feedback="accept", reply_to=blocked.id, source="human"))
    assert w.rework.work_tier("ceo") == "relayed"


def test_root_and_an_agent_without_a_task_have_no_work_tier(w: ServicesWorld) -> None:
    received(w, "human")
    assert w.rework.work_tier("root") is None and w.rework.work_tier("ceo/eng") is None


def test_an_open_task_without_a_tier_gives_no_work_tier(w: ServicesWorld) -> None:
    received(w, None)
    assert w.rework.work_tier("ceo") is None


def test_two_open_traces_and_a_batch_of_one_give_the_tier_of_the_batch(w: ServicesWorld) -> None:
    """The stamper's rules: the open tasks name two traces, so the one trace of the run's batch is the case."""
    received(w, "relayed", trace=TRACE)
    run_of_lead(w)  # the first task is read in an earlier run and stays open
    w.d.end_run("ceo")
    human_task(w, BATCH)
    run_of_lead(w)  # the batch holds only the second task
    assert w.rework.work_tier("ceo") == "human"


def test_two_open_traces_and_no_batch_give_no_work_tier(w: ServicesWorld) -> None:
    received(w, "relayed", trace=TRACE)
    human_task(w, BATCH)
    assert w.rework.work_tier("ceo") is None


def test_an_open_task_without_a_trace_leaves_the_case_to_the_batch(w: ServicesWorld) -> None:
    """``open_task_traces`` lists a missing trace, and the stamper then takes no open-task case: the batch decides."""
    received(w, "relayed", trace=None)
    run_of_lead(w)
    w.d.end_run("ceo")
    human_task(w, BATCH)
    run_of_lead(w)
    assert w.rework.work_tier("ceo") == "human"
