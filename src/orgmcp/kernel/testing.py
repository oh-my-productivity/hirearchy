"""In-memory fakes of the kernel's ports, and the registry the contract suites iterate over.

A fake passes the same contract suite as the real adapter (``tests/test_contract_*.py``), so a consumer's unit test may
use it instead of the filesystem, the system clock or the process environment.
"""

from __future__ import annotations

import json
import os
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

from ._paths import OrgPaths
from ._ports import AtomicWriter, Clock, Environment, EventSink, IdGenerator, JsonObject, LedgerStore, TokenSource, TraceTap
from ._system import FsAtomicWriter, FsLedgerStore, OsEnvironment, SecretsTokens, SystemClock, TimestampIdGenerator
from ._timeutil import STAMP_FORMAT

T0 = datetime(2026, 10, 18, 10, 0, 0, tzinfo=timezone.utc)


class FakeClock(Clock):
    """Time moves only when told (``advance``, ``sleep``, ``at``), plus one microsecond per ``now()`` so that ids stay
    unique and ordered."""

    def __init__(self, start: datetime = T0) -> None:
        self.t = start
        self.origin = start

    def now(self) -> datetime:
        self.t += timedelta(microseconds=1)
        return self.t

    def time(self) -> float:
        return self.t.timestamp()

    def monotonic(self) -> float:
        return (self.t - self.origin).total_seconds()

    def sleep(self, seconds: float) -> None:
        self.advance(seconds)

    def advance(self, seconds: float) -> None:
        """Move time forward."""
        self.t += timedelta(seconds=seconds)

    def at(self, offset_s: float) -> datetime:
        """Jump to ``start + offset_s`` seconds (never backwards)."""
        target = self.origin + timedelta(seconds=offset_s)
        if target > self.t:
            self.t = target
        return self.t


class SequenceIdGenerator(IdGenerator):
    """Ids with the real format whose last part counts ``0000``, ``0001`` ... instead of being random."""

    def __init__(self, clock: Clock) -> None:
        self._clock = clock
        self._count = 0

    def message_id(self, sender: str) -> str:
        n = self._count
        self._count = (n + 1) % 0x10000  # four hex digits, like the random part of a real id
        return f"{self._clock.now():{STAMP_FORMAT}}-{sender.replace('/', '.')}-{n:04x}"


class CounterTokens(TokenSource):
    """Tokens that count ``start``, ``start + 1`` ... instead of being random (so the ids of messages are the same in every run).

    One counter for every length by default - the ids and the temp names of the atomic writes number off the same sequence, as the scenarios
    that patched ``core.secrets`` had it; ``per_length`` keeps a counter for each byte length (what the golden suite had), so that a write does not
    move the ids. ``counts`` is how many tokens were made, by byte length."""

    def __init__(self, per_length: bool = False, start: int = 0) -> None:
        self._per_length = per_length
        self._start = start
        self.counts: dict[int, int] = {}
        self._made = 0

    def token_hex(self, nbytes: int) -> str:
        n = self._start + (self.counts.get(nbytes, 0) if self._per_length else self._made)
        self._made += 1
        self.counts[nbytes] = self.counts.get(nbytes, 0) + 1
        return f"{n:0{2 * nbytes}x}"


@dataclass
class RecordedEvent:
    kind: str
    actor: str | None
    run: str | None
    trace: str | None
    proc: str | None
    fields: dict[str, object] = field(default_factory=dict)


class ListEventSink(EventSink):
    def __init__(self) -> None:
        self.events: list[RecordedEvent] = []

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
        self.events.append(RecordedEvent(kind, actor, run, trace, proc, dict(fields)))


class RecordingTraceTap(TraceTap):
    def __init__(self) -> None:
        self.notes: list[str | None] = []

    def note(self, trace: str | None) -> None:
        self.notes.append(trace)


class MemoryAtomicWriter(AtomicWriter):
    def __init__(self) -> None:
        self.files: dict[Path, str] = {}

    def write(self, path: Path, text: str) -> None:
        self.files[path] = text


class RecordingAtomicWriter(AtomicWriter):
    """Writes nothing; tells ``on_write(path, text)`` what it was asked to write, in order (a test that only needs to see the writes)."""

    def __init__(self, on_write: Callable[[Path, str], None]) -> None:
        self._on_write = on_write

    def write(self, path: Path, text: str) -> None:
        self._on_write(path, text)


class FailingAtomicWriter(AtomicWriter):
    """Fails like a full disk for the paths ``fails`` selects (all by default); writes the others through ``inner``."""

    def __init__(
        self,
        inner: AtomicWriter,
        fails: Callable[[Path], bool] = lambda path: True,
        error: OSError | None = None,
    ) -> None:
        self._inner = inner
        self._fails = fails
        self._error = error or OSError(28, "No space left on device")
        self.attempts: list[Path] = []

    def write(self, path: Path, text: str) -> None:
        self.attempts.append(path)
        if self._fails(path):
            raise self._error
        self._inner.write(path, text)


class MemoryLedgerStore(LedgerStore):
    """Ledgers kept as the JSON text the real store would put in ``.runtime/<name>.json``."""

    def __init__(self) -> None:
        self.texts: dict[str, str] = {}

    def read(self, name: str) -> JsonObject:
        try:
            data = json.loads(self.texts[name])
        except (KeyError, ValueError):
            return {}
        return data if isinstance(data, dict) else {}

    def write(self, name: str, data: JsonObject) -> None:
        self.texts[name] = json.dumps(data, indent=2) + "\n"


class DictEnvironment(Environment):
    def __init__(
        self,
        variables: Mapping[str, str] | None = None,
        cwd: Path = Path("/work"),
        home: Path = Path("/home/user"),
    ) -> None:
        self._variables = dict(variables or {})
        self._cwd = cwd
        self._home = home

    def set(self, name: str, value: str) -> None:
        """Define a variable."""
        self._variables[name] = value

    def get(self, name: str) -> str | None:
        return self._variables.get(name)

    def cwd(self) -> Path:
        return self._cwd

    def home(self) -> Path:
        return self._home

    def variables(self) -> Mapping[str, str]:
        return dict(self._variables)


# ------------------------------------------------------------------------------ harnesses and the registry


@dataclass(frozen=True)
class WriterHarness:
    writer: AtomicWriter
    base: Path  # a directory the writer may write below
    read: Callable[[Path], str | None]  # the text last written to a path, None when nothing was


@dataclass(frozen=True)
class LedgerHarness:
    store: LedgerStore
    put_raw: Callable[[str, str], None]  # put arbitrary file text in a ledger (to test unreadable ones)


@dataclass(frozen=True)
class EnvHarness:
    env: Environment
    put: Callable[[str, str], None]  # define a variable
    close: Callable[[], None]  # undo every ``put``


def system_clock(tmp_path: Path) -> Clock:
    return SystemClock()


def fake_clock(tmp_path: Path) -> Clock:
    return FakeClock()


def timestamp_id_generator(tmp_path: Path) -> IdGenerator:
    return TimestampIdGenerator(SystemClock())


def sequence_id_generator(tmp_path: Path) -> IdGenerator:
    return SequenceIdGenerator(FakeClock())


def secrets_tokens(tmp_path: Path) -> TokenSource:
    return SecretsTokens()


def counter_tokens(tmp_path: Path) -> TokenSource:
    return CounterTokens()


def list_event_sink(tmp_path: Path) -> EventSink:
    return ListEventSink()


def recording_trace_tap(tmp_path: Path) -> TraceTap:
    return RecordingTraceTap()


def _read_file(path: Path) -> str | None:
    return path.read_bytes().decode("utf-8") if path.is_file() else None


def fs_atomic_writer(tmp_path: Path) -> WriterHarness:
    return WriterHarness(FsAtomicWriter(), tmp_path, _read_file)


def memory_atomic_writer(tmp_path: Path) -> WriterHarness:
    writer = MemoryAtomicWriter()
    return WriterHarness(writer, tmp_path, writer.files.get)


def fs_ledger_store(tmp_path: Path) -> LedgerHarness:
    paths = OrgPaths(tmp_path)

    def put_raw(name: str, raw: str) -> None:
        paths.runtime_dir().mkdir(parents=True, exist_ok=True)
        paths.ledger_file(name).write_text(raw, encoding="utf-8")

    return LedgerHarness(FsLedgerStore(paths, FsAtomicWriter()), put_raw)


def memory_ledger_store(tmp_path: Path) -> LedgerHarness:
    store = MemoryLedgerStore()
    return LedgerHarness(store, store.texts.__setitem__)


def os_environment(tmp_path: Path) -> EnvHarness:
    before: dict[str, str | None] = {}

    def put(name: str, value: str) -> None:
        before.setdefault(name, os.environ.get(name))
        os.environ[name] = value

    def close() -> None:
        for name, old in before.items():
            if old is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = old

    return EnvHarness(OsEnvironment(), put, close)


def dict_environment(tmp_path: Path) -> EnvHarness:
    env = DictEnvironment()
    return EnvHarness(env, env.set, lambda: None)


IMPLEMENTATIONS: Mapping[type, Sequence[Callable[[Path], object]]] = {
    Clock: [system_clock, fake_clock],
    IdGenerator: [timestamp_id_generator, sequence_id_generator],
    TokenSource: [secrets_tokens, counter_tokens],
    EventSink: [list_event_sink],
    TraceTap: [recording_trace_tap],
    AtomicWriter: [fs_atomic_writer, memory_atomic_writer],
    LedgerStore: [fs_ledger_store, memory_ledger_store],
    Environment: [os_environment, dict_environment],
}
