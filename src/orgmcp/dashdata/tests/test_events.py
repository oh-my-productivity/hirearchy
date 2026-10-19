"""Events for a human: one readable line per event (moved from ``tests/test_dashboard_events.py``; the assertions are those)."""

from __future__ import annotations

import pytest

from orgmcp.dashdata import describe, event_lines, humanize

TS = "2026-10-18T10:05:27.000000Z"


def ev(kind: str, **kw: object) -> dict[str, object]:
    return {"v": 1, "ts": TS, "seq": 1, "proc": "mcp", "pid": 5, "kind": kind, **kw}


def lookup(agent: str, mid: str) -> tuple[str, str, str] | None:
    return {"m1": ("note", "Scope change", "root"), "m2": ("task", "Audit", "ceo")}.get(mid)


def test_the_lines_of_the_brief() -> None:
    assert humanize(ev("run.start", agent="ceo", actor="runtime", batch=["m1"], pgid=1, budget_before=9, run="ceo@x", traces=["t"]),
                    lookup=lookup).text == '10:05:27 run started (batch: note "Scope change" from root)'
    assert humanize(ev("tool.call", actor="ceo", tool="inbox", ok=True, ms=5)).text == "10:05:27 inbox ok 5ms"
    line = humanize(ev("tool.call", actor="ceo", tool="delegate", ok=False, ms=5, error_type="OrgError",
                       error="not enough budget: you have 5 run(s) and must keep 2 in reserve",
                       args={"to": "ceo/analyst", "budget": 9}))
    assert line.text == ("10:05:27 delegate → ceo/analyst REFUSED: not enough budget: you have 5 run(s) and must keep 2 in reserve")
    assert line.error
    line = humanize(ev("run.end", agent="ceo", ok=True, duration_ms=33000, exit_code=0, budget_after=2))
    assert line.text == "10:05:27 run ended ok after 33s" and not line.error
    assert humanize(ev("msg.deliver", actor="ceo", **{"from": "ceo"}, to="root", type="result", status="done",
                       title="Quarterly market report", id="x")).text == '10:05:27 sent result (done) "Quarterly market report" → root'


@pytest.mark.parametrize("e", [
    ev("run.start", agent="ceo", batch=["m1", "m2"], pgid=77, budget_before=9, run="ceo@2026", traces=["tr"], child_pid=78),
    ev("run.end", agent="ceo", ok=False, exit_code=1, duration_ms=1000, budget_after=1, run="ceo@2026", error="exit code 1"),
    ev("tool.call", actor="ceo", tool="read", ok=True, ms=3, args={"path": "a.md", "body_chars": 40}, run="ceo@2026", trace="tr"),
    ev("msg.deliver", actor="root", **{"from": "root"}, to="ceo", type="task", title="T", id="2026-id-root", trace="tr", hops=1, wake=True),
    ev("scheduler.heartbeat", running=["ceo@2026"], runnable=1, waiting_on_you=0),
    ev("agent.failure", agent="ops/deploy", count=2),
])
def test_ids_and_internals_stay_in_the_raw_form(e: dict[str, object]) -> None:
    text = humanize(e, actor=True, lookup=lookup).text
    for noise in ("pgid", "budget_before", "budget_after", "child_pid", "@2026", "trace=", "run=", "2026-id-root", "body_chars", "hops"):
        assert noise not in text, text
    assert "=" not in text
    raw = event_lines([e], raw=True)[0].text
    assert str(e["kind"]) in raw  # the raw form is format_event
    assert "=" in raw or e["kind"] == "agent.failure"


def test_run_start_batches() -> None:
    e = ev("run.start", agent="ceo", batch=["m1", "m2", "m3", "m4", "m5"])
    assert describe(e, lookup=lambda a, i: ("note", f"T{i}", "root")).startswith('run started (batch: note "Tm1" from root, note "Tm2" from root, note "Tm3" from root, +2 more)')
    assert describe(e) == "run started (batch of 5 message(s))"  # without a lookup the messages are only counted
    assert describe(ev("run.start", agent="ceo", batch=["gone"]), lookup=lambda a, i: None) == "run started (batch of 1 message(s))"
    assert describe(ev("run.start", agent="ceo", batch=[])) == "run started"


def test_messages_read_from_either_side() -> None:
    e = ev("msg.deliver", actor="ceo", **{"from": "ceo"}, to="ceo/analyst", type="task", title="Collect", budget=4)
    assert describe(e, me="ceo") == 'sent task "Collect" → ceo/analyst +4 run(s)'
    assert describe(e, me="ceo/analyst") == 'received task "Collect" from ceo +4 run(s)'
    assert describe(e) == 'sent task "Collect" → ceo/analyst +4 run(s)'


def test_failures_are_errors_and_say_why() -> None:
    bad = [ev("run.end", agent="a", ok=False, duration_ms=2000, error="exit code 3"),
           ev("run.end", agent="a", ok=True, duration_ms=2000, timed_out=True),
           ev("tool.call", actor="a", tool="send", ok=False, error_type="KeyError", error="'x'"),
           ev("scheduler.error", phase="reap", error="boom"), ev("run.orphan", agent="a", action="kept", detail="may be alive")]
    lines = event_lines(bad)
    assert all(x.error for x in lines)
    assert "FAILED after 2.0s: exit code 3" in lines[0].text and "timed out" in lines[1].text and "FAILED: 'x'" in lines[2].text
    assert not humanize(ev("tool.call", actor="a", tool="read", ok=True, ms=1)).error


def test_the_who_column_of_the_merged_stream() -> None:
    assert humanize(ev("run.end", agent="ops/deploy", actor="runtime", ok=True, duration_ms=1), actor=True).text.split()[1] == "ops/deploy"
    assert humanize(ev("scheduler.heartbeat", actor="runtime", running=[]), actor=True).text.split()[1] == "scheduler"
    assert humanize(ev("tool.call", actor="ceo", tool="read", ok=True, ms=1), actor=True).text.split()[1] == "ceo"


def test_unknown_kinds_and_odd_events_do_not_raise() -> None:
    assert describe(ev("something.new", answer=42, pid=1)).startswith("something.new answer=42")
    odd: list[dict[str, object]] = [{}, {"kind": None}, {"ts": "garbage", "kind": "tool.call"}, ev("tool.call"), ev("run.end"), ev("msg.deliver"),
                                    ev("tool.call", args="not a dict"), ev("prune", removed_days=3)]
    for e in odd:
        assert isinstance(humanize(e, actor=True, me="x", lookup=lookup).text, str)


def test_a_line_is_cut_to_the_width_it_is_given() -> None:
    line = humanize(ev("tool.call", actor="ceo", tool="read", ok=True, ms=1), width=12)
    assert line.text == "10:05:27 rea…" or len(line.text) <= 12
    assert len(humanize(ev("tool.call", actor="ceo", tool="read", ok=True, ms=1), width=200).text) < 200


def test_every_scheduler_and_agent_kind_has_its_words() -> None:
    assert describe(ev("scheduler.start", mode="until_done", max_parallel=2)) == "scheduler started (until_done, max_parallel 2)"
    assert describe(ev("scheduler.exit", reason="finished: no open tasks")) == "scheduler exited: finished: no open tasks"
    assert describe(ev("scheduler.heartbeat", running=["a", "b"], runnable=1, waiting_on_you=2)) == "scheduler heartbeat: 2 running, 1 runnable, 2 waiting on you"
    assert describe(ev("scheduler.error", phase="reap", error="boom")) == "scheduler error in reap: boom"
    assert describe(ev("stall.nudge", to="ceo", step=2)) == "stall nudge → ceo (step 2)"
    assert describe(ev("prune", removed_days=["a", "b"])) == "pruned 2 old day(s) of events"
    assert describe(ev("review.run", flagged=3)) == "review run: 3 flagged"
    assert describe(ev("agent.pause", reason="x")) == "paused: x" and describe(ev("agent.resume")) == "resumed"
    assert describe(ev("agent.hire", agent="ops", role="Ops")) == "hired ops (Ops)" and describe(ev("agent.retire", agent="ops", reason="done")) == "retired ops: done"
    assert describe(ev("service.define", owner="ceo", service="brief", version=2)) == "service ceo/brief v2 defined"
    assert describe(ev("cli.command", command="status", ok=True, ms=3)) == "command `orgmcp status` ok 3ms"
    assert describe(ev("cli.command", command="status", ok=False, error="boom")) == "command `orgmcp status` FAILED: boom"
    assert describe(ev("agent.failure", count=3)) == "run failed: 3 consecutive failed run(s)"
