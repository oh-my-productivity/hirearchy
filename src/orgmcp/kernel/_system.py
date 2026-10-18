"""The real adapters of the kernel's ports: the system clock, ids, files, the process environment."""

from __future__ import annotations

import secrets
from collections.abc import Callable, Mapping
from datetime import datetime
from pathlib import Path

from ._paths import OrgLayout
from ._ports import AtomicWriter, Clock, Environment, IdGenerator, JsonObject, LedgerStore


class SystemClock(Clock):
    def now(self) -> datetime:
        raise NotImplementedError("red: K1")

    def time(self) -> float:
        raise NotImplementedError("red: K1")

    def monotonic(self) -> float:
        raise NotImplementedError("red: K1")

    def sleep(self, seconds: float) -> None:
        raise NotImplementedError("red: K1")


class TimestampIdGenerator(IdGenerator):
    def __init__(self, clock: Clock, token_hex: Callable[[int], str] = secrets.token_hex) -> None:
        self._clock = clock
        self._token_hex = token_hex

    def message_id(self, sender: str) -> str:
        raise NotImplementedError("red: K1")


class FsAtomicWriter(AtomicWriter):
    def __init__(self, token_hex: Callable[[int], str] = secrets.token_hex) -> None:
        self._token_hex = token_hex

    def write(self, path: Path, text: str) -> None:
        raise NotImplementedError("red: K1")


class FsLedgerStore(LedgerStore):
    def __init__(self, paths: OrgLayout, writer: AtomicWriter) -> None:
        self._paths = paths
        self._writer = writer

    def read(self, name: str) -> JsonObject:
        raise NotImplementedError("red: K1")

    def write(self, name: str, data: JsonObject) -> None:
        raise NotImplementedError("red: K1")


class OsEnvironment(Environment):
    def get(self, name: str) -> str | None:
        raise NotImplementedError("red: K1")

    def cwd(self) -> Path:
        raise NotImplementedError("red: K1")

    def home(self) -> Path:
        raise NotImplementedError("red: K1")

    def variables(self) -> Mapping[str, str]:
        raise NotImplementedError("red: K1")
