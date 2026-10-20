"""``observability`` as the tests have always called it: ``now_view(org, now=...)``, ``trace(org, task_id)``, ``check(org)``, ``render_now(view)`` ...

Every view is a port of the runtime of the organization (``org.runtime.now_queries``, ``trace_queries``, ``metric_queries``, ``event_queries``,
``integrity_checks``, ``observability_renderer``, ``observability_text``); the functions here only hand the organization's port the arguments, in the order
the tests give them. The pure vocabulary (``percentile``, ``parse_when`` ...) is the package's api.

What a test needs to look different (the time, the scheduler, the processes) it puts into the runtime of its organization (``health_world.with_ports``)
before the view is asked.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from datetime import datetime
from pathlib import Path
from typing import Any

from orgmcp.app import wiring
from orgmcp.daemon import SchedulerState, SchedulerStatus
from orgmcp.daemon.testing import FakeSchedulerStatus
from orgmcp.kernel import Clock, fmt_dur
from orgmcp.kernel.testing import FakeClock
from orgmcp.observability import fmt_rel, format_event, is_error, normalize_refusal, parse_when, percentile

from .health_world import _OVERRIDES, with_clock, with_ports
from .obs_fixtures import T0

__all__ = [
    "check", "event_files", "events", "events_view", "fmt_dur", "fmt_rel", "follow_events", "format_event", "freeze", "is_error", "metrics", "normalize_refusal",
    "now_view", "observe_text", "parse_when", "percentile", "render_check", "render_events", "render_metrics", "render_now", "render_trace", "scheduler_is",
    "trace",
]


def freeze(org: Any) -> FakeClock:
    """The time of ``org`` stands still at ``obs_fixtures.T0`` until the test moves it (``clock.at(seconds)``; one microsecond per reading)."""
    clock = FakeClock(T0)
    with_clock(org, clock)
    return clock


def scheduler_is(_monkeypatch: object, state: SchedulerState, *orgs: Any) -> FakeSchedulerStatus:
    """The scheduler is in ``state`` for ``orgs`` (their runtimes are opened again with a status that says so)."""
    status = FakeSchedulerStatus(state)
    for org in orgs:
        with_ports(org, {SchedulerStatus: status})
    return status


# ------------------------------------------------------------------------------------------ the views


def event_files(org: Any, since: datetime | None = None, until: datetime | None = None) -> list[Path]:
    return [f.path for f in org.runtime.event_reader.files(since, until)]


def events_view(org: Any, since: Any = None, until: Any = None, agent: str | None = None, kind: str | None = None, trace: str | None = None,
                errors: bool = False, limit: int | None = None, now: datetime | None = None) -> dict[str, Any]:
    return org.runtime.event_queries.events_view(since, until, agent, kind, trace, errors, limit, now)  # type: ignore[no-any-return]


def events(org: Any, since: Any = None, until: Any = None, agent: str | None = None, kind: str | None = None, trace: str | None = None,
           errors: bool = False, limit: int | None = None, now: datetime | None = None) -> list[dict[str, Any]]:
    return org.runtime.event_queries.events(since, until, agent, kind, trace, errors, limit, now)  # type: ignore[no-any-return]


class _SleepingClock(Clock):
    """The clock of the organization, whose waits are ``sleep`` (a test makes the events appear while the follower waits)."""

    def __init__(self, inner: Clock, sleep: Callable[[float], None]) -> None:
        self._inner, self._sleep = inner, sleep

    def now(self) -> datetime:
        return self._inner.now()

    def time(self) -> float:
        return self._inner.time()

    def monotonic(self) -> float:
        return self._inner.monotonic()

    def sleep(self, seconds: float) -> None:
        self._sleep(seconds)


def follow_events(org: Any, agent: str | None = None, kind: str | None = None, trace: str | None = None, errors: bool = False, poll: float = 0.5,
                  sleep: Callable[[float], None] | None = None, max_polls: int | None = None) -> Iterator[dict[str, Any]]:
    overrides = {**getattr(org, _OVERRIDES, {})}
    if sleep is not None:
        overrides[Clock] = _SleepingClock(org.runtime.clock, sleep)
    return wiring.open_runtime(org.root, overrides).event_queries.follow(agent, kind, trace, errors, poll, max_polls)  # type: ignore[no-any-return]


def trace(org: Any, task_id: str, now: datetime | None = None) -> dict[str, Any]:
    return org.runtime.trace_queries.trace(task_id, now)  # type: ignore[no-any-return]


def metrics(org: Any, since: Any = "24h", by: str | None = None, now: datetime | None = None, agent: str | None = None) -> dict[str, Any]:
    return org.runtime.metric_queries.metrics(since, by, now, agent)  # type: ignore[no-any-return]


def now_view(org: Any, now: datetime | None = None) -> dict[str, Any]:
    return org.runtime.now_queries.now_view(now)  # type: ignore[no-any-return]


def check(org: Any, now: datetime | None = None) -> dict[str, Any]:
    return org.runtime.integrity_checks.check(now)  # type: ignore[no-any-return]


def observe_text(org: Any, view: str = "now", target: str | None = None, since: str = "24h", by: str | None = None, errors_only: bool = False,
                 limit: int = 50, now: datetime | None = None, max_lines: int | None = None) -> str:
    return org.runtime.observability_text.observe_text(view, target, since, by, errors_only, limit, now, max_lines)  # type: ignore[no-any-return]


# ------------------------------------------------------------------------------------------ the text of the views (pure: any runtime has the renderer)


def _renderer() -> Any:
    return wiring.open_runtime(Path.cwd()).observability_renderer


def render_events(view: dict[str, Any], max_lines: int | None = None) -> str:
    return _renderer().render_events(view, max_lines)  # type: ignore[no-any-return]


def render_trace(tr: dict[str, Any], max_lines: int | None = None) -> str:
    return _renderer().render_trace(tr, max_lines)  # type: ignore[no-any-return]


def render_metrics(m: dict[str, Any], limit: int = 50) -> str:
    return _renderer().render_metrics(m, limit)  # type: ignore[no-any-return]


def render_now(v: dict[str, Any], max_lines: int | None = None) -> str:
    return _renderer().render_now(v, max_lines)  # type: ignore[no-any-return]


def render_check(res: dict[str, Any]) -> str:
    return _renderer().render_check(res)  # type: ignore[no-any-return]
