"""The sink of an organization: stamps an event with the envelope and appends it to the process's file for the day."""

from __future__ import annotations

import os
import threading
from collections.abc import Callable
from pathlib import Path

from ..eventlog import SCHEMA_VERSION
from ..kernel import Clock, Environment, EventSink, JsonObject, OrgLayout
from ..settings import EventSwitch
from ..snapshots import IgnoreList
from ._ports import DropLog, LineWriters
from .api import EventSinks, ProcessLabel

RETRY_AFTER = 5.0  # seconds before an unwritable events directory is tried again


class FsEventSink(EventSink):
    """Emission is cheap (one ``stat`` of ORG.md, one ``write``) and never raises: any failure is swallowed and counted.

    ``actor`` and ``run`` default to ``$ORG_AGENT`` / ``$ORG_RUN_ID`` as the environment is when the event is emitted (the scheduler gives
    every agent process its own); the process name is the label's, which is global to the process."""

    def __init__(
        self,
        layout: OrgLayout,
        writers: LineWriters,
        drops: DropLog,
        switch: EventSwitch,
        label: ProcessLabel,
        clock: Clock,
        environment: Environment,
        ignore: IgnoreList,
        retry_after: float = RETRY_AFTER,
    ) -> None:
        self._root = str(layout.root)
        self._writers = writers
        self._drops = drops
        self._switch = switch
        self._label = label
        self._clock = clock
        self._environment = environment
        self._ignore = ignore
        self._retry_after = retry_after

    def emit(
        self,
        kind: str,
        /,
        *,
        actor: str | None = None,
        run: str | None = None,
        trace: str | None = None,
        proc: str | None = None,
        **fields: object,
    ) -> None:
        try:
            self._emit(kind, actor, run, trace, proc or self._label.get(), fields)
        except Exception as exc:  # noqa: BLE001
            self._drops.drop(f"{type(exc).__name__}: {exc}")

    def _emit(self, kind: str, actor: str | None, run: str | None, trace: str | None, proc: str, fields: dict[str, object]) -> None:
        pid = os.getpid()
        writer = self._writers.writer(self._root, proc, pid)
        if not self._switch.enabled():
            return
        ts = self._clock.now().isoformat(timespec="microseconds")
        env = self._environment
        record: JsonObject = {
            "v": SCHEMA_VERSION, "ts": ts, "seq": 0, "proc": proc, "pid": pid, "kind": kind,
            "actor": actor or env.get("ORG_AGENT") or ("runtime" if proc == "scheduler" else "root"),
            "run": run or env.get("ORG_RUN_ID") or None,
            "trace": trace or None,
        }
        for name, value in fields.items():
            if name not in record:
                record[name] = value
        writer.append(record, ts[:10], self._clock, self._retry_after, self._keep_out_of_git)

    def _keep_out_of_git(self) -> None:
        """The events directory is new: keep the events out of the organization's git snapshots (like the other runtime files)."""
        try:
            self._ignore.ensure_runtime_files()
        except Exception:  # noqa: BLE001
            pass


class FsEventSinks(EventSinks):
    """The sink of each organization root, made by ``factory`` the first time it is asked for and kept."""

    def __init__(self, drops: DropLog, factory: Callable[[Path], EventSink]) -> None:
        self._drops = drops
        self._factory = factory
        self._lock = threading.Lock()
        self._sinks: dict[Path, EventSink] = {}

    def for_root(self, root: Path) -> EventSink:
        sink = self._sinks.get(root)
        if sink is None:
            with self._lock:
                sink = self._sinks.get(root)
                if sink is None:
                    sink = self._sinks[root] = self._factory(root)
        return sink

    def dropped(self) -> int:
        return self._drops.dropped()

    def reset(self) -> None:
        """Forget the sinks (and what they know of ORG.md)."""
        with self._lock:
            self._sinks.clear()
