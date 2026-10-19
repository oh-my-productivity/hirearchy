"""``MessageTraceDeriver``: the trace of every message, as recorded in its file, else derived from the files with the rules the runtime applies
at send time (best effort): ``new``, ``link``, ``open-task``, ``batch``, else unknown."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from orgmcp.kernel import stamp_of
from orgmcp.observability._derive import LogTraceDerivers, MessageTraceDeriver
from orgmcp.observability._messages import Msg
from orgmcp.observability._ports import TraceDeriver, TraceDerivers
from orgmcp.runs.testing import MemoryRuns

from ._support import RED

pytestmark = RED

EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)


def msg(mid: str, sender: str, to: str, kind: str = "task", **fields: object) -> Msg:
    values: dict[str, object] = {
        "id": mid, "sender": sender, "to": to, "type": kind, "title": "", "status": None, "budget": 0, "reply_to": None, "revises": None,
        "service": None, "feedback": None, "wake": True, "trace": None, "t": stamp_of(mid) or EPOCH, **fields,
    }
    return Msg(**values)  # type: ignore[arg-type]


def at(n: int, who: str = "root") -> str:
    """An id ``n`` seconds after 10:00:00."""
    return f"20261018T1000{n:02d}000000-{who}-0001"


def stem(n: int) -> str:
    return f"20261018T1000{n:02d}000000"


def deriver(msgs: list[Msg], runs: MemoryRuns | None = None, batches: dict[str, list[str]] | None = None) -> TraceDeriver:
    made = MessageTraceDeriver({m.id: m for m in msgs}, batches, runs or MemoryRuns())
    assert isinstance(made, TraceDeriver)
    return made


def test_a_trace_in_the_file_is_taken_as_recorded() -> None:
    assert deriver([msg(at(1), "root", "ceo", trace="T9")]).of(at(1)) == ("T9", "recorded")


def test_root_starts_a_request_with_a_task_that_revises_nothing() -> None:
    d = deriver([msg(at(1), "root", "ceo")])
    assert d.of(at(1)) == (at(1), "derived:new")


def test_a_message_that_is_not_there_has_no_trace() -> None:
    assert deriver([]).of("nope") == (None, "unknown")


def test_a_reply_or_a_rework_belongs_to_the_request_of_the_message_it_refers_to() -> None:
    task, sub = msg(at(1), "root", "ceo"), msg(at(2, "ceo"), "ceo", "ceo/eng", reply_to=at(1))
    rework = msg(at(3), "root", "ceo", revises=at(1))
    note = msg(at(4, "ceo"), "ceo", "root", "note", reply_to="gone", revises=at(1))
    d = deriver([task, sub, rework, note])
    assert [d.of(m.id) for m in (sub, rework, note)] == [(at(1), "derived:link")] * 3


def test_a_reference_to_a_message_without_a_trace_is_not_a_link() -> None:
    a = msg(at(1, "ceo"), "ceo", "root", "note")
    b = msg(at(2, "ceo"), "ceo", "root", "note", reply_to=at(1))
    assert deriver([a, b]).of(at(2)) == (None, "unknown")


def test_references_that_point_at_each_other_end_in_unknown() -> None:
    a = msg(at(1, "ceo"), "ceo", "root", "note", reply_to=at(2, "ceo"))
    b = msg(at(2, "ceo"), "ceo", "root", "note", reply_to=at(1, "ceo"))
    d = deriver([a, b])
    assert d.of(a.id) == (None, "unknown") and d.of(b.id) == (None, "unknown")


def test_the_open_tasks_of_the_sender_decide_when_they_all_share_one_request() -> None:
    t1, t2 = msg(at(1), "root", "ceo"), msg(at(2), "root", "ceo")
    sent = msg(at(5, "ceo"), "ceo", "root", "note")
    assert deriver([t1, sent]).of(sent.id) == (t1.id, "derived:open-task")
    assert deriver([t1, t2, sent]).of(sent.id)[1] != "derived:open-task"  # two requests are open: ambiguous


def test_a_task_that_got_its_final_result_before_the_message_is_not_open() -> None:
    t1, t2 = msg(at(1), "root", "ceo"), msg(at(2), "root", "ceo")
    done = msg(at(3, "ceo"), "ceo", "root", "result", status="done", reply_to=t1.id)
    sent = msg(at(5, "ceo"), "ceo", "root", "note")
    assert deriver([t1, t2, done, sent]).of(sent.id) == (t2.id, "derived:open-task")


def test_a_blocked_result_does_not_close_a_task_and_a_result_after_the_message_does_not_either() -> None:
    t1, t2 = msg(at(1), "root", "ceo"), msg(at(2), "root", "ceo")
    blocked = msg(at(3, "ceo"), "ceo", "root", "result", status="blocked", reply_to=t1.id)
    sent = msg(at(5, "ceo"), "ceo", "root", "note")
    late = msg(at(8, "ceo"), "ceo", "root", "result", status="failed", reply_to=t2.id)
    assert deriver([t1, t2, blocked, late, sent]).of(sent.id)[1] != "derived:open-task"  # t1 and t2 are both open when it was sent


def test_the_batch_of_the_run_decides_when_it_has_one_request() -> None:
    runs = MemoryRuns()
    runs.put_log("ceo", f"{stem(30)}.log", "")
    old = msg(at(1, "gone"), "gone", "ceo", "note", trace="T1")
    sent = msg(at(40, "ceo"), "ceo", "root", "note")
    d = deriver([old, sent], runs, {f"ceo@{stem(30)}": [old.id]})
    assert d.of(sent.id) == ("T1", "derived:batch")


def test_without_run_events_the_batch_is_what_arrived_between_the_previous_run_and_this_one() -> None:
    runs = MemoryRuns()
    for n in (10, 30):
        runs.put_log("ceo", f"{stem(n)}.log", "")
    before = msg(at(5, "gone"), "gone", "ceo", "note", trace="T0")  # before the previous run: not in this batch
    arrived = msg(at(20, "gone"), "gone", "ceo", "note", trace="T1")
    after = msg(at(35, "gone"), "gone", "ceo", "note", trace="T2")  # after this run started: not in it
    sent = msg(at(40, "ceo"), "ceo", "root", "note")
    assert deriver([before, arrived, after, sent], runs).of(sent.id) == ("T1", "derived:batch")


def test_the_first_run_takes_everything_that_arrived_before_it() -> None:
    runs = MemoryRuns()
    runs.put_log("ceo", f"{stem(30)}.log", "")
    a, b = msg(at(5, "gone"), "gone", "ceo", "note", trace="T0"), msg(at(20, "gone"), "gone", "ceo", "note", trace="T1")
    sent = msg(at(40, "ceo"), "ceo", "root", "note")
    assert deriver([a, b, sent], runs).of(sent.id) == (None, "unknown")  # two requests in the batch


def test_a_message_before_any_run_has_no_batch_and_root_and_the_runtime_never_have_one() -> None:
    runs = MemoryRuns()
    runs.put_log("ceo", f"{stem(30)}.log", "")
    early = msg(at(5, "ceo"), "ceo", "root", "note")
    arrived = msg(at(2, "gone"), "gone", "ceo", "note", trace="T1")
    from_runtime = msg(at(40, "runtime"), "runtime", "ceo", "note")
    from_root = msg(at(41), "root", "ceo", "note")
    d = deriver([early, arrived, from_runtime, from_root], runs, {f"ceo@{stem(30)}": [arrived.id]})
    assert [d.of(m.id) for m in (early, from_runtime, from_root)] == [(None, "unknown")] * 3


def test_the_message_itself_is_not_part_of_its_batch() -> None:
    runs = MemoryRuns()
    runs.put_log("ceo", f"{stem(30)}.log", "")
    mine = msg(at(40, "ceo"), "ceo", "root", "note", trace=None)
    assert deriver([mine], runs, {f"ceo@{stem(30)}": [mine.id]}).of(mine.id) == (None, "unknown")


def test_the_start_of_a_run_is_read_from_the_file_name_with_its_suffix() -> None:
    """A log whose stem is shorter than a timestamp has no start for the batch rule (the name is cut at 21 characters with ``.log`` in it)."""
    runs = MemoryRuns()
    runs.put_log("ceo", "20261018T1000301.log", "")  # a stem of 16 characters: the time would be readable from the stem alone
    old = msg(at(1, "gone"), "gone", "ceo", "note", trace="T1")
    sent = msg(at(40, "ceo"), "ceo", "root", "note")
    assert deriver([old, sent], runs).of(sent.id) == (None, "unknown")


def test_logs_that_are_hidden_or_not_logs_are_not_runs() -> None:
    runs = MemoryRuns()
    runs.put_log("ceo", f".{stem(30)}.log", "")
    runs.put_log("ceo", f"{stem(30)}.txt", "")
    old = msg(at(1, "gone"), "gone", "ceo", "note", trace="T1")
    sent = msg(at(40, "ceo"), "ceo", "root", "note")
    assert deriver([old, sent], runs).of(sent.id) == (None, "unknown")


def test_an_answer_is_remembered() -> None:
    task = msg(at(1), "root", "ceo")
    d = deriver([task])
    assert d.of(task.id) is d.of(task.id)


def test_the_derivers_make_one_over_the_messages_and_batches_they_are_given(tmp_path: Path) -> None:
    derivers = LogTraceDerivers(MemoryRuns())
    assert isinstance(derivers, TraceDerivers)
    task = msg(at(1), "root", "ceo")
    assert derivers.derive({task.id: task}).of(task.id) == (task.id, "derived:new")
    assert derivers.derive({task.id: task}, {}).of(task.id) == (task.id, "derived:new")


@pytest.mark.parametrize("sender", ["root", "runtime"])
def test_it_is_a_trace_deriver_for_every_sender(sender: str) -> None:
    assert deriver([msg(at(1), sender, "ceo", "note")]).of(at(1))[0] is None
