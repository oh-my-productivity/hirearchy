"""Contract of ``TraceLookup``: over the mailboxes on disk and over the in-memory ones it gives the same answers."""

from __future__ import annotations

from pathlib import Path

import pytest

from hirearchy.traces import TraceLookup
from hirearchy.traces.testing import IMPLEMENTATIONS, TraceHarness

from ._support import make, mid, put, result

@pytest.fixture(params=IMPLEMENTATIONS[TraceLookup], ids=lambda factory: factory.__name__)
def h(request: pytest.FixtureRequest, tmp_path: Path) -> TraceHarness:
    made = make(request, tmp_path)
    assert isinstance(made.lookup, TraceLookup)
    return made


# ------------------------------------------------------------------------------ trace_of


@pytest.mark.parametrize("box", ["inbox", "inflight", "read", "sent"])
def test_trace_of_finds_the_trace_in_each_of_the_four_boxes(h: TraceHarness, box: str) -> None:
    msg_id = put(h, "ceo", box, 1, trace="T1")
    assert h.lookup.trace_of("ceo", msg_id) == "T1"


def test_trace_of_looks_in_the_boxes_of_that_agent_only(h: TraceHarness) -> None:
    msg_id = put(h, "ceo", "inbox", 1, trace="T1")
    assert h.lookup.trace_of("ceo/eng", msg_id) is None and h.lookup.trace_of("root", msg_id) is None


def test_trace_of_the_boxes_of_root_are_in_the_organization_itself(h: TraceHarness) -> None:
    msg_id = put(h, "root", "sent", 1, trace="T1", sender="root", to="ceo")
    assert h.lookup.trace_of("root", msg_id) == "T1" and h.lookup.trace_of(" /root/ ", msg_id) == "T1"


def test_trace_of_reads_an_address_that_is_spelled_differently(h: TraceHarness) -> None:
    msg_id = put(h, "ceo/eng", "read", 1, trace="T1")
    assert h.lookup.trace_of(" /ceo/eng/ ", msg_id) == "T1"


def test_trace_of_a_message_without_a_trace_is_none(h: TraceHarness) -> None:
    msg_id = put(h, "ceo", "inbox", 1)
    assert h.lookup.trace_of("ceo", msg_id) is None


def test_trace_of_a_message_that_is_not_there_is_none(h: TraceHarness) -> None:
    assert h.lookup.trace_of("ceo", mid(7)) is None and h.lookup.trace_of("nobody", mid(7)) is None


def test_trace_of_a_file_that_does_not_parse_is_none(h: TraceHarness) -> None:
    msg_id = mid(1)
    h.mail.put(f"ceo/inbox/{msg_id}.md", "---\nfrom: [unclosed\nto: ceo\n---\nbody\n")
    assert h.lookup.trace_of("ceo", msg_id) is None


@pytest.mark.parametrize("bad", ["", None, "../inbox/X", "a/b", "a b", "..", "x\n"])
def test_trace_of_an_id_that_is_not_a_plain_file_name_is_none(h: TraceHarness, bad: str | None) -> None:
    msg_id = put(h, "ceo/eng", "inbox", 1, trace="T1")
    assert h.lookup.trace_of("ceo/eng", bad) is None
    assert h.lookup.trace_of("ceo/eng", f"../inbox/{msg_id}") is None  # would resolve to a real file without the check


def test_trace_of_the_first_box_that_has_the_file_decides(h: TraceHarness) -> None:
    msg_id = mid(1)
    put(h, "ceo", "inbox", 1, trace="IN")
    put(h, "ceo", "sent", 1, trace="OUT")
    assert h.lookup.trace_of("ceo", msg_id) == "IN"


# ------------------------------------------------------------------------------ open_task_traces


def test_open_task_traces_are_those_of_the_tasks_without_a_result(h: TraceHarness) -> None:
    t1 = put(h, "ceo", "inbox", 1, trace="A")
    put(h, "ceo", "read", 2, trace="B")
    put(h, "ceo", "inflight", 3, trace="C")
    result(h, "ceo", 4, t1)
    assert h.lookup.open_task_traces("ceo") == ["B", "C"]


def test_open_task_traces_are_sorted_by_task_id_and_keep_a_task_without_a_trace_as_none(h: TraceHarness) -> None:
    put(h, "ceo", "read", 3, trace="C")
    put(h, "ceo", "inbox", 1)
    put(h, "ceo", "inbox", 2, trace="B")
    assert h.lookup.open_task_traces("ceo") == [None, "B", "C"]


def test_a_blocked_result_leaves_the_task_open_and_a_later_final_one_closes_it(h: TraceHarness) -> None:
    task = put(h, "ceo", "read", 1, trace="A")
    result(h, "ceo", 2, task, "blocked")
    assert h.lookup.open_task_traces("ceo") == ["A"]
    result(h, "ceo", 3, task, "done")
    assert h.lookup.open_task_traces("ceo") == []


def test_only_tasks_count(h: TraceHarness) -> None:
    put(h, "ceo", "inbox", 1, trace="A", kind="note")
    put(h, "ceo", "inbox", 2, trace="A", kind="result", reply_to="x", status="done")
    assert h.lookup.open_task_traces("ceo") == []


def test_only_a_result_the_agent_sent_closes_a_task(h: TraceHarness) -> None:
    task = put(h, "ceo", "inbox", 1, trace="A")
    put(h, "ceo", "inbox", 2, kind="result", reply_to=task, status="done", sender="ceo/eng")
    assert h.lookup.open_task_traces("ceo") == ["A"]


def test_open_task_traces_of_root_the_runtime_and_a_stranger_are_empty(h: TraceHarness) -> None:
    put(h, "root", "inbox", 1, trace="A", sender="ceo", to="root")
    h.mail.put(f"runtime/inbox/{mid(2)}.md", "x")
    mail_only = put(h, "ghost", "inbox", 3, trace="A")  # a mailbox without an agent
    assert mail_only and h.lookup.open_task_traces("root") == [] and h.lookup.open_task_traces("runtime") == []
    assert h.lookup.open_task_traces("ghost") == []


def test_open_task_traces_reads_an_address_that_is_spelled_differently(h: TraceHarness) -> None:
    put(h, "ceo/eng", "inbox", 1, trace="A")
    assert h.lookup.open_task_traces(" /ceo/eng/ ") == ["A"]


# ------------------------------------------------------------------------------ context_trace


def test_context_trace_open_tasks_that_share_one_trace(h: TraceHarness) -> None:
    put(h, "ceo", "inbox", 1, trace="A")
    put(h, "ceo", "read", 2, trace="A")
    assert h.lookup.context_trace("ceo") == ("A", "open-task", [])


def test_context_trace_an_open_task_without_a_trace_defeats_the_open_task_rule(h: TraceHarness) -> None:
    put(h, "ceo", "inbox", 1)
    put(h, "ceo", "read", 2, trace="A")
    assert h.lookup.context_trace("ceo") == (None, "ambiguous", ["A"])


def test_context_trace_the_one_trace_of_the_batch_when_the_open_tasks_differ(h: TraceHarness) -> None:
    put(h, "ceo", "read", 1, trace="A")
    put(h, "ceo", "inflight", 2, trace="B")
    assert h.lookup.context_trace("ceo") == ("B", "batch", [])


def test_context_trace_the_batch_decides_when_an_open_task_has_no_trace(h: TraceHarness) -> None:
    put(h, "ceo", "read", 1)
    put(h, "ceo", "inflight", 2, trace="B", kind="note")
    assert h.lookup.context_trace("ceo") == ("B", "batch", [])


def test_context_trace_a_batch_of_several_traces_is_ambiguous_with_every_candidate_sorted(h: TraceHarness) -> None:
    put(h, "ceo", "inflight", 1, trace="B")
    put(h, "ceo", "inflight", 2, trace="A")
    put(h, "ceo", "read", 3, trace="C")
    put(h, "ceo", "inflight", 4, kind="note")  # no trace: not a candidate
    assert h.lookup.context_trace("ceo") == (None, "ambiguous", ["A", "B", "C"])


def test_context_trace_without_anything_is_ambiguous_with_no_candidates(h: TraceHarness) -> None:
    assert h.lookup.context_trace("ceo") == (None, "ambiguous", [])


def test_context_trace_of_root_the_runtime_and_a_stranger_has_no_context(h: TraceHarness) -> None:
    put(h, "root", "inflight", 1, trace="A", sender="ceo", to="root")
    put(h, "ghost", "inflight", 2, trace="A")
    for addr in ("root", "runtime", "ghost"):
        assert h.lookup.context_trace(addr) == (None, "ambiguous", [])


def test_a_closed_task_is_not_context_but_its_trace_stays_a_candidate_through_the_batch(h: TraceHarness) -> None:
    task = put(h, "ceo", "inflight", 1, trace="A")
    result(h, "ceo", 2, task)
    assert h.lookup.open_task_traces("ceo") == []
    assert h.lookup.context_trace("ceo") == ("A", "batch", [])
