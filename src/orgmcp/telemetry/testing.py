"""In-memory fakes of the telemetry roles, the kit that builds a real sink over a temporary organization, and the registry the contract
suites iterate over.

A fake passes the same contract suite as the real class (``tests/test_contract_*.py``), so a consumer's unit test may use it instead of
an event log on disk. ``SinkKit`` is the real sink with every collaborator in the open (a fake clock, a dictionary environment, a fake
ignore list), which is what most unit tests of the package want.
"""

from __future__ import annotations

import json
import shutil
from collections.abc import Callable, Iterator, Mapping, Sequence
from contextlib import AbstractContextManager, contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

from ..eventlog import DAY_RE, EVENTS_REL, PROCS
from ..kernel import EventSink, JsonObject, OrgPaths, TraceTap
from ..kernel.testing import T0, DictEnvironment, FakeClock, ListEventSink, RecordedEvent, RecordingTraceTap
from ..settings import EventSwitch
from ..settings.testing import SwitchHarness, fs_event_switch
from ..snapshots.testing import MemoryIgnoreList
from ._label import MutableProcessLabel
from ._pool import EventWriterPool
from ._retention import FsEventRetention
from ._sink import FsEventSink, FsEventSinks
from ._summarize import JsonArgumentSummarizer
from ._trace_scope import ThreadLocalTraceScope
from .api import ArgumentSummarizer, EventRetention, EventSinks, ProcessLabel, TraceScope

PURE = {"ArgumentSummarizer"}  # a pure function of its argument: one implementation, no fake

ORG_MD = "---\nevents: true\n---\nrules\n"


# ------------------------------------------------------------------------------------------------------------- the fakes


class MemoryProcessLabel(ProcessLabel):
    """The name of a process, kept in a variable."""

    def __init__(self) -> None:
        raise NotImplementedError("red: the in-memory process label is not written yet")

    def get(self) -> str:
        return self._name

    def set(self, name: str) -> None:
        self._name = name if name in PROCS else "cli"


class _CountingSink(EventSink):
    """A recording sink that loses the events while its owner is ``broken``, and counts them."""

    recorder: ListEventSink
    _owner: MemoryEventSinks

    def __init__(self, owner: MemoryEventSinks) -> None:
        raise NotImplementedError("red: the in-memory sinks are not written yet")

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
        if self._owner.broken:
            self._owner.lost += 1
        else:
            self.recorder.emit(kind, actor=actor, run=run, trace=trace, proc=proc, **fields)


class MemoryEventSinks(EventSinks):
    """One recording sink per root; ``broken=True`` makes every emission fail the way a full disk does (counted, never raised)."""

    sinks: dict[Path, _CountingSink]
    broken: bool
    lost: int

    def __init__(self) -> None:
        raise NotImplementedError("red: the in-memory sinks are not written yet")

    def for_root(self, root: Path) -> EventSink:
        return self.sinks.setdefault(root, _CountingSink(self))

    def dropped(self) -> int:
        return self.lost

    def events(self, root: Path) -> list[RecordedEvent]:
        """What was emitted for ``root``."""
        sink = self.sinks.get(root)
        return list(sink.recorder.events) if sink else []


class MemoryEventRetention(EventRetention):
    """The day directories of an event log as a set of names, and other names that are not days."""

    days: set[str]
    others: set[str]
    _clock: FakeClock

    def __init__(self, clock: FakeClock | None = None, days: Sequence[str] = (), others: Sequence[str] = ()) -> None:
        raise NotImplementedError("red: the in-memory retention is not written yet")

    def prune(self, keep_days: int, today: datetime | None = None) -> list[str]:
        cutoff = ((today or self._clock.now()) - timedelta(days=max(1, int(keep_days)))).strftime("%Y-%m-%d")
        removed = sorted(d for d in self.days if DAY_RE.match(d) and d < cutoff)
        self.days -= set(removed)
        return removed


class StackTraceScope(TraceScope, TraceTap):
    """Collects like the real scope, without threads: one stack for the whole process."""

    _seen: list[list[str | None]]

    def __init__(self) -> None:
        raise NotImplementedError("red: the in-memory trace scope is not written yet")

    def collect(self) -> AbstractContextManager[list[str | None]]:
        return self._collect()

    @contextmanager
    def _collect(self) -> Iterator[list[str | None]]:
        seen: list[str | None] = []
        self._seen.append(seen)
        try:
            yield seen
        finally:
            self._seen.pop()

    def note(self, trace: str | None) -> None:
        if self._seen:
            self._seen[-1].append(trace)


# --------------------------------------------------------------------------------------------- the kit of a real sink


@dataclass(frozen=True)
class SinkKit:
    """A real ``FsEventSink`` over a temporary organization (``ORG.md`` with ``events: true``) and its collaborators."""

    sink: FsEventSink
    root: Path
    clock: FakeClock
    environment: DictEnvironment
    label: MutableProcessLabel
    pool: EventWriterPool
    ignore: MemoryIgnoreList
    org_md: SwitchHarness  # put / remove ORG.md
    retry_after: float
    files: Callable[[], list[Path]]  # every event file of the organization, by day then name
    events: Callable[[], list[JsonObject]]  # every event line of every file, parsed, in the order of the files
    sink_for_root: Callable[..., FsEventSink]  # another sink of the same organization over the same pool (a second runtime)


def build_sink(
    root: Path,
    pool: EventWriterPool,
    clock: FakeClock,
    environment: DictEnvironment,
    label: MutableProcessLabel,
    ignore: MemoryIgnoreList,
    switch: EventSwitch,
    retry_after: float,
) -> FsEventSink:
    return FsEventSink(OrgPaths(root), pool, pool, switch, label, clock, environment, ignore, retry_after)


def sink_kit(tmp_path: Path, org_md: str | None = ORG_MD, retry_after: float = 5.0, pool: EventWriterPool | None = None) -> SinkKit:
    """``tmp_path`` is the organization root; ``org_md=None``: there is no organization there (no ORG.md)."""
    clock, environment, label, ignore = FakeClock(), DictEnvironment(), MutableProcessLabel(), MemoryIgnoreList()
    pool = pool or EventWriterPool(clock)
    switch = fs_event_switch(tmp_path)
    if org_md is not None:
        switch.put(org_md)
    sink = build_sink(tmp_path, pool, clock, environment, label, ignore, switch.switch, retry_after)

    def files() -> list[Path]:
        return sorted((tmp_path / EVENTS_REL).glob("*/*.jsonl"))

    def events() -> list[JsonObject]:
        return [json.loads(line) for f in files() for line in f.read_text(encoding="utf-8").splitlines()]

    def sink_for_root(retry: float | None = None) -> FsEventSink:
        return build_sink(tmp_path, pool, clock, environment, label, ignore, switch.switch, retry_after if retry is None else retry)

    return SinkKit(sink, tmp_path, clock, environment, label, pool, ignore, switch, retry_after, files, events, sink_for_root)


# ------------------------------------------------------------------------------------------ harnesses and the registry


@dataclass(frozen=True)
class SinkHarness:
    sink: EventSink
    written: Callable[[], list[JsonObject]]  # what was emitted, in order: at least ``kind``, the free fields and what was given explicitly


@dataclass(frozen=True)
class SinksHarness:
    sinks: EventSinks
    root: Path
    other: Path  # the root of another organization
    written: Callable[[Path], list[JsonObject]]  # what was emitted for a root, in order (same shape as ``SinkHarness.written``)
    break_storage: Callable[[], None]  # from now on nothing can be written


@dataclass(frozen=True)
class RetentionHarness:
    retention: EventRetention
    days: Callable[[], list[str]]  # the day names that exist now, sorted
    others: Callable[[], list[str]]  # the entries that are not days
    put_day: Callable[[str], None]
    put_other: Callable[[str], None]
    today: datetime  # "now" of the clock the retention reads


def _given(event: RecordedEvent) -> JsonObject:
    out: JsonObject = {"kind": event.kind, **event.fields}
    out.update({name: value for name, value in (("actor", event.actor), ("run", event.run), ("trace", event.trace), ("proc", event.proc))
                if value is not None})
    return out


def fs_event_sink(tmp_path: Path) -> SinkHarness:
    kit = sink_kit(tmp_path)
    return SinkHarness(kit.sink, kit.events)


def list_event_sink(tmp_path: Path) -> SinkHarness:
    sink = ListEventSink()
    return SinkHarness(sink, lambda: [_given(e) for e in sink.events])


def fs_event_sinks(tmp_path: Path) -> SinksHarness:
    root, other = tmp_path / "one", tmp_path / "two"
    pool = EventWriterPool(FakeClock())
    root.mkdir()
    other.mkdir()
    kits = {root: sink_kit(root, pool=pool), other: sink_kit(other, pool=pool)}

    def factory(path: Path) -> EventSink:
        return kits[path].sink

    def break_storage() -> None:
        for kit in kits.values():
            shutil.rmtree(kit.root / ".runtime", ignore_errors=True)
            (kit.root / ".runtime").write_text("a file where the directory should be")

    sinks = FsEventSinks(pool, factory)
    return SinksHarness(sinks, root, other, lambda path: kits[path].events(), break_storage)


def memory_event_sinks(tmp_path: Path) -> SinksHarness:
    sinks = MemoryEventSinks()

    def break_storage() -> None:
        sinks.broken = True

    return SinksHarness(sinks, tmp_path / "one", tmp_path / "two", lambda path: [_given(e) for e in sinks.events(path)], break_storage)


def fs_process_label(tmp_path: Path) -> ProcessLabel:
    return MutableProcessLabel()


def memory_process_label(tmp_path: Path) -> ProcessLabel:
    return MemoryProcessLabel()


def fs_event_retention(tmp_path: Path) -> RetentionHarness:
    kit = sink_kit(tmp_path)
    base = tmp_path / EVENTS_REL
    retention = FsEventRetention(OrgPaths(tmp_path), kit.clock, kit.pool)

    def put_day(name: str) -> None:
        (base / name).mkdir(parents=True, exist_ok=True)
        (base / name / "mcp-1-1.jsonl").write_text("{}\n", encoding="utf-8")

    def put_other(name: str) -> None:
        (base / name).mkdir(parents=True, exist_ok=True)

    def entries(days: bool) -> list[str]:
        return sorted(p.name for p in base.iterdir() if bool(DAY_RE.match(p.name)) == days) if base.is_dir() else []

    return RetentionHarness(retention, lambda: entries(True), lambda: entries(False), put_day, put_other, T0)


def memory_event_retention(tmp_path: Path) -> RetentionHarness:
    clock = FakeClock()
    fake = MemoryEventRetention(clock)
    return RetentionHarness(fake, lambda: sorted(fake.days), lambda: sorted(fake.others), fake.days.add, fake.others.add, T0)


def thread_local_trace_scope(tmp_path: Path) -> ThreadLocalTraceScope:
    return ThreadLocalTraceScope()


def stack_trace_scope(tmp_path: Path) -> StackTraceScope:
    return StackTraceScope()


def recording_trace_tap(tmp_path: Path) -> RecordingTraceTap:
    return RecordingTraceTap()


def json_argument_summarizer(tmp_path: Path) -> ArgumentSummarizer:
    return JsonArgumentSummarizer()


IMPLEMENTATIONS: Mapping[type, Sequence[Callable[[Path], object]]] = {
    EventSink: [fs_event_sink, list_event_sink],
    EventSinks: [fs_event_sinks, memory_event_sinks],
    ProcessLabel: [fs_process_label, memory_process_label],
    EventRetention: [fs_event_retention, memory_event_retention],
    ArgumentSummarizer: [json_argument_summarizer],
    TraceScope: [thread_local_trace_scope, stack_trace_scope],
    TraceTap: [thread_local_trace_scope, recording_trace_tap],
}
