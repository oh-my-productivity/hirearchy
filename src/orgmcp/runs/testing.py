"""In-memory fake of the ``runs`` ports, and the registry the contract suites iterate over.

``MemoryRuns`` is the log writer, the log reader and the registry at once: logs are byte strings with an mtime, time is the ``Clock`` it
was given (a ``FakeClock``: it moves only when told). It obeys the same contract suites as the filesystem implementations
(``tests/test_contract_*.py``), so a consumer's unit test may use it instead of an organization on disk.
"""

from __future__ import annotations

import copy
import json
import os
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from pathlib import Path

from ..kernel import STAMP_FORMAT, Clock, JsonObject, OrgPaths, stamp_of
from ..kernel.testing import FakeClock, fs_ledger_store
from ._caching import CachingRunLogReader, FsDirectoryStamps
from ._format import FACTS_BYTES, HEAD_BYTES, TAIL_BYTES, cut_tail, is_failed, is_runtime_only, log_note, parse_facts
from ._reader import FsRunLogReader
from ._registry import FsRunRegistry
from ._writer import FsRunLogWriter
from .api import RunLogFile, RunLogReader, RunLogSink, RunLogWriter, RunOutcomes, RunRegistry, RunWindow


@dataclass
class _Log:
    data: bytearray
    mtime: float  # epoch seconds, as ``st_mtime``


class _MemorySink(RunLogSink):
    def __init__(self, runs: MemoryRuns, path: Path) -> None:
        self._runs = runs
        self._path = path
        self._closed = False

    @property
    def path(self) -> Path:
        return self._path

    def write(self, text: str) -> None:
        if self._closed:
            raise ValueError("I/O operation on closed file.")
        self._runs._append(self._path, text.encode("utf-8"))

    def flush(self) -> None:
        pass

    def close(self) -> None:
        self._closed = True


class MemoryRuns(RunLogWriter, RunLogReader, RunRegistry):
    """Run logs and the registry kept in memory. An agent's directory exists once ``add_agent`` said so (``create`` needs it)."""

    def __init__(self, clock: Clock | None = None, root: Path = Path("/org")) -> None:
        self._clock: Clock = clock or FakeClock()
        self._paths = OrgPaths(root)
        self._agents: set[Path] = {self._paths.root}  # the directories that exist: the organization's, and those of the agents added
        self._logs: dict[Path, _Log] = {}
        self._records: dict[str, object] = {}  # the content of running.json: whatever was put there

    # ------------------------------------------------------------------------------------------------------- setting up

    def add_agent(self, addr: str) -> None:
        """The directory of the agent exists."""
        self._agents.add(self._paths.agent_dir(addr))

    def put_log(self, addr: str, name: str, content: str | bytes) -> Path:
        """A log as the scheduler may have left it (any file name, hidden ones included), written now."""
        directory = self._paths.agent_dir(addr)
        self._agents.add(directory)
        path = directory / "runs" / name
        data = content.encode("utf-8") if isinstance(content, str) else content
        self._logs[path] = _Log(bytearray(data), self._clock.time())
        return path

    def set_mtime(self, path: Path, epoch: float) -> None:
        """When the log was last written."""
        self._logs[path].mtime = epoch

    def read_log(self, path: Path) -> bytes | None:
        """The content of a log, None when there is none."""
        log = self._logs.get(path)
        return None if log is None else bytes(log.data)

    def put_ledger(self, text: str) -> None:
        """The raw text of ``running.json`` (an unreadable one means no records)."""
        try:
            data = json.loads(text)
        except ValueError:
            data = {}
        self._records = data if isinstance(data, dict) else {}

    def _append(self, path: Path, data: bytes) -> None:
        log = self._logs.setdefault(path, _Log(bytearray(), 0.0))
        log.data += data
        log.mtime = self._clock.time()

    def _visible(self, addr: str) -> list[Path]:
        directory = self._paths.agent_dir(addr) / "runs"
        return sorted(p for p in self._logs if p.parent == directory and p.name.endswith(".log") and not p.name.startswith("."))

    # ---------------------------------------------------------------------------------------------------------- writer

    def create(self, addr: str) -> Path:
        directory = self._paths.agent_dir(addr)
        if directory not in self._agents:
            raise FileNotFoundError(f"no directory for {addr}: {directory}")
        path = directory / "runs" / f"{self._clock.now():{STAMP_FORMAT}}.log"
        log = self._logs.setdefault(path, _Log(bytearray(), 0.0))
        log.mtime = self._clock.time()  # like touch: an existing log keeps its content
        return path

    def open_sink(self, path: Path) -> RunLogSink:
        self._logs.setdefault(path, _Log(bytearray(), self._clock.time()))
        return _MemorySink(self, path)

    def append_note(self, rel_path: str, text: str) -> None:
        path = self._paths.root / rel_path
        if path in self._logs:
            self._append(path, log_note(text).encode("utf-8"))

    # ---------------------------------------------------------------------------------------------------------- reader

    def count(self, addr: str) -> int:
        return len(self._visible(addr))

    def files(self, addr: str) -> list[RunLogFile]:
        return [RunLogFile(p.stem, p, stamp_of(p.stem)) for p in self._visible(addr)]

    def windows(self, addr: str) -> list[RunWindow]:
        out = []
        for path in self._visible(addr):
            start = stamp_of(path.stem)
            if start:
                out.append(RunWindow(start, max(start, datetime.fromtimestamp(self._logs[path].mtime, timezone.utc))))
        return out

    def outcomes(self, addr: str) -> RunOutcomes:
        failed: set[datetime] = set()
        runtime_only: set[datetime] = set()
        for path in self._visible(addr):
            start = stamp_of(path.stem)
            if start is None:
                continue
            data = bytes(self._logs[path].data)
            if is_failed(data[max(0, len(data) - TAIL_BYTES):].decode("utf-8", "replace")):
                failed.add(start)
            if is_runtime_only(data[:HEAD_BYTES].decode("utf-8", "replace")):
                runtime_only.add(start)
        return RunOutcomes(frozenset(failed), frozenset(runtime_only))

    def last_end(self, addr: str) -> float:
        directory = self._paths.agent_dir(addr) / "runs"
        return max((log.mtime for p, log in self._logs.items() if p.parent == directory and p.name.endswith(".log")), default=0.0)

    def facts(self, path: Path) -> JsonObject:
        log = self._logs.get(path)
        if log is None:
            return {}
        return parse_facts(bytes(log.data[max(0, len(log.data) - FACTS_BYTES):]).decode("utf-8", "replace"))

    def tail(self, path: Path, max_bytes: int, max_lines: int) -> tuple[str, bool]:
        data = self._existing(path)
        return cut_tail(data[max(0, len(data) - max_bytes):], len(data), max_lines)

    def head(self, path: Path, max_bytes: int) -> str:
        return self._existing(path)[:max_bytes].decode("utf-8", "replace")

    def _existing(self, path: Path) -> bytes:
        log = self._logs.get(path)
        if log is None:
            raise FileNotFoundError(f"no such log: {path}")
        return bytes(log.data)

    # -------------------------------------------------------------------------------------------------------- registry

    def all(self) -> dict[str, JsonObject]:
        return {k: copy.deepcopy(v) for k, v in self._records.items() if isinstance(v, dict)}

    def record(self, addr: str, record: JsonObject) -> None:
        records: dict[str, object] = dict(self.all())
        records[addr] = copy.deepcopy(record)
        self._records = records

    def forget(self, *addrs: str) -> None:
        records = self.all()
        if any(records.pop(a, None) is not None for a in addrs):  # stops at the first record found, like the scheduler always did
            self._records = dict(records)

    def replace(self, records: Mapping[str, JsonObject]) -> None:
        self._records = copy.deepcopy(dict(records))


# ------------------------------------------------------------------------------ harnesses and the registry


@dataclass(frozen=True)
class RunsHarness:
    """What a contract test needs of one implementation: the three ports, a clock it controls, and ways to put logs where they belong."""

    writer: RunLogWriter
    reader: RunLogReader
    registry: RunRegistry
    clock: FakeClock  # the one the writer stamps new logs with
    root: Path  # the organization directory (paths of logs are below it)
    add_agent: Callable[[str], None]  # the agent's directory exists
    put_log: Callable[[str, str, str | bytes], Path]  # (addr, file name, content): a log as the scheduler may have left it
    set_mtime: Callable[[Path, float], None]  # when the log was last written (epoch seconds)
    read_log: Callable[[Path], bytes | None]  # the content of a log, None when there is none
    put_ledger: Callable[[str], None]  # the raw text of running.json (to test unreadable ones)


def fs_runs(tmp_path: Path) -> RunsHarness:
    paths = OrgPaths(tmp_path)
    clock = FakeClock()
    ledgers = fs_ledger_store(tmp_path)

    def add_agent(addr: str) -> None:
        paths.agent_dir(addr).mkdir(parents=True, exist_ok=True)

    def put_log(addr: str, name: str, content: str | bytes) -> Path:
        directory = paths.agent_dir(addr) / "runs"
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / name
        path.write_bytes(content.encode("utf-8") if isinstance(content, str) else content)
        return path

    def set_mtime(path: Path, epoch: float) -> None:
        os.utime(path, (epoch, epoch))

    def read_log(path: Path) -> bytes | None:
        return path.read_bytes() if path.is_file() else None

    return RunsHarness(
        writer=FsRunLogWriter(paths, clock), reader=FsRunLogReader(paths), registry=FsRunRegistry(ledgers.store), clock=clock,
        root=tmp_path, add_agent=add_agent, put_log=put_log, set_mtime=set_mtime, read_log=read_log,
        put_ledger=lambda text: ledgers.put_raw("running", text),
    )


def caching_fs_runs(tmp_path: Path) -> RunsHarness:
    """The filesystem harness whose reader is the caching decorator (what the dashboard uses)."""
    plain = fs_runs(tmp_path)
    paths = OrgPaths(tmp_path)
    return replace(plain, reader=CachingRunLogReader(FsRunLogReader(paths), FsDirectoryStamps(paths), plain.clock))


def memory_runs(tmp_path: Path) -> RunsHarness:
    clock = FakeClock()
    memory = MemoryRuns(clock, tmp_path)
    return RunsHarness(
        writer=memory, reader=memory, registry=memory, clock=clock, root=tmp_path, add_agent=memory.add_agent, put_log=memory.put_log,
        set_mtime=memory.set_mtime, read_log=memory.read_log, put_ledger=memory.put_ledger,
    )


IMPLEMENTATIONS: Mapping[type, Sequence[Callable[[Path], object]]] = {
    RunLogWriter: [fs_runs, memory_runs],
    RunLogSink: [fs_runs, memory_runs],
    RunLogReader: [fs_runs, memory_runs, caching_fs_runs],
    RunRegistry: [fs_runs, memory_runs],
}
