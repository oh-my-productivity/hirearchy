"""The real adapters of the kernel's ports: the system clock, ids, files, the process environment."""

from __future__ import annotations

import contextlib
import json
import os
import secrets
import time
from collections.abc import Callable, Mapping
from datetime import datetime, timezone
from pathlib import Path

from ._paths import OrgLayout
from ._ports import AtomicWriter, Clock, Environment, IdGenerator, JsonObject, LedgerStore, TokenSource
from ._timeutil import STAMP_FORMAT


class SystemClock(Clock):
    def now(self) -> datetime:
        return datetime.now(timezone.utc)

    def time(self) -> float:
        return time.time()

    def monotonic(self) -> float:
        return time.monotonic()

    def sleep(self, seconds: float) -> None:
        time.sleep(seconds)


class SecretsTokens(TokenSource):
    def token_hex(self, nbytes: int) -> str:
        return secrets.token_hex(nbytes)


class TimestampIdGenerator(IdGenerator):
    def __init__(self, clock: Clock, token_hex: Callable[[int], str] = secrets.token_hex) -> None:
        self._clock = clock
        self._token_hex = token_hex

    def message_id(self, sender: str) -> str:
        return f"{self._clock.now():{STAMP_FORMAT}}-{sender.replace('/', '.')}-{self._token_hex(2)}"


class FsAtomicWriter(AtomicWriter):
    def __init__(self, token_hex: Callable[[int], str] = secrets.token_hex) -> None:
        self._token_hex = token_hex

    def write(self, path: Path, text: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.parent / f".tmp-{self._token_hex(4)}-{path.name}"
        try:
            tmp.write_text(text, encoding="utf-8")
            os.replace(tmp, path)
        except BaseException:
            with contextlib.suppress(OSError):  # the original failure is the one to report
                tmp.unlink(missing_ok=True)
            raise


class FsLedgerStore(LedgerStore):
    def __init__(self, paths: OrgLayout, writer: AtomicWriter) -> None:
        self._paths = paths
        self._writer = writer

    def read(self, name: str) -> JsonObject:
        try:
            data = json.loads(self._paths.ledger_file(name).read_text(encoding="utf-8"))
        except (FileNotFoundError, ValueError):
            return {}
        return data if isinstance(data, dict) else {}

    def write(self, name: str, data: JsonObject) -> None:
        self._writer.write(self._paths.ledger_file(name), json.dumps(data, indent=2) + "\n")


class OsEnvironment(Environment):
    def get(self, name: str) -> str | None:
        return os.environ.get(name)

    def cwd(self) -> Path:
        return Path.cwd()

    def home(self) -> Path:
        return Path.home()

    def variables(self) -> Mapping[str, str]:
        return dict(os.environ)
