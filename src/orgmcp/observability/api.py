"""The public surface of ``observability``: what the runtime did, answered from the files alone.

Everything here is read-only: a pure function of the files of an organization directory (nothing is written, no lock is taken).

* ``events``  the merged raw stream of the per-process event files (filterable, followable): ``EventQueries``;
* ``trace``   one request (a root task) as a tree of messages, runs, tool calls and refusals, with totals: ``TraceQueries``;
* ``metrics`` counts, rates and latency percentiles over a time window, optionally grouped: ``MetricQueries``.

(``now``, ``check`` and the text of every view are the second half of the package; they arrive with step C-obs-2.)

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
    "MetricQueries",
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
