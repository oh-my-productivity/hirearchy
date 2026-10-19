"""The public surface of ``observability``: what the runtime did, answered from the files alone.

Everything here is read-only: a pure function of the files of an organization directory (nothing is written, no lock is taken).

* ``events``  the merged raw stream of the per-process event files (filterable, followable): ``EventQueries``;
* ``trace``   one request (a root task) as a tree of messages, runs, tool calls and refusals, with totals: ``TraceQueries``;
* ``metrics`` counts, rates and latency percentiles over a time window, optionally grouped: ``MetricQueries``.

* ``now``     what is happening right now: scheduler, runs in flight, what is queued and why, what waits on you, what broke lately: ``NowQueries``;
* ``check``   the invariants of the runtime itself (messages intact, budget conserved, nothing stuck, runs accounted for): ``IntegrityChecks``.

``ObservabilityRenderer`` turns each view into compact text and ``ObservabilityText`` is the single entry point (the MCP tool ``observe`` and the
command line): the text of one view by its name.

Each view returns a JSON-able dict. The event files are written by the runtime: one append-only JSONL file per process per UTC day. The
readers tolerate what a live system produces: a partial last line, unknown kinds and fields, missing directories, files of other days, and an
organization that has no events at all (then ``trace`` falls back to the message files and run logs and says so).

The pure functions are the vocabulary of the views: ``percentile`` (nearest rank), ``parse_when`` (``15m`` / ``24h`` / ISO), ``fmt_rel`` (time
within a request), ``normalize_refusal`` (what varies removed, so reasons group), ``is_error`` (what an event means by going wrong) and
``format_event`` (one line).
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime
from typing import Protocol, runtime_checkable

from ..kernel import JsonObject
from ._pure import fmt_rel, format_event, is_error, normalize_refusal, parse_when, percentile

__all__ = [
    "EventQueries",
    "IntegrityChecks",
    "MetricQueries",
    "NowQueries",
    "ObservabilityRenderer",
    "ObservabilityText",
    "TraceQueries",
    "fmt_rel",
    "format_event",
    "is_error",
    "normalize_refusal",
    "parse_when",
    "percentile",
]


@runtime_checkable
class EventQueries(Protocol):
    def events_view(
        self,
        since: str | datetime | None = None,
        until: str | datetime | None = None,
        agent: str | None = None,
        kind: str | None = None,
        trace: str | None = None,
        errors: bool = False,
        limit: int | None = None,
        now: datetime | None = None,
    ) -> JsonObject:
        """The merged raw stream, filtered by time window first, then by fields: ``{"events", "total", "shown", "since", "until"}``.
        ``since`` / ``until`` are durations before ``now`` (``15m``, ``24h``), ``now`` or ISO timestamps (``parse_when``; an unreadable
        one is an ``OrgError``). ``kind`` matches the kind or its prefix (``run`` matches ``run.start``); ``agent`` the actor, the agent
        or the sender or recipient of the event; ``trace`` the trace of the event or one of its ``traces``; ``errors`` only what ``is_error``
        says. With ``limit`` the LAST ``limit`` events of the window are kept (``total`` counts all that matched). ``now`` defaults to the clock."""
        ...

    def events(
        self,
        since: str | datetime | None = None,
        until: str | datetime | None = None,
        agent: str | None = None,
        kind: str | None = None,
        trace: str | None = None,
        errors: bool = False,
        limit: int | None = None,
        now: datetime | None = None,
    ) -> list[JsonObject]:
        """The matching events (the last ``limit`` of them), oldest first."""
        ...

    def follow(
        self,
        agent: str | None = None,
        kind: str | None = None,
        trace: str | None = None,
        errors: bool = False,
        poll: float = 0.5,
        max_polls: int | None = None,
    ) -> Iterator[JsonObject]:
        """New matching events as they are written (what is in the files already is not returned), polled every ``poll`` seconds of the
        clock; stops after ``max_polls`` polls when given, else never."""
        ...


@runtime_checkable
class TraceQueries(Protocol):
    def trace(self, task_id: str, now: datetime | None = None) -> JsonObject:
        """One request as a tree, in time order, with totals. ``task_id`` is a root task id (a message of the request is accepted too and
        resolved to its request; an unknown id, or a message whose request cannot be determined, is an ``OrgError`` that names root's
        latest tasks). Works from the message files and run logs alone (then ``partial``); run and tool-call events add queue wait,
        durations, tool calls and refusals.

        Totals: ``runs`` is what ``progress`` reports for the task (run logs of the task's team inside the task's window), ``run_ms`` the
        sum of their durations, ``queue_ms`` the sum of queue waits (run start minus earliest message of the batch), ``user_wait_ms`` the
        time items that needed the human waited for root's next action on the request, ``wall_ms`` task creation to the final result (or ``now``)."""
        ...


@runtime_checkable
class MetricQueries(Protocol):
    def metrics(self, since: str | datetime | None = "24h", by: str | None = None, now: datetime | None = None, agent: str | None = None) -> JsonObject:
        """Counts, rates and percentiles over ``[since, now]``. Runs are the run logs of the window (so counts equal what the files say), with
        outcome and duration from ``run.end`` events (else from the log's closing lines); percentiles are nearest-rank on the raw durations.
        ``by``: ``agent`` | ``tool`` | ``service`` | ``trace`` adds a table grouped that way (anything else is an ``OrgError``); ``agent``
        restricts to one agent."""
        ...


@runtime_checkable
class NowQueries(Protocol):
    def now_view(self, now: datetime | None = None) -> JsonObject:
        """What is happening right now (``now`` defaults to the clock): ``{"now", "scheduler", "max_parallel", "runs_in_flight", "queued",
        "waiting_on_you", "open_root_tasks", "paused", "errors_15m", "last_event", "events_seen"}``. ``scheduler`` is the state of the scheduler
        process with, while it runs, its mode, uptime and the age of its last heartbeat, else why the last one exited; ``runs_in_flight`` the runs
        that have a batch inflight with the time they have run and the traces of the batch; ``queued`` every agent with unread mail and why it
        has not started (a run still going, paused, no budget, no scheduler, ``max_parallel`` busy, or ready for the next tick); ``waiting_on_you``
        what root has to decide. Works with no events at all (then what is derived from events is empty)."""
        ...


@runtime_checkable
class IntegrityChecks(Protocol):
    def check(self, now: datetime | None = None) -> JsonObject:
        """The invariants of the runtime, each PASS/FAIL with details (read-only): ``{"ok", "checks": [{"id", "name", "ok", "details"}]}`` for
        (a) every message file parses, ids are unique, each sender copy has a recipient copy and vice versa; (b) budget conservation: what root
        handed down equals what agents hold plus what runs used plus what came back plus what was dropped at the retirement of a top-level agent;
        (c) nothing inflight without a live run; (d) every ``run.start`` has a ``run.end`` or a live process, and every run log since events began
        has a ``run.start``; (e) per-file ``seq`` has no gaps; (f) the scheduler pid file matches a live scheduler process."""
        ...


@runtime_checkable
class ObservabilityRenderer(Protocol):
    def render_events(self, view: JsonObject, max_lines: int | None = None) -> str:
        """The text of ``EventQueries.events_view`` (``view["any"]``, when present and false, says the organization has no event files yet)."""
        ...

    def render_trace(self, tr: JsonObject, max_lines: int | None = None) -> str:
        """The text of ``TraceQueries.trace``."""
        ...

    def render_metrics(self, m: JsonObject, limit: int = 50) -> str:
        """The text of ``MetricQueries.metrics``; ``limit`` rows of each table."""
        ...

    def render_now(self, v: JsonObject, max_lines: int | None = None) -> str:
        """The text of ``NowQueries.now_view``."""
        ...

    def render_check(self, res: JsonObject) -> str:
        """The text of ``IntegrityChecks.check``: one PASS/FAIL line per invariant with its details, then the verdict."""
        ...


@runtime_checkable
class ObservabilityText(Protocol):
    def observe_text(
        self,
        view: str = "now",
        target: str | None = None,
        since: str = "24h",
        by: str | None = None,
        errors_only: bool = False,
        limit: int = 50,
        now: datetime | None = None,
        max_lines: int | None = None,
    ) -> str:
        """The text of one view: ``now`` | ``trace`` | ``metrics`` | ``events`` | ``check`` (any other is an ``OrgError``; the name is stripped and
        lowercased, none means ``now``). ``target``: the root task id for ``trace`` (required); for ``events`` a trace id, an agent address or an
        event kind (``tool.call``, ``run``); for ``metrics`` an agent. ``limit``: events shown, rows per table (at least 1). ``max_lines`` caps
        the lines of a view (default: twice ``limit``, at least 80)."""
        ...
