"""The rules of a trace that are plain functions: the window of runs of a root task, the summary of tool calls, the time spent waiting for the human.

The window is the one ``progress`` counts runs by: from the creation of the task to its final result (or now), cut where root's next task to the
same assignee begins; the tests pin it here, and ``app/tests/test_trace_progress.py`` proves that the trace and ``progress`` count the same runs."""

from __future__ import annotations

from datetime import datetime
from typing import cast

from hirearchy.kernel import JsonObject, stamp_of
from hirearchy.observability._messages import Msg
from hirearchy.observability._trace import calls_summary, in_window, run_window, user_wait

from ._support import stamp



def task(n: int, to: str = "ceo", **fields: object) -> Msg:
    mid = f"{stamp(n):%Y%m%dT%H%M%S%f}-root-{n:04x}"
    values: dict[str, object] = {"id": mid, "sender": "root", "to": to, "type": "task", "title": "", "status": None, "budget": 0, "reply_to": None,
                                 "revises": None, "service": None, "feedback": None, "wake": True, "trace": None, "t": stamp_of(mid), **fields}
    return Msg(**values)  # type: ignore[arg-type]


def result(n: int, status: str, of: Msg, **fields: object) -> Msg:
    return task(n, "root", sender="ceo", type="result", status=status, reply_to=of.id, **fields)


def test_the_window_runs_from_the_task_to_its_final_result() -> None:
    t = task(10)
    assert run_window(t, None, [t]) == (t.id[:21], None)
    done = result(50, "done", t)
    assert run_window(t, done, [t]) == (t.id[:21], done.id[:21])
    assert run_window(t, result(50, "failed", t), [t])[1] is not None


def test_a_blocked_result_does_not_end_the_window() -> None:
    t = task(10)
    assert run_window(t, result(50, "blocked", t), [t]) == (t.id[:21], None)


def test_the_next_task_to_the_same_assignee_cuts_the_window() -> None:
    first, other, second = task(10), task(20, "ops"), task(30)
    assert run_window(first, None, [first, other, second]) == (first.id[:21], second.id[:21])
    done = result(25, "done", first)
    assert run_window(first, done, [first, second])[1] == done.id[:21]  # its own end comes first
    late = result(60, "done", first)
    assert run_window(first, late, [first, second])[1] == second.id[:21]  # the next task comes first


def test_a_name_is_inside_a_window_by_its_first_21_characters() -> None:
    a, b = f"{stamp(10):%Y%m%dT%H%M%S%f}", f"{stamp(20):%Y%m%dT%H%M%S%f}"
    assert in_window(a + ".log", a, b) and in_window(b + "-x", a, b) and not in_window(f"{stamp(21):%Y%m%dT%H%M%S%f}", a, b)
    assert in_window(f"{stamp(900):%Y%m%dT%H%M%S%f}", a, None) and not in_window(f"{stamp(5):%Y%m%dT%H%M%S%f}", a, None)


def test_tool_calls_are_summed_by_tool_and_the_refused_ones_are_listed() -> None:
    calls: list[JsonObject] = [
        {"tool": "read", "ok": True}, {"tool": "delegate", "ok": False, "ts": "T", "error": "x  y\n" * 400, "error_type": "OrgError", "actor": "ceo"},
        {"tool": "read", "ok": True}, {"tool": "write", "ok": None},
    ]
    summary = calls_summary(calls)
    assert summary["total"] == 4 and summary["by_tool"] == {"read": 2, "delegate": 1, "write": 1}
    (refused,) = cast("list[JsonObject]", summary["refused"])
    assert refused["tool"] == "delegate" and refused["t"] == "T" and refused["actor"] == "ceo" and len(str(refused["error"])) == 500


def tool_call(ts: float, actor: str, tool: str, trace: str) -> tuple[datetime, JsonObject]:
    return stamp(ts), {"kind": "tool.call", "actor": actor, "tool": tool, "trace": trace}


def test_the_human_is_waited_for_from_what_needs_them_to_their_next_action() -> None:
    t = task(0)
    blocked = Msg(**{**result(20, "blocked", t).__dict__, "to": "root"})
    note = task(40, "root", sender="ceo", type="note")
    reply = task(50, "ceo", type="note")
    assert user_wait([t, blocked, reply], [], "T", stamp(100)) == 30000.0
    assert user_wait([t, blocked, note, reply], [], "T", stamp(100)) == 30000.0  # two asks, one answer: the spans overlap
    assert user_wait([t, blocked], [], "T", stamp(100)) == 80000.0  # not answered: until the end of the request


def test_a_state_changing_tool_call_of_root_is_an_action_and_reading_is_not() -> None:
    t = task(0)
    blocked = Msg(**{**result(20, "blocked", t).__dict__, "to": "root"})
    events = [tool_call(30, "root", "progress", "T"), tool_call(35, "root", "observe", "T"), tool_call(60, "root", "delegate", "T"),
              tool_call(45, "root", "delegate", "OTHER"), tool_call(41, "ceo", "delegate", "T")]
    assert user_wait([t, blocked], events, "T", stamp(100)) == 40000.0


def test_what_does_not_need_the_human_is_not_waited_for() -> None:
    t = task(0)
    done = Msg(**{**result(20, "done", t).__dict__, "to": "root"})
    silent = Msg(**{**result(21, "blocked", t).__dict__, "to": "root", "wake": False})
    to_agent = Msg(**{**result(22, "blocked", t).__dict__, "to": "ceo"})
    assert user_wait([t, done, silent, to_agent], [], "T", stamp(100)) == 0
