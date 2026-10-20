"""The functions of ``observe.py`` that stand for the first half of ``observability`` - ``events_view``, ``events``, ``follow_events``, ``trace``,
``metrics``, ``percentile`` ... - say what they always said, and ask the package.

The expected files were captured from ``observe.py`` before the package existed (``orgmcp/observability/tests/expected``); the rendered texts are
the ones the command line and the MCP tool print. The cases of ``tests/test_observe`` stay as they were."""

from __future__ import annotations

import dataclasses
import json
import re
from pathlib import Path
from typing import Any

import pytest

from orgmcp import observe
from orgmcp.kernel.testing import FakeClock
from orgmcp.observability import api
from orgmcp.observability.tests import _scenario
from orgmcp.observability.tests._scenario import NOW, SINCE, stamp
from orgmcp.observability.tests._support import expected
from orgmcp.progress import progress

EVENTS: dict[str, dict[str, Any]] = {
    "all": dict(since=SINCE), "errors": dict(since=SINCE, errors=True), "agent_limit": dict(since=SINCE, agent="ceo/eng", limit=3),
    "kind_run": dict(since=SINCE, kind="run"), "kind_tool": dict(since=SINCE, kind="tool.call", limit=5),
    "window": dict(since=stamp(10), until=stamp(70)), "relative": dict(since="3m", until="now"),
}
METRICS: dict[str, dict[str, Any]] = {
    "plain": {}, "by_agent": dict(by="agent"), "by_tool": dict(by="tool"), "by_service": dict(by="service"), "by_trace": dict(by="trace"),
    "agent": dict(agent="ceo", by="tool"), "narrow": dict(since="2m"),
}


def dump(data: object) -> str:
    return json.dumps(getattr(observe, "_plain")(data), indent=2, default=str) + "\n"  # what the command line prints


@pytest.fixture
def clock(process_overrides: Any) -> Any:
    return _scenario.install(process_overrides)


@pytest.fixture
def built(tmp_path: Path, clock: Any) -> Any:
    made = _scenario.story(tmp_path, clock)
    _scenario.extend(made)
    return made


@pytest.fixture
def bare(tmp_path: Path, clock: Any) -> Any:
    return _scenario.make_org(tmp_path)


@pytest.mark.parametrize("name", EVENTS)
def test_events_view_and_its_text(built: Any, name: str) -> None:
    view = observe.events_view(built.org, now=NOW, **EVENTS[name])
    assert dump(view) == expected(f"events_{name}.json")
    assert observe.events(built.org, now=NOW, **EVENTS[name]) == view["events"]
    view["any"] = True
    assert observe.render_events(view) + "\n" == expected(f"events_{name}.txt")


@pytest.mark.parametrize("name", METRICS)
def test_metrics_and_their_text(built: Any, name: str) -> None:
    m = observe.metrics(built.org, **{"since": SINCE, **METRICS[name]}, now=NOW)
    assert dump(m) == expected(f"metrics_{name}.json")
    assert observe.render_metrics(m) + "\n" == expected(f"metrics_{name}.txt")


def test_trace_and_its_text(built: Any) -> None:
    tr = observe.trace(built.org, built.task.id, NOW)
    assert dump(tr) == expected("trace_recorded.json") and observe.render_trace(tr) + "\n" == expected("trace_recorded.txt")
    assert dump(observe.trace(built.org, built.sub.id, NOW)) == expected("trace_of_message.json")
    rework = observe.trace(built.org, built.again.id, NOW)
    assert dump(rework) == expected("trace_rework.json") and observe.render_trace(rework) + "\n" == expected("trace_rework.txt")


@pytest.mark.parametrize(("label", "kw"), [("derived", dict(record=False)), ("noevents", dict(events=False))])
def test_trace_of_an_organization_that_records_less(tmp_path: Path, clock: Any, label: str, kw: dict[str, bool]) -> None:
    built = _scenario.story(tmp_path, clock, **kw)
    tr = observe.trace(built.org, built.task.id, NOW)
    assert dump(tr) == expected(f"trace_{label}.json") and observe.render_trace(tr) + "\n" == expected(f"trace_{label}.txt")
    assert dump({k: v.__dict__ for k, v in observe.build_messages(observe.scan_messages(built.org)).items()}) == expected(f"messages_{label}.json")


def test_the_trace_counts_the_runs_of_each_task_as_progress_does(built: Any) -> None:
    tr = observe.trace(built.org, built.again.id, NOW)
    tasks = tr["totals"]["tasks"]
    assert len(tasks) == 2
    for task in tasks:
        line = progress(built.org, task["task"])
        assert f"runs {task['runs']} of {task['budget']}" in line, (line, task)


def test_follow_events_sleeps_the_given_function_between_polls(built: Any) -> None:
    slept: list[float] = []

    def sleeper(seconds: float) -> None:
        slept.append(seconds)
        built.log.tool(stamp(300 + len(slept)), "ceo", f"t{len(slept)}")

    got = [e["tool"] for e in observe.follow_events(built.org, kind="tool", poll=0.5, sleep=sleeper, max_polls=3)]
    assert got == ["t1", "t2"] and slept == [0.5, 0.5]


def test_traces_is_still_the_name_of_the_deriver_over_an_org(built: Any) -> None:
    msgs = observe.build_messages(observe.scan_messages(built.org))
    traces = observe.Traces(built.org, msgs)
    assert traces.of(built.task.id) == (built.task.id, "recorded") and traces.of("nope") == (None, "unknown")


def test_the_pure_names_are_the_packages() -> None:
    for name in ("fmt_rel", "percentile", "normalize_refusal", "is_error", "format_event"):
        assert getattr(observe, name) is getattr(api, name), name
    assert observe.parse_when("15m", stamp(0)) == stamp(-900)


def test_the_default_now_is_the_clock_of_the_runtime(built: Any) -> None:
    until = observe.metrics(built.org, since=SINCE)["until"]
    assert re.fullmatch(r"2026-10-18T10:02:3\d\.\d+\+00:00", str(until)) or str(until).startswith("2026-10-18T10:02:"), until
    assert observe.events_view(built.org, since="1h")["since"] < str(until)


def test_the_clock_of_the_runtime_is_what_a_default_now_is_made_of(built: Any) -> None:
    built.org.runtime = dataclasses.replace(built.org.runtime, clock=FakeClock(NOW))
    assert observe.metrics(built.org, since=SINCE)["until"].startswith("2026-10-18T10:03:20")
    assert 199999.0 < observe.trace(built.org, built.task.id)["totals"]["wall_ms"] <= 200000.0  # the request is open (reworked): it lasts until now
    assert observe.events_view(built.org, since="1h")["until"] is None


# ------------------------------------------------------------------------------ the second half (C-obs-2): now, check, the text

@pytest.mark.parametrize("name", list(_scenario.SCENARIOS))
def test_now_and_check_and_their_text(built: Any, name: str) -> None:
    setup, state, verdict = _scenario.SCENARIOS[name]
    setup(built)
    _scenario.settle(built.org)
    _scenario.follow_ports(built.org, state, verdict)
    view = observe.now_view(built.org, NOW)
    assert dump(view) == expected(f"now_{name}.json") and observe.render_now(view) + "\n" == expected(f"now_{name}.txt")
    result = observe.check(built.org, NOW)
    assert dump(result) == expected(f"check_{name}.json") and observe.render_check(result) + "\n" == expected(f"check_{name}.txt")


def test_now_and_check_of_an_organization_nothing_happened_in(bare: Any) -> None:
    _scenario.follow_ports(bare, ("stopped", None, None, ""), "gone")
    assert dump(observe.now_view(bare, NOW)) == expected("now_bare.json")
    assert dump(observe.check(bare, NOW)) == expected("check_bare.json")
    assert observe.observe_text(bare, "events", since=SINCE, now=NOW) + "\n" == expected("text_events_none.txt")


def test_observe_text(built: Any) -> None:
    setup, state, verdict = _scenario.SCENARIOS["busy"]
    setup(built)
    _scenario.settle(built.org)
    _scenario.follow_ports(built.org, state, verdict)
    cases: dict[str, dict[str, Any]] = {
        "now": dict(view="now"), "check": dict(view="check"), "trace": dict(view="trace", target=built.task.id), "metrics": dict(view="metrics"),
        "metrics_agent": dict(view="metrics", target="ceo", by="tool"), "events": dict(view="events"), "events_agent": dict(view="events", target="ceo/eng"),
        "events_trace": dict(view="events", target=built.task.id), "events_kind": dict(view="events", target="tool.call"),
        "events_errors": dict(view="events", errors_only=True, limit=3), "events_root": dict(view="events", target="root"), "now_small": dict(view="now", limit=2),
    }
    for label, kw in cases.items():
        assert observe.observe_text(built.org, since=SINCE, now=NOW, **kw) + "\n" == expected(f"text_{label}.txt"), label
    assert observe.observe_text(built.org, " NOW ", since=SINCE, now=NOW) + "\n" == expected("text_view_upper.txt")
    assert observe.render_now(observe.now_view(built.org, NOW), 12) + "\n" == expected("now_busy_capped.txt")


def test_the_scheduler_and_the_judge_are_those_of_the_runtime_in_force(built: Any) -> None:
    setup, _, _ = _scenario.SCENARIOS["busy"]
    setup(built)
    _scenario.settle(built.org)
    _scenario.follow_ports(built.org, _scenario.RUNNING, "ours")
    assert observe.now_view(built.org, NOW)["scheduler"]["state"] == "running"
    _scenario.follow_ports(built.org, _scenario.STOPPED, "gone")
    assert observe.now_view(built.org, NOW)["scheduler"]["state"] == "stopped"
    assert not observe.check(built.org, NOW)["ok"]


def test_the_legacy_names_that_stay(built: Any) -> None:
    assert observe.VIEWS == ("now", "trace", "metrics", "events", "check") and observe.COPY_GRACE == 5.0 and observe.INFLIGHT_GRACE == 30.0
    assert observe.ERROR_WINDOW.total_seconds() == 900 and observe.RECV_BOXES == ("inbox", "inflight", "read")
    assert observe._scheduler_files(built.org) and observe._tail_events(observe._scheduler_files(built.org)[0][2]) is not None
