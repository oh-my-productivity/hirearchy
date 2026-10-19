"""Contract of ``ObservabilityText``: the text of one view by its name, over an organization on disk and one in memory.

The text is what the renderer makes of the view the queries answer, so these tests ask for the views and render them too."""

from __future__ import annotations

from pathlib import Path

import pytest

from orgmcp.kernel import OrgError
from orgmcp.observability import ObservabilityText
from orgmcp.observability.testing import IMPLEMENTATIONS, ObservabilityWorld

from . import _support
from ._support import RED, stamp

pytestmark = RED

NOW = stamp(500)
SINCE = "2026-10-18T00:00:00Z"


@pytest.fixture(params=_support.implementations(IMPLEMENTATIONS[ObservabilityText]))
def w(request: pytest.FixtureRequest, tmp_path: Path) -> ObservabilityWorld:
    made: ObservabilityWorld = request.param(tmp_path)
    assert isinstance(made.text, ObservabilityText)
    made.agent("ceo")
    made.agent("ceo/eng")
    return made


def test_now_is_the_text_of_the_now_view(w: ObservabilityWorld) -> None:
    w.tool(100, "ceo", "send", ok=False, error="nope")
    assert w.text.observe_text("now", now=NOW) == w.renderer.render_now(w.now.now_view(NOW), 100)


def test_check_is_the_text_of_the_checks(w: ObservabilityWorld) -> None:
    w.settle()
    assert w.text.observe_text("check", now=NOW) == w.renderer.render_check(w.checks.check(NOW))
    assert w.text.observe_text("check", now=NOW).endswith("all checks passed")


def test_trace_is_the_text_of_the_trace_of_the_target(w: ObservabilityWorld) -> None:
    task = w.send("root", "ceo", "task", 0, title="Ship it", budget=2, trace="self", box="read")
    assert w.text.observe_text("trace", task.id, now=NOW) == w.renderer.render_trace(w.traces.trace(task.id, NOW), 100)


def test_metrics_are_the_text_of_the_metrics_for_the_target_agent(w: ObservabilityWorld) -> None:
    w.tool(100, "ceo", "send")
    assert w.text.observe_text("metrics", "ceo", since=SINCE, by="tool", now=NOW) == w.renderer.render_metrics(
        w.metrics.metrics(SINCE, "tool", NOW, "ceo"), 50
    )


def test_events_are_the_text_of_the_events_the_target_names(w: ObservabilityWorld) -> None:
    w.tool(100, "ceo", "send", trace="T-1")
    w.tool(101, "ceo/eng", "write")
    for target, expect in (("ceo", {"agent": "ceo"}), ("tool.call", {"kind": "tool.call"}), ("20261018T100000000000-root-0001", {"trace": "20261018T100000000000-root-0001"})):
        view = w.events.events_view(SINCE, None, expect.get("agent"), expect.get("kind"), expect.get("trace"), False, 50, NOW)
        view["any"] = True
        assert w.text.observe_text("events", target, since=SINCE, now=NOW) == w.renderer.render_events(view, 100)


def test_events_say_when_the_organization_has_no_event_files(w: ObservabilityWorld) -> None:
    assert w.text.observe_text("events", since=SINCE, now=NOW) == "(no matching events) - this organization has no event files yet"
    w.tool(100, "ceo", "send", ok=False, error="boom")
    assert "1 of 1 matching event(s)" in w.text.observe_text("events", since=SINCE, now=NOW)


def test_the_limit_is_the_events_shown_and_the_lines_are_twice_the_limit_at_least_eighty(w: ObservabilityWorld) -> None:
    for i in range(30):
        w.tool(100 + i, "ceo", "send")
    assert w.text.observe_text("events", since=SINCE, limit=3, now=NOW).splitlines()[0].startswith("3 of 30 matching event(s)")
    assert len(w.text.observe_text("events", since=SINCE, limit=30, max_lines=5, now=NOW).splitlines()) == 7  # head, 5 lines, the cut hint


def test_the_name_of_the_view_is_stripped_and_lowercased(w: ObservabilityWorld) -> None:
    assert w.text.observe_text("  NOW ", now=NOW) == w.text.observe_text("now", now=NOW) == w.text.observe_text(None, now=NOW)  # type: ignore[arg-type]


def test_another_view_is_refused(w: ObservabilityWorld) -> None:
    with pytest.raises(OrgError, match="view must be one of now, trace, metrics, events, check"):
        w.text.observe_text("nope")


def test_a_trace_needs_a_target(w: ObservabilityWorld) -> None:
    with pytest.raises(OrgError, match="trace needs target=<root task id>"):
        w.text.observe_text("trace")


def test_a_trace_of_nothing_is_refused_by_the_trace(w: ObservabilityWorld) -> None:
    with pytest.raises(OrgError, match="no message nope"):
        w.text.observe_text("trace", "nope", now=NOW)
