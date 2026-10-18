"""The event log: one append-only, structured record of what the runtime did (emission side).

Files: ``<org>/.runtime/events/<YYYY-MM-DD>/<proc>-<pid>-<start_epoch_ms>.jsonl``, one per process per UTC day, written
only by that process (so concurrent MCP servers and the scheduler never interleave). Readers glob and merge by ``ts``.
Every line is one JSON object: the envelope ``v, ts, seq, proc, pid, kind, actor, run, trace`` plus the fields of its kind.

Design rules:

* Emission is cheap: the process's file is opened once per day and kept open, a line is one ``write()`` on an
  ``O_APPEND`` descriptor (no buffering, no fsync), and the only per-event filesystem call is one ``stat`` of ORG.md
  (the ``events`` setting is re-read when that file changes).
* Emission NEVER raises: any failure (read-only or missing directory, full disk, a value that cannot be serialized)
  is swallowed and counted; the first one per process is reported on stderr.
* A line is at most 8 KB: longer ones are shrunk (``"truncated": true``). No message bodies, file contents or
  environment values are ever put in an event; ``summarize_args`` keeps only ids, names, paths and lengths.
* ``seq`` counts the lines of one file (it restarts at 1 in each day's file); a gap means a lost line.
"""

from __future__ import annotations

import json
import os
import shutil
import sys
import threading
import time
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .eventlog import DAY_RE, ENVELOPE, EVENTS_REL, LINE_MAX, PROCS, SCHEMA_VERSION  # noqa: F401 - the format, defined by eventlog

RETRY_AFTER = 5.0  # seconds before an unwritable events directory is tried again
TITLE_MAX = 80
ERROR_MAX = 500

_proc = "cli"  # which process this is, unless an emission names one
_lock = threading.Lock()
_writers: dict[tuple[str, str, int], "_Writer"] = {}
_dropped = 0
_warned = False
_tl = threading.local()


# ------------------------------------------------------------------------------------------------ small helpers


def clip(value: object, limit: int = TITLE_MAX) -> str:
    """``value`` as text of at most ``limit`` characters (an ellipsis marks a cut)."""
    text = value if isinstance(value, str) else str(value)
    return text if len(text) <= limit else text[: max(0, limit - 1)] + "…"


def set_process(name: str) -> None:
    """Name this process for the ``proc`` field and the file name (``scheduler``, ``mcp`` or ``cli``)."""
    global _proc
    _proc = name if name in PROCS else "cli"


def process() -> str:
    return _proc


def dropped() -> int:
    """How many events this process could not write."""
    return _dropped


def reset() -> None:
    """Forget open files and counters (tests; also what a fork child would need)."""
    global _dropped, _warned, _proc
    with _lock:
        for w in _writers.values():
            w.close()
        _writers.clear()
    _dropped, _warned, _proc = 0, False, "cli"


def _drop(exc: BaseException | str) -> None:
    global _dropped, _warned
    _dropped += 1
    if not _warned:
        _warned = True
        try:
            print(f"orgmcp: the event log is unavailable ({exc}); events are being dropped "
                  "(the operation itself is not affected)", file=sys.stderr, flush=True)
        except Exception:  # noqa: BLE001 - even a closed stderr must not matter
            pass


def _falsy(value: object) -> bool:
    if isinstance(value, str):
        return value.strip().lower() in ("false", "no", "off", "0")
    return value is False or (isinstance(value, int) and value == 0)


@contextmanager
def traces_seen():
    """Collect the traces of the messages delivered (in this thread) while the block runs."""
    previous = getattr(_tl, "seen", None)
    seen: list = []
    _tl.seen = seen
    try:
        yield seen
    finally:
        _tl.seen = previous


def note_trace(trace: str | None) -> None:
    seen = getattr(_tl, "seen", None)
    if seen is not None:
        seen.append(trace)


def single(traces) -> str | None:
    """The one distinct non-null trace of ``traces``, else None."""
    distinct = {t for t in traces if t}
    return next(iter(distinct)) if len(distinct) == 1 else None


# ------------------------------------------------------------------------------------------------------ writer


class _Writer:
    """The open file of one process (``proc``, ``pid``) for one organization."""

    def __init__(self, root: str, proc: str, pid: int):
        self.root, self.proc, self.pid = root, proc, pid
        self.stem = f"{proc}-{pid}-{int(time.time() * 1000)}"
        self.fd: int | None = None
        self.day = ""
        self.seq = 0
        self.retry_at = 0.0
        self.stamp: tuple | None = None  # (mtime_ns, size) of ORG.md the settings were read from
        self.enabled = True

    def close(self) -> None:
        if self.fd is not None:
            try:
                os.close(self.fd)
            except OSError:
                pass
        self.fd, self.day = None, ""

    def active(self) -> bool:
        """Is emission on for this organization? False when ORG.md is missing (no organization there: write nothing)
        or ``events: false``. Settings are re-read only when ORG.md changes."""
        try:
            st = os.stat(os.path.join(self.root, "ORG.md"))
        except OSError:
            return False
        stamp = (st.st_mtime_ns, st.st_size)
        if stamp != self.stamp:
            from .core import split_frontmatter  # late: core imports this module

            try:
                with open(os.path.join(self.root, "ORG.md"), encoding="utf-8") as f:
                    meta, _ = split_frontmatter(f.read())
                self.enabled = not _falsy(meta.get("events", True))
            except Exception:  # noqa: BLE001 - unreadable settings mean the default (on)
                self.enabled = True
            self.stamp = stamp
        return self.enabled

    def open(self, day: str) -> None:
        events = os.path.join(self.root, str(EVENTS_REL))
        fresh = not os.path.isdir(events)
        folder = os.path.join(events, day)
        os.makedirs(folder, exist_ok=True)
        if fresh:
            ensure_ignored(self.root)
        fd = os.open(os.path.join(folder, self.stem + ".jsonl"), os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
        self.close()
        self.fd, self.day, self.seq = fd, day, 0


def ensure_ignored(root: str | Path) -> None:
    """Keep the events out of the organization's git snapshots (same mechanism as the other runtime files)."""
    try:
        from .app.wiring import open_runtime  # late: the app package imports the facade, which imports this module

        open_runtime(Path(root)).ignore_list.ensure_runtime_files()
    except Exception:  # noqa: BLE001
        pass


# ------------------------------------------------------------------------------------------------------ emit


def emit(root: str | Path, kind: str, /, *, actor: str | None = None, run: str | None = None,
         trace: str | None = None, proc: str | None = None, **fields) -> None:
    """Append one event to the log of the organization at ``root``. Never raises.

    ``actor``: who the event is for (default: ``$ORG_AGENT``; else ``runtime`` in the scheduler, ``root`` elsewhere).
    ``run``: the run id (default ``$ORG_RUN_ID``, which the scheduler gives to every agent process).
    """
    try:
        _emit(str(root), kind, actor, run, trace, proc or _proc, fields)
    except Exception as exc:  # noqa: BLE001
        _drop(f"{type(exc).__name__}: {exc}")


def _emit(root: str, kind: str, actor, run, trace, proc: str, fields: dict) -> None:
    pid = os.getpid()
    key = (root, proc, pid)
    w = _writers.get(key)
    if w is None:
        with _lock:
            w = _writers.setdefault(key, _Writer(root, proc, pid))
    if not w.active():
        return
    ts = datetime.now(timezone.utc).isoformat(timespec="microseconds")
    env = os.environ
    record = {
        "v": SCHEMA_VERSION, "ts": ts, "seq": 0, "proc": proc, "pid": pid, "kind": kind,
        "actor": actor or env.get("ORG_AGENT") or ("runtime" if proc == "scheduler" else "root"),
        "run": run or env.get("ORG_RUN_ID") or None,
        "trace": trace or None,
    }
    for name, value in fields.items():
        if name not in record:
            record[name] = value
    with _lock:
        w.seq += 1
        record["seq"] = w.seq
        if w.fd is None or w.day != ts[:10]:
            if time.monotonic() < w.retry_at:
                raise OSError("events directory not writable (retrying later)")
            try:
                w.open(ts[:10])
            except OSError:
                w.close()
                w.retry_at = time.monotonic() + RETRY_AFTER
                raise
            record["seq"] = w.seq = 1
        data = _encode(record)
        try:
            os.write(w.fd, data)
        except OSError:
            w.close()
            w.retry_at = time.monotonic() + RETRY_AFTER
            raise


def _default(value: object) -> str:
    return str(value)


def _encode(record: dict) -> bytes:
    """One JSON line; shrunk to ``LINE_MAX`` bytes when it is longer (fields clipped, then dropped, ``truncated``)."""
    line = json.dumps(record, ensure_ascii=False, separators=(",", ":"), default=_default)
    data = line.encode("utf-8", "replace")
    if len(data) < LINE_MAX:
        return data + b"\n"
    for text_limit, items in ((300, 25), (60, 5)):
        record = {k: (v if k in ENVELOPE else _shrink(v, text_limit, items)) for k, v in record.items()}
        record["truncated"] = True
        data = json.dumps(record, ensure_ascii=False, separators=(",", ":"), default=_default).encode("utf-8", "replace")
        if len(data) < LINE_MAX:
            return data + b"\n"
    extra = sorted((k for k in record if k not in ENVELOPE and k != "truncated"),
                   key=lambda k: -len(json.dumps(record[k], default=_default)))
    for k in extra:
        del record[k]
        data = json.dumps(record, ensure_ascii=False, separators=(",", ":"), default=_default).encode("utf-8", "replace")
        if len(data) < LINE_MAX:
            break
    return data[: LINE_MAX - 1] + b"\n" if len(data) >= LINE_MAX else data + b"\n"


def _shrink(value, text_limit: int, items: int, depth: int = 0):
    if isinstance(value, str):
        return clip(value, text_limit)
    if depth > 4:
        return clip(value, text_limit)
    if isinstance(value, dict):
        return {str(k): _shrink(v, text_limit, items, depth + 1) for k, v in list(value.items())[:items]}
    if isinstance(value, (list, tuple, set)):
        return [_shrink(v, text_limit, items, depth + 1) for v in list(value)[:items]]
    return value


# ------------------------------------------------------------------------------------------------ arg summaries

# String arguments that are short identifiers (ids, addresses, names, paths, verdicts): kept, clipped.
_KEEP_STR = {
    "to": 200, "task_id": 200, "status": 40, "name": 80, "owner": 200, "service": 80, "verdict": 20, "report": 200,
    "agent": 200, "path": 300, "reply_to": 200, "revises": 200, "view": 40, "target": 200, "since": 80, "until": 80,
    "by": 40, "model": 80, "workspace": 300, "kind": 40, "plan_id": 80, "role": 80, "title": TITLE_MAX,
}
# Lists of short strings that are kept (paths, tool names).
_KEEP_LIST = {"inputs", "artifacts", "tools"}


def summarize_args(arguments: dict) -> dict:
    """What a tool call put in its arguments, safe to log: ids, addresses, titles (clipped), statuses, budgets, paths,
    service names, verdicts, booleans and numbers as they are; any other text only as its length (``body_chars``);
    dicts as their keys (``inputs_keys``); other lists as their length (``acceptance_n``). Never a body."""
    out: dict = {}
    for name, value in arguments.items():
        if value is None:
            continue  # an argument left at its default says nothing
        if isinstance(value, (bool, int, float)):
            out[name] = value
        elif isinstance(value, str):
            if name in _KEEP_STR:
                out[name] = clip(value, _KEEP_STR[name])
            else:
                out[f"{name}_chars"] = len(value)
        elif isinstance(value, dict):
            out[f"{name}_keys"] = [clip(k, 60) for k in list(value)[:20]]
        elif isinstance(value, (list, tuple)):
            if name in _KEEP_LIST and all(isinstance(v, str) for v in value):
                out[name] = [clip(v, 200) for v in value[:20]] + (["…"] if len(value) > 20 else [])
            else:
                out[f"{name}_n"] = len(value)
                chars = sum(len(v) for v in value if isinstance(v, str))
                if chars:
                    out[f"{name}_chars"] = chars
        else:
            out[f"{name}_type"] = type(value).__name__
    return out


# ------------------------------------------------------------------------------------------------- retention


def prune(root: str | Path, keep_days: int, today: datetime | None = None) -> list[str]:
    """Delete day directories of the event log older than ``keep_days`` days (at least 1). Returns the removed names.
    Never raises."""
    removed: list[str] = []
    try:
        base = Path(root) / EVENTS_REL
        cutoff = ((today or datetime.now(timezone.utc)) - timedelta(days=max(1, int(keep_days)))).strftime("%Y-%m-%d")
        for d in sorted(base.iterdir()) if base.is_dir() else []:
            if d.is_dir() and DAY_RE.match(d.name) and d.name < cutoff:
                shutil.rmtree(d, ignore_errors=True)
                if not d.exists():
                    removed.append(d.name)
    except Exception as exc:  # noqa: BLE001
        _drop(f"prune: {type(exc).__name__}: {exc}")
    return removed
