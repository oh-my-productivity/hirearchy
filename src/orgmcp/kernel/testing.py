"""In-memory fakes of the kernel's ports, and the registry the contract suites iterate over.

A fake passes the same contract suite as the real adapter (``tests/test_contract_*.py``), so a consumer's unit test may
use it instead of the filesystem, the system clock or the process environment.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from ._paths import OrgLayout, OrgPaths
from ._ports import AtomicWriter, Clock, Environment, EventSink, IdGenerator, JsonObject, LedgerStore, TraceTap
from ._system import FsAtomicWriter, FsLedgerStore, OsEnvironment, SystemClock, TimestampIdGenerator

T0 = datetime(2026, 10, 18, 10, 0, 0, tzinfo=timezone.utc)


class FakeClock(Clock):
    """Time moves only when told (``advance``, ``sleep``, ``at``), plus one microsecond per ``now()`` so that ids stay
    unique and ordered."""

    def __init__(self, start: datetime = T0) -> None:
        self.t = start
        self.origin = start

    def now(self) -> datetime:
        raise NotImplementedError("red: K1")

    def time(self) -> float:
        raise NotImplementedError("red: K1")

    def monotonic(self) -> float:
        raise NotImplementedError("red: K1")

    def sleep(self, seconds: float) -> None:
        raise NotImplementedError("red: K1")

    def advance(self, seconds: float) -> None:
        """Move time forward."""
        raise NotImplementedError("red: K1")

    def at(self, offset_s: float) -> datetime:
        """Jump to ``start + offset_s`` seconds (never backwards)."""
        raise NotImplementedError("red: K1")


class SequenceIdGenerator(IdGenerator):
    """Ids with the real format whose last part counts ``0000``, ``0001`` ... instead of being random."""

    def __init__(self, clock: Clock) -> None:
        self._clock = clock
        self._count = 0

    def message_id(self, sender: str) -> str:
        raise NotImplementedError("red: K1")


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
        raise NotImplementedError("red: K1")


class RecordingTraceTap(TraceTap):
    def __init__(self) -> None:
        self.notes: list[str | None] = []

    def note(self, trace: str | None) -> None:
        raise NotImplementedError("red: K1")


class MemoryAtomicWriter(AtomicWriter):
    def __init__(self) -> None:
        self.files: dict[Path, str] = {}

    def write(self, path: Path, text: str) -> None:
        raise NotImplementedError("red: K1")


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
        raise NotImplementedError("red: K1")


class MemoryLedgerStore(LedgerStore):
    """Ledgers kept as the JSON text the real store would put in ``.runtime/<name>.json``."""

    def __init__(self) -> None:
        self.texts: dict[str, str] = {}

    def read(self, name: str) -> JsonObject:
        raise NotImplementedError("red: K1")

    def write(self, name: str, data: JsonObject) -> None:
        raise NotImplementedError("red: K1")


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
        raise NotImplementedError("red: K1")

    def get(self, name: str) -> str | None:
        raise NotImplementedError("red: K1")

    def cwd(self) -> Path:
        raise NotImplementedError("red: K1")

    def home(self) -> Path:
        raise NotImplementedError("red: K1")

    def variables(self) -> Mapping[str, str]:
        raise NotImplementedError("red: K1")


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


def list_event_sink(tmp_path: Path) -> EventSink:
    return ListEventSink()


def recording_trace_tap(tmp_path: Path) -> TraceTap:
    return RecordingTraceTap()


def fs_atomic_writer(tmp_path: Path) -> WriterHarness:
    raise NotImplementedError("red: K1")


def memory_atomic_writer(tmp_path: Path) -> WriterHarness:
    raise NotImplementedError("red: K1")


def fs_ledger_store(tmp_path: Path) -> LedgerHarness:
    raise NotImplementedError("red: K1")


def memory_ledger_store(tmp_path: Path) -> LedgerHarness:
    raise NotImplementedError("red: K1")


def os_environment(tmp_path: Path) -> EnvHarness:
    raise NotImplementedError("red: K1")


def dict_environment(tmp_path: Path) -> EnvHarness:
    raise NotImplementedError("red: K1")


IMPLEMENTATIONS: Mapping[type, Sequence[Callable[[Path], object]]] = {
    Clock: [system_clock, fake_clock],
    IdGenerator: [timestamp_id_generator, sequence_id_generator],
    EventSink: [list_event_sink],
    TraceTap: [recording_trace_tap],
    AtomicWriter: [fs_atomic_writer, memory_atomic_writer],
    LedgerStore: [fs_ledger_store, memory_ledger_store],
    Environment: [os_environment, dict_environment],
}
