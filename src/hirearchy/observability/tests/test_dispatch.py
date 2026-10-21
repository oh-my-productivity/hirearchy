"""``ViewDispatcher``: the text of one view by its name, asked of the queries, the checks and the renderer; ``AgentTargetedEvents``: what a target names."""

from __future__ import annotations

from datetime import datetime
from typing import Any

import pytest

from hirearchy.agents.testing import fs_agents
from hirearchy.eventlog.testing import MemoryEventLog
from hirearchy.kernel import OrgError
from hirearchy.kernel.testing import FakeClock
from hirearchy.observability import ObservabilityRenderer
from hirearchy.observability._dispatch import AgentTargetedEvents, ViewDispatcher
from hirearchy.observability._ports import TargetedEvents
from hirearchy.observability.testing import FixedEventQueries, FixedIntegrityChecks, FixedMetricQueries, FixedNowQueries, FixedTraceQueries, stamp



NOW = stamp(200)


class Words(ObservabilityRenderer):
    """A renderer that says what it was given."""

    def render_events(self, view: dict[str, Any], max_lines: int | None = None) -> str:
        return f"events {view.get('any')} {max_lines}"

    def render_trace(self, tr: dict[str, Any], max_lines: int | None = None) -> str:
        return f"trace {tr.get('task')} {max_lines}"

    def render_metrics(self, m: dict[str, Any], limit: int = 50) -> str:
        return f"metrics {limit}"

    def render_now(self, v: dict[str, Any], max_lines: int | None = None) -> str:
        return f"now {max_lines}"

    def render_check(self, res: dict[str, Any]) -> str:
        return "check"


class Targets(TargetedEvents):
    def __init__(self) -> None:
        self.asked: list[tuple[Any, ...]] = []

    def view(self, target: str | None, since: str, errors_only: bool, limit: int, now: datetime | None) -> dict[str, Any]:
        self.asked.append((target, since, errors_only, limit, now))
        return {"events": [], "any": True}


class World:
    def __init__(self) -> None:
        self.targets, self.traces = Targets(), FixedTraceQueries({"T-1": {"task": "T-1"}})
        self.metrics, self.now, self.checks = FixedMetricQueries({}), FixedNowQueries({}), FixedIntegrityChecks()
        self.text = ViewDispatcher(self.targets, self.traces, self.metrics, self.now, self.checks, Words())


def test_the_lines_are_capped_at_twice_the_limit_and_at_least_eighty() -> None:
    w = World()
    assert w.text.observe_text("now", now=NOW) == "now 100" and w.text.observe_text("now", limit=10, now=NOW) == "now 80"
    assert w.text.observe_text("now", limit=100, now=NOW) == "now 200" and w.text.observe_text("now", max_lines=7, now=NOW) == "now 7"
    assert w.now.asked == [NOW] * 4


def test_the_limit_is_at_least_one_and_defaults_to_fifty() -> None:
    w = World()
    assert w.text.observe_text("metrics", limit=0) == "metrics 50" and w.text.observe_text("metrics", limit=-3) == "metrics 1"
    assert w.metrics.asked[0] == dict(since="24h", by=None, now=None, agent=None)


def test_metrics_are_asked_for_the_target_as_an_agent() -> None:
    w = World()
    w.text.observe_text("metrics", "ceo", "2h", "tool", now=NOW)
    assert w.metrics.asked == [dict(since="2h", by="tool", now=NOW, agent="ceo")]


def test_a_trace_needs_a_target_and_asks_for_it() -> None:
    w = World()
    assert w.text.observe_text("trace", "T-1", now=NOW) == "trace T-1 100" and w.traces.asked == [("T-1", NOW)]
    with pytest.raises(OrgError, match="trace needs target=<root task id> .see progress for the ids."):
        w.text.observe_text("trace")


def test_the_check_is_asked_for_the_time() -> None:
    w = World()
    assert w.text.observe_text("check", now=NOW) == "check" and w.checks.asked == [NOW]


def test_events_are_asked_of_the_targeted_view() -> None:
    w = World()
    assert w.text.observe_text("events", "ceo", "3h", errors_only=True, limit=7, now=NOW) == "events True 80"
    assert w.targets.asked == [("ceo", "3h", True, 7, NOW)]


def test_the_view_name_is_stripped_and_lowercased_and_none_means_now() -> None:
    w = World()
    assert w.text.observe_text("  Now ") == "now 100" and w.text.observe_text(None) == "now 100"  # type: ignore[arg-type]
    assert w.text.observe_text("") == "now 100"


def test_another_view_is_an_error_that_lists_the_views() -> None:
    with pytest.raises(OrgError, match="view must be one of now, trace, metrics, events, check"):
        World().text.observe_text("nope")


# ------------------------------------------------------------------------------ what a target names


def targeted(tmp_path: Any, files: bool = False) -> tuple[AgentTargetedEvents, FixedEventQueries, MemoryEventLog]:
    agents = fs_agents(tmp_path)
    agents.put("ceo/AGENT.md", "---\nrole: ceo\n---\nc\n")
    log = MemoryEventLog(FakeClock())
    if files:
        log.append("2026-10-18", "mcp-1-1.jsonl", b"{}\n")
    fixed = FixedEventQueries()
    return AgentTargetedEvents(fixed, agents.directory, log), fixed, log


def asked(fixed: FixedEventQueries) -> dict[str, Any]:
    (name, kw), = fixed.asked
    assert name == "events_view"
    return kw


@pytest.mark.parametrize(
    ("target", "agent", "kind", "trace"),
    [
        (None, None, None, None),
        ("ceo", "ceo", None, None),
        ("root", "root", None, None),
        ("runtime", "runtime", None, None),
        ("tool.call", None, "tool.call", None),
        ("run", None, "run", None),
        ("20261018T100000000000-root-0001", None, None, "20261018T100000000000-root-0001"),
        ("nobody", None, "nobody", None),
    ],
)
def test_a_target_is_a_trace_an_agent_or_a_kind(tmp_path: Any, target: str | None, agent: str | None, kind: str | None, trace: str | None) -> None:
    view, fixed, _ = targeted(tmp_path)
    view.view(target, "24h", False, 50, NOW)
    got = asked(fixed)
    assert (got["agent"], got["kind"], got["trace"]) == (agent, kind, trace)
    assert (got["since"], got["until"], got["errors"], got["limit"], got["now"]) == ("24h", None, False, 50, NOW)


def test_the_view_says_whether_the_organization_has_event_files(tmp_path: Any) -> None:
    assert targeted(tmp_path)[0].view(None, "24h", False, 50, NOW)["any"] is False
    assert targeted(tmp_path, files=True)[0].view(None, "24h", False, 50, NOW)["any"] is True
