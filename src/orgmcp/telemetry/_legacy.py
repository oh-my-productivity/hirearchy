"""The old module-level functions of ``orgmcp.telemetry``, as thin adapters over the process defaults (``_process``).

Exported by ``__init__`` until step E3 (``LEGACY_EXPORTS``). ``datetime`` is imported here because the fixtures that fix the time of the
events replace ``orgmcp.telemetry.datetime`` (the composition root's event clock reads it).
"""

from __future__ import annotations

from contextlib import AbstractContextManager
from datetime import datetime
from pathlib import Path

from ..eventlog import DAY_RE, ENVELOPE, EVENTS_REL, LINE_MAX, PROCS, SCHEMA_VERSION
from ..kernel import TITLE_MAX, JsonObject, clip, single
from ._process import count_dropped, defaults
from ._summarize import JsonArgumentSummarizer

__all__ = [
    "DAY_RE", "ENVELOPE", "ERROR_MAX", "EVENTS_REL", "LINE_MAX", "PROCS", "SCHEMA_VERSION", "TITLE_MAX", "clip", "datetime", "dropped",
    "emit", "ensure_ignored", "note_trace", "process", "prune", "reset", "set_process", "single", "summarize_args", "traces_seen",
]

ERROR_MAX = 500  # the longest error text that goes into an event


def set_process(name: str) -> None:
    """Name this process for the ``proc`` field and the file name (``scheduler``, ``mcp`` or ``cli``)."""
    defaults().label().set(name)


def process() -> str:
    return defaults().label().get()


def dropped() -> int:
    """How many events this process could not write."""
    return defaults().drops().dropped()


def reset() -> None:
    """Forget open files and counters (tests; also what a fork child would need)."""
    defaults().reset()


def traces_seen() -> AbstractContextManager[list[str | None]]:
    """Collect the traces of the messages delivered (in this thread) while the block runs."""
    return defaults().channel().collect()


def note_trace(trace: str | None) -> None:
    defaults().channel().note(trace)


def ensure_ignored(root: str | Path) -> None:
    """Keep the events out of the organization's git snapshots (same mechanism as the other runtime files)."""
    try:
        defaults().ignore_list(Path(root)).ensure_runtime_files()
    except Exception:  # noqa: BLE001
        pass


def emit(root: str | Path, kind: str, /, *, actor: str | None = None, run: str | None = None,
         trace: str | None = None, proc: str | None = None, **fields: object) -> None:
    """Append one event to the log of the organization at ``root``. Never raises.

    ``actor``: who the event is for (default: ``$ORG_AGENT``; else ``runtime`` in the scheduler, ``root`` elsewhere).
    ``run``: the run id (default ``$ORG_RUN_ID``, which the scheduler gives to every agent process).
    """
    try:
        defaults().sink(root if isinstance(root, Path) else Path(root)).emit(kind, actor=actor, run=run, trace=trace, proc=proc, **fields)
    except Exception as exc:  # noqa: BLE001 - the sink never raises; the lookup of the sink might
        count_dropped(exc)


def summarize_args(arguments: dict[str, object]) -> JsonObject:
    """What a tool call put in its arguments, safe to log: ids, addresses, titles (clipped), statuses, budgets, paths,
    service names, verdicts, booleans and numbers as they are; any other text only as its length (``body_chars``);
    dicts as their keys (``inputs_keys``); other lists as their length (``acceptance_n``). Never a body."""
    return JsonArgumentSummarizer().summarize(arguments)


def prune(root: str | Path, keep_days: int, today: datetime | None = None) -> list[str]:
    """Delete day directories of the event log older than ``keep_days`` days (at least 1). Returns the removed names.
    Never raises."""
    try:
        return defaults().retention(Path(root)).prune(keep_days, today)
    except Exception as exc:  # noqa: BLE001 - the retention never raises; the lookup of it might
        count_dropped(exc)
        return []
