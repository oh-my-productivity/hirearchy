"""The primitive ports every feature may use: time, ids, events, atomic file writes, ledgers, the environment."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from datetime import datetime
from pathlib import Path
from typing import Protocol, TypeVar, runtime_checkable

T = TypeVar("T")

JsonObject = dict[str, object]
Provider = Callable[[], T]


@runtime_checkable
class Clock(Protocol):
    def now(self) -> datetime:
        """Aware UTC wall-clock time."""
        ...

    def time(self) -> float:
        """Epoch seconds."""
        ...

    def monotonic(self) -> float:
        """Monotonic seconds for waits and TTLs."""
        ...

    def sleep(self, seconds: float) -> None:
        """Block."""
        ...


@runtime_checkable
class IdGenerator(Protocol):
    def message_id(self, sender: str) -> str:
        """``<UTC %Y%m%dT%H%M%S%f>-<sender, / as .>-<4 hex>``; lexicographic order is creation order."""
        ...


@runtime_checkable
class EventSink(Protocol):
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
        """Append one event to the org's event log. Never raises."""
        ...


@runtime_checkable
class TraceTap(Protocol):
    def note(self, trace: str | None) -> None:
        """Tell the running tool call which trace a delivered message carries."""
        ...


@runtime_checkable
class AtomicWriter(Protocol):
    def write(self, path: Path, text: str) -> None:
        """Write via temp file + rename, creating parent directories."""
        ...


@runtime_checkable
class LedgerStore(Protocol):
    def read(self, name: str) -> JsonObject:
        """``.runtime/<name>.json``; ``{}`` when missing or unparsable."""
        ...

    def write(self, name: str, data: JsonObject) -> None:
        """Atomically replace the ledger."""
        ...


@runtime_checkable
class Environment(Protocol):
    def get(self, name: str) -> str | None:
        """An environment variable."""
        ...

    def cwd(self) -> Path:
        """Working directory."""
        ...

    def home(self) -> Path:
        """The user's home directory."""
        ...

    def variables(self) -> Mapping[str, str]:
        """A copy of the environment for child processes."""
        ...
