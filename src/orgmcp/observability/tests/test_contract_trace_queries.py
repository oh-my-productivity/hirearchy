"""Contract of ``TraceQueries``: one request as a tree of messages, runs, tool calls and refusals, with totals; over files on disk and in memory.

The story is a root task to ``ceo`` (6 runs) that ``ceo`` splits to ``ceo/eng`` and reports as done: three runs, one refused call, 87 s of run time.
Timeline in seconds: task 0, ceo runs 3..45, delegation 20, eng runs 70..100, its result 95, ceo runs 115..130, final result 125."""

from __future__ import annotations

from pathlib import Path

import pytest

from orgmcp.kernel import OrgError
from orgmcp.observability import TraceQueries
from orgmcp.observability.testing import IMPLEMENTATIONS, ObservabilityWorld

from . import _support
from ._support import RED, items, request, stamp, table

pytestmark = RED

NOW = stamp(200)


@pytest.fixture(params=_support.implementations(IMPLEMENTATIONS[TraceQueries]))
def w(request: pytest.FixtureRequest, tmp_path: Path) -> ObservabilityWorld:
    made: ObservabilityWorld = request.param(tmp_path)
    assert isinstance(made.traces, TraceQueries)
    return made


def runs_of(tr: dict[str, object]) -> list[dict[str, object]]:
    return [i for i in items(tr) if i["kind"] == "run"]


def test_every_message_run_call_and_refusal_of_the_request_is_in_the_tree_in_time_order(w: ObservabilityWorld) -> None:
    ids = request(w)
    tr = w.traces.trace(ids["task"], now=NOW)
    assert [i["id"] for i in items(tr) if i["kind"] == "message"] == [ids["task"], ids["sub"], ids["res_eng"], ids["res"]]
    assert [i["run"] for i in runs_of(tr)] == [ids["run1"], ids["run2"], ids["run3"]]
    rel = [i["rel_ms"] for i in items(tr)]
    assert rel == sorted(rel)  # type: ignore[type-var]
    first = runs_of(tr)[0]
    assert first["outcome"] == "ok" and first["source"] == "events" and first["duration_ms"] == 42000.0
    assert table(first, "tool_calls")["total"] == 3 and table(first, "tool_calls")["by_tool"] == {"delegate": 2, "inbox": 1}
    (refused,) = items(table(first, "tool_calls"), "refused")
    assert refused["tool"] == "delegate" and str(refused["error"]).startswith("not enough budget")


def test_the_header_and_the_totals(w: ObservabilityWorld) -> None:
    ids = request(w)
    tr = w.traces.trace(ids["task"], now=NOW)
    assert (tr["task"], tr["title"], tr["assignee"], tr["state"], tr["partial"]) == (ids["task"], "Ship it", "ceo", "done", False)
    assert tr["team"] == ["ceo", "ceo/eng"] and tr["notes"] == []
    assert tr["start"] == stamp(0).isoformat() and tr["end"] == stamp(125).isoformat()
    totals = table(tr, "totals")
    assert (totals["runs"], totals["run_ms"], totals["tool_calls"], totals["refusals"]) == (3, 87000.0, 7, 1)
    assert totals["outcomes"] == {"ok": 3} and (totals["budget_given"], totals["budget_used"], totals["budget_returned"]) == (6, 3, 3)
    assert totals["wall_ms"] == 125000.0 and totals["user_wait_ms"] == 0 and 70000 < totals["queue_ms"] < 80000  # type: ignore[operator]
    assert table(tr, "window") == {"start": ids["task"][:21], "end": ids["res"][:21]}


def test_a_message_of_the_request_is_resolved_to_its_request(w: ObservabilityWorld) -> None:
    ids = request(w)
    tr = w.traces.trace(ids["sub"], now=NOW)
    assert tr["task"] == ids["task"] and tr["notes"] == [f"{ids['sub']} belongs to the request {ids['task']}; showing that"]
    assert tr["partial"] is False  # a redirect is information, not a gap


def test_an_unknown_id_names_the_latest_tasks_of_root(w: ObservabilityWorld) -> None:
    ids = request(w)
    with pytest.raises(OrgError, match=f"no message nope. Root's tasks \\(latest\\): {ids['task']}"):
        w.traces.trace("nope", now=NOW)


def test_a_message_whose_request_cannot_be_determined_is_refused(w: ObservabilityWorld) -> None:
    ids = request(w)
    note = w.send("root", "ceo", "note", 150, title="Hello")  # not a task, no trace, no link, nothing open
    with pytest.raises(OrgError, match=f"{note.id} is not a root task and its request cannot be determined. Root's tasks \\(latest\\): {ids['task']}"):
        w.traces.trace(note.id, now=NOW)


def test_without_events_the_trace_is_built_from_the_files_and_says_so(w: ObservabilityWorld) -> None:
    for addr in ("ceo", "ceo/eng"):
        w.agent(addr)
    task = w.send("root", "ceo", "task", 0, title="Ship it", budget=6, trace="self", box="read")
    w.run_log("ceo", 3, "# exit 0 after 42s\n", end=45)
    w.send("ceo", "root", "result", 50, title="Ship it", budget=2, status="done", reply_to=task.id, trace=task.id, box="read")
    tr = w.traces.trace(task.id, now=NOW)
    (run,) = runs_of(tr)
    assert run["source"] == "log" and run["duration_ms"] == 42000.0 and run["queue_ms"] is None
    assert tr["partial"] is True
    assert tr["notes"] == ["partial: no run events for this request (queue waits, tool calls and refusals unknown); runs and durations come from the run logs"]


def test_a_message_without_a_recorded_trace_gets_the_request_it_follows_from(w: ObservabilityWorld) -> None:
    for addr in ("ceo", "ceo/eng"):
        w.agent(addr)
    task = w.send("root", "ceo", "task", 0, title="Ship it", budget=6, box="read")  # no trace in its file: an organization older than traces
    sub = w.send("ceo", "ceo/eng", "task", 20, title="Build", budget=3, reply_to=task.id, box="read")
    tr = w.traces.trace(task.id, now=NOW)
    by_id = {i["id"]: i for i in items(tr) if i["kind"] == "message"}
    assert by_id[task.id]["trace_source"] == "derived:new" and by_id[sub.id]["trace_source"] == "derived:link"
    assert "2 message(s) have no recorded trace: their request was derived from reply_to/revises/open tasks (marked ~)" in tr["notes"]  # type: ignore[operator]


def test_what_waits_for_the_human_counts_until_the_next_action_of_root(w: ObservabilityWorld) -> None:
    for addr in ("ceo",):
        w.agent(addr)
    task = w.send("root", "ceo", "task", 0, title="Ship it", budget=6, trace="self", box="read")
    w.send("ceo", "root", "result", 20, title="Ship it", status="blocked", reply_to=task.id, trace=task.id, box="read")
    w.send("root", "ceo", "note", 50, title="Here you go", trace=task.id, box="read")
    tr = w.traces.trace(task.id, now=NOW)
    assert table(tr, "totals")["user_wait_ms"] == 30000.0 and tr["state"] == "blocked"


def test_a_rework_belongs_to_the_request_and_each_task_is_counted_apart(w: ObservabilityWorld) -> None:
    ids = request(w)
    again = w.send("root", "ceo", "task", 140, title="Ship it again", budget=3, revises=ids["task"], trace=ids["task"])
    w.run_log("ceo", 142, "# exit 0 after 5s\n", end=147)
    tr = w.traces.trace(again.id, now=NOW)  # the rework redirects to the request, which now ends with the rework
    assert tr["task"] == ids["task"] and tr["state"] == "open" and tr["end"] is None
    tasks = table(tr, "totals")["tasks"]
    assert [(t["task"], t["state"], t["runs"]) for t in tasks] == [(ids["task"], "done", 3), (again.id, "open", 1)]  # type: ignore[attr-defined]


def test_the_end_of_an_open_request_is_now(w: ObservabilityWorld) -> None:
    for addr in ("ceo",):
        w.agent(addr)
    task = w.send("root", "ceo", "task", 0, title="Ship it", budget=6, trace="self")
    tr = w.traces.trace(task.id, now=stamp(90))
    assert tr["state"] == "open" and table(tr, "totals")["wall_ms"] == 90000.0


def test_now_defaults_to_the_clock(w: ObservabilityWorld) -> None:
    w.agent("ceo")
    task = w.send("root", "ceo", "task", 0, title="Ship it", budget=6, trace="self")
    w.clock.at(60)
    wall = table(w.traces.trace(task.id), "totals")["wall_ms"]
    assert 60000 <= wall < 61000  # type: ignore[operator]
