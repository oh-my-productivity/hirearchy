"""Observability, the query half: read-only views over the event log, the message files and the run logs.

Everything here is a pure function of the files in an organization directory (nothing is written, no lock is taken):

* ``now``     what is happening right now: scheduler, runs in flight, what is queued and why, what waits on you,
              what broke in the last 15 minutes;
* ``trace``   one request (a root task) as a tree: messages, runs, tool calls and refusals, with totals;
* ``metrics`` counts, rates and latency percentiles over a time window, optionally grouped;
* ``events``  the merged raw stream of the per-process event files (filterable, followable);
* ``check``   invariants of the runtime itself (messages intact, budget conserved, nothing stuck, runs accounted for).

Each view returns a JSON-able dict; ``render_*`` turn it into compact text. ``observe_text`` is the single entry point
used by the MCP tool ``observe`` and by the CLI.

The event files are written by the runtime (see the observability spec, section 2): one append-only JSONL file per
process per UTC day, ``.runtime/events/<YYYY-MM-DD>/<proc>-<pid>-<start_epoch_ms>.jsonl``. The readers tolerate what
a live system produces: a partial last line, unknown kinds and fields, missing directories, files of other days, and
an organization that has no events at all (then ``trace`` falls back to the message files and run logs and says so).

THIS MODULE IS LEGACY (steps C-obs-1 and C-obs-2 of the refactor, ARCHITECTURE.md 3.31 and 5.10). Every view is the package
``orgmcp.observability``: ``events_view`` / ``events`` / ``follow_events`` / ``trace`` / ``metrics`` / ``now_view`` / ``check`` / ``render_*`` /
``observe_text`` below only ask it (through ``app.wire_observability``, over the ports of ``org.runtime`` in force at each call, so a test that
replaces the scheduler status or the clock of the runtime is seen), and the pure functions are its api. What stays here are the names the dashboard,
the command line and the MCP tool still import (``_scheduler_files``, ``_tail_events``, ``_head_event``, ``_running_ledger``, ``_run_logs``,
``Follower``, ``_plain``, ``_matcher``, ...) and ``register_observe_tool``, which stays until D-mcp. The default time of every view is the clock of
the runtime (``org.runtime.clock``).
"""

from __future__ import annotations

import time
from collections.abc import Callable, Iterator
from datetime import datetime
from pathlib import Path

from . import kernel as _kernel
from .app import wire_eventlog
from .app import wire_observability as _wired
from .core import Org
from .eventlog import ENVELOPE as _ENVELOPE
from .eventlog import EVENTS_REL, EventFollower, event_file
from .mail import MessageFile
from .observability import api as _api

EVENTS_DIR = EVENTS_REL
ERROR_WINDOW = _wired.ERROR_WINDOW
COPY_GRACE = _wired.COPY_GRACE
INFLIGHT_GRACE = _wired.INFLIGHT_GRACE
RECV_BOXES = _wired.RECV_BOXES
ENVELOPE = set(_ENVELOPE)
READ_ONLY_TOOLS = _wired.READ_ONLY_TOOLS
VIEWS = _wired.VIEWS

# ============================================================================================ the vocabulary (the package's)

fmt_dur = _kernel.fmt_dur
fmt_rel = _api.fmt_rel
percentile = _api.percentile
parse_when = _api.parse_when
normalize_refusal = _api.normalize_refusal
is_error = _api.is_error
format_event = _api.format_event
_clip = _kernel.clip_line
_ts = _kernel.parse_time
_plain = _wired.plain
_matcher = _wired.matcher

# ============================================================================================ the event log


def event_files(org: Org, since: datetime | None = None, until: datetime | None = None) -> list[Path]:
    """The event files that can hold events in ``[since, until]``: day directories first, then files by name
    (a file not written since ``since`` has nothing newer)."""
    return [f.path for f in org.runtime.event_reader.files(since, until)]


def timed_events(org: Org, since: datetime | None = None, until: datetime | None = None) -> Iterator[tuple[datetime, dict]]:
    """Events in ``[since, until]`` as (time, event), merged over all process files in time order (a heap merge:
    every file is time-ordered by its single writer)."""
    return org.runtime.event_reader.timed(since, until)


def iter_events(org: Org, since: datetime | None = None, until: datetime | None = None) -> Iterator[dict]:
    return org.runtime.event_reader.events(since, until)


def events_view(org: Org, since=None, until=None, agent: str | None = None, kind: str | None = None,
                trace: str | None = None, errors: bool = False, limit: int | None = None,
                now: datetime | None = None) -> dict:
    """The merged raw stream, filtered by time window first, then by fields (``EventQueries.events_view``)."""
    return _wired.event_queries_of(org.runtime).events_view(since, until, agent, kind, trace, errors, limit, now)


def events(org: Org, since=None, until=None, agent=None, kind=None, trace=None, errors=False, limit=None,
           now: datetime | None = None) -> list[dict]:
    """The matching events (the last ``limit`` of them), oldest first."""
    return _wired.event_queries_of(org.runtime).events(since, until, agent, kind, trace, errors, limit, now)


class Follower(EventFollower):
    """Tails the event files: ``poll()`` returns the complete new lines of all files (today's and yesterday's day
    directories) since the last call, in time order. Files that appear later (a new process) are read from the start.
    The tailing is ``eventlog``'s; this keeps the old signature and takes the time from the clock of the runtime."""

    def __init__(self, org: Org, match: Callable[[dict], bool] | None = None, now: datetime | None = None):
        self.org, self.match = org, match or (lambda ev: True)
        self._follower = org.runtime.event_followers.follow(self.match, now or org.runtime.clock.now())

    def poll(self, emit: bool = True, now: datetime | None = None) -> list[dict]:
        return self._follower.poll(emit, now or self.org.runtime.clock.now())


def follow_events(org: Org, agent=None, kind=None, trace=None, errors=False, poll: float = 0.5,
                  sleep: Callable[[float], None] = time.sleep, max_polls: int | None = None) -> Iterator[dict]:
    """Yield new matching events as they are written (polling). Stops after ``max_polls`` polls if given."""
    return _wired.event_queries_sleeping(org.runtime, sleep).follow(agent, kind, trace, errors, poll, max_polls)


# ============================================================================================ message files


FileRec = MessageFile  # a message file as the index of the mail package sees it (data)
Msg = _wired.Msg
build_messages = _wired.build_messages


def scan_messages(org: Org) -> list[FileRec]:
    """Every message file of every mailbox of root and the live agents, parsed once (cached by path + mtime)."""
    return org.runtime.message_index.scan()


def Traces(org: Org, msgs: dict, batches: dict[str, list[str]] | None = None):  # noqa: N802 - it was the class of the trace of every message
    """The trace of every message (``MessageTraceDeriver``): ``.of(message id)`` is ``(trace id or None, source)``."""
    return _wired.trace_derivers_of(org.runtime).derive(msgs, batches)


# ============================================================================================ runs


def _running_ledger(org: Org) -> dict[str, dict]:
    return org.runtime.run_registry.all()


RunRec = _wired.RunRec
run_events = _wired.run_events


def _run_logs(org: Org, agent: str) -> list[tuple[str, Path]]:
    return [(f.stem, f.path) for f in org.runtime.run_log_reader.files(agent)]


def collect_runs(org: Org, since: datetime | None, until: datetime | None, evs: dict[str, dict[str, dict]] | None = None,
                 agents: list[str] | None = None) -> list[RunRec]:
    """Every run that STARTED in ``[since, until]``: the run logs of the live agents (the file truth: one log = one
    run = one run of budget), completed with ``run.start/run.end`` events where there are some, plus runs known only
    from events (agents retired since). Oldest first."""
    return _wired.run_collection_of(org.runtime).collect(since, until, evs, agents)


# ============================================================================================ trace


def run_window(org: Org, task: Msg, result: Msg | None, root_tasks: list[Msg]) -> tuple[str, str | None]:
    """(start, end) of a root task's run window, as 21-character timestamps, exactly as ``progress`` counts runs."""
    return _wired.run_window(task, result, root_tasks)


def trace(org: Org, task_id: str, now: datetime | None = None) -> dict:
    """One request as a tree, in time order, with totals (``TraceQueries.trace``)."""
    return _wired.trace_queries_of(org.runtime).trace(task_id, now)


# ============================================================================================ metrics


def metrics(org: Org, since="24h", by: str | None = None, now: datetime | None = None, agent: str | None = None) -> dict:
    """Counts, rates and percentiles over ``[since, now]`` (``MetricQueries.metrics``)."""
    return _wired.metric_queries_of(org.runtime).metrics(since, by, now, agent)


# ============================================================================================ the text of the views


def render_events(view: dict, max_lines: int | None = None) -> str:
    return _wired.system_renderer().render_events(view, max_lines)


def render_trace(tr: dict, max_lines: int | None = None) -> str:
    return _wired.system_renderer().render_trace(tr, max_lines)


def render_metrics(m: dict, limit: int = 50) -> str:
    return _wired.system_renderer().render_metrics(m, limit)


# ============================================================================================ now


def _tail_events(path: Path, nbytes: int = 65536) -> list[dict]:
    return wire_eventlog.system_reader().tail(event_file(path), nbytes)


def _scheduler_files(org: Org) -> list[tuple[int, int, Path]]:
    """(start_epoch_ms, pid, path) of every scheduler event file, newest process first."""
    out = [(f.start_ms, f.pid, f.path) for f in org.runtime.event_reader.files() if f.proc == "scheduler"]
    return sorted(out, key=lambda x: (x[0], str(x[2])), reverse=True)


def _head_event(path: Path) -> dict | None:
    return wire_eventlog.system_reader().head(event_file(path))


def now_view(org: Org, now: datetime | None = None) -> dict:
    """What is happening right now. Works with no events (then the event-derived parts are empty) (``NowQueries.now_view``)."""
    return _wired.now_queries_of(org.runtime).now_view(now)


def render_now(v: dict, max_lines: int | None = None) -> str:
    return _wired.system_renderer().render_now(v, max_lines)


# ============================================================================================ check


def check(org: Org, now: datetime | None = None) -> dict:
    """The invariants of the runtime, each PASS/FAIL with details (read-only) (``IntegrityChecks.check``)."""
    return _wired.integrity_checks_of(org.runtime).check(now)


def render_check(res: dict) -> str:
    return _wired.system_renderer().render_check(res)


# ============================================================================================ entry points


def observe_text(org: Org, view: str = "now", target: str | None = None, since: str = "24h", by: str | None = None,
                 errors_only: bool = False, limit: int = 50, now: datetime | None = None, max_lines: int | None = None) -> str:
    """The text of one view. ``target``: the task id for ``trace``; for ``events`` a trace id, an agent address or an
    event kind (``tool.call``, ``run``); for ``metrics`` an agent. ``limit``: events shown, rows per table (``ObservabilityText.observe_text``)."""
    return _wired.observe_text_of(org.runtime).observe_text(view, target, since, by, errors_only, limit, now, max_lines)


def register_observe_tool(mcp, binding) -> None:
    """Register the root-only, read-only MCP tool ``observe``."""

    @mcp.tool()
    def observe(view: str = "now", target: str | None = None, since: str = "24h", by: str | None = None,
                errors_only: bool = False, limit: int = 50) -> str:
        """Read-only look at how the organization is running. view=
        "now": what runs, what is queued and why, what waits on you, errors of the last 15 min.
        "trace" (target=root task id): every message, run, tool call and refusal of one request, with time spent
        queued, running and waiting on you. "metrics" (since=15m|24h|7d|ISO, by=agent|tool|service|trace): runs,
        failures, refusal rates, latency percentiles, budget spent. "events" (target=agent, trace id or kind,
        errors_only): the raw record. "check": is the runtime consistent (budget, messages, stuck runs)?"""
        return observe_text(binding.get(), view, target, since, by, errors_only, limit)
