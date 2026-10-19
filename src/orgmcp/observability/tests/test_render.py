"""``TextObservabilityRenderer``: the text of the views, character for character as ``observe.render_*`` made it.

The views are the expected JSON files (what the queries answer, captured before the move), the text the expected ``.txt`` beside each."""

from __future__ import annotations

import json
from typing import Any

import pytest

from orgmcp.observability._render import TextObservabilityRenderer

from ._support import RED, expected

pytestmark = RED

R = TextObservabilityRenderer()


def view(name: str) -> dict[str, Any]:
    loaded: dict[str, Any] = json.loads(expected(name))
    return loaded


@pytest.mark.parametrize("name", ["all", "errors", "agent_limit", "kind_run", "kind_tool", "window", "relative", "trace"])
def test_events(name: str) -> None:
    assert R.render_events(view(f"events_{name}.json")) + "\n" == expected(f"events_{name}.txt")


@pytest.mark.parametrize("name", ["recorded", "derived", "noevents", "rework"])
def test_traces(name: str) -> None:
    assert R.render_trace(view(f"trace_{name}.json")) + "\n" == expected(f"trace_{name}.txt")


@pytest.mark.parametrize("name", ["plain", "by_agent", "by_tool", "by_service", "by_trace", "agent", "narrow"])
def test_metrics(name: str) -> None:
    assert R.render_metrics(view(f"metrics_{name}.json")) + "\n" == expected(f"metrics_{name}.txt")


@pytest.mark.parametrize("name", ["stopped", "ready", "unverified", "busy", "busy_full", "story", "retired", "corrupt", "corrupt_unverified", "bare"])
def test_now_and_check(name: str) -> None:
    assert R.render_now(view(f"now_{name}.json")) + "\n" == expected(f"now_{name}.txt")
    assert R.render_check(view(f"check_{name}.json")) + "\n" == expected(f"check_{name}.txt")


def test_no_events_say_whether_the_organization_has_event_files() -> None:
    empty = {"events": [], "total": 0, "shown": 0}
    assert R.render_events(empty) == "(no matching events)" and R.render_events({**empty, "any": True}) == "(no matching events)"
    assert R.render_events({**empty, "any": False}) == "(no matching events) - this organization has no event files yet"


def test_events_that_were_cut_say_how_many_and_how_to_narrow() -> None:
    cut = {"events": [{"ts": "2026-10-18T10:00:00+00:00", "kind": "tool.call", "actor": "ceo", "tool": "x", "ok": True}], "total": 4, "shown": 1}
    head = R.render_events(cut).splitlines()[0]
    assert head == "1 of 4 matching event(s), oldest first - 3 earlier one(s) not shown: narrow with since/agent/kind/trace or raise the limit"


def test_a_view_longer_than_the_cap_ends_with_the_hint() -> None:
    lines = R.render_now(view("now_busy.json"), 4).splitlines()
    assert len(lines) == 5 and lines[-1].startswith("... ") and lines[-1].endswith("narrow with observe events errors_only=true")


def test_the_verdict_of_a_check_names_the_failed_ones() -> None:
    res = {"ok": False, "checks": [{"id": "a", "name": "n", "ok": True, "details": ["d"]}, {"id": "b", "name": "m", "ok": False, "details": ["x", "y"]}]}
    assert R.render_check(res) == "(a) PASS n\n      d\n(b) FAIL m\n      x\n      y\nFAILED: b"
    assert R.render_check({"ok": True, "checks": []}) == "all checks passed"
