"""In-memory fake of the ``runs`` ports, and the registry the contract suites iterate over.

``MemoryRuns`` is the log writer, the log reader and the registry at once: logs are byte strings with an mtime, time is the ``Clock`` it
was given (a ``FakeClock``: it moves only when told). It obeys the same contract suites as the filesystem implementations
(``tests/test_contract_*.py``), so a consumer's unit test may use it instead of an organization on disk.
"""

from __future__ import annotations

import os
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, replace
from pathlib import Path

from ..kernel import Clock, JsonObject, OrgPaths
from ..kernel.testing import FakeClock, fs_ledger_store
from ._caching import CachingRunLogReader, FsDirectoryStamps
from ._reader import FsRunLogReader
from ._registry import FsRunRegistry
from ._writer import FsRunLogWriter
from .api import RunLogFile, RunLogReader, RunLogSink, RunLogWriter, RunOutcomes, RunRegistry, RunWindow


class MemoryRuns(RunLogWriter, RunLogReader, RunRegistry):
    """Run logs and the registry kept in memory. An agent's directory exists once ``add_agent`` said so (``create`` needs it)."""

    def __init__(self, clock: Clock | None = None, root: Path = Path("/org")) -> None:
        raise NotImplementedError("red: A-runs")

    def add_agent(self, addr: str) -> None:
        raise NotImplementedError("red: A-runs")

    def put_log(self, addr: str, name: str, content: str | bytes) -> Path:
        raise NotImplementedError("red: A-runs")

    def set_mtime(self, path: Path, epoch: float) -> None:
        raise NotImplementedError("red: A-runs")

    def read_log(self, path: Path) -> bytes | None:
        raise NotImplementedError("red: A-runs")

    def put_ledger(self, text: str) -> None:
        raise NotImplementedError("red: A-runs")

    def create(self, addr: str) -> Path:
        raise NotImplementedError("red: A-runs")

    def open_sink(self, path: Path) -> RunLogSink:
        raise NotImplementedError("red: A-runs")

    def append_note(self, rel_path: str, text: str) -> None:
        raise NotImplementedError("red: A-runs")

    def count(self, addr: str) -> int:
        raise NotImplementedError("red: A-runs")

    def files(self, addr: str) -> list[RunLogFile]:
        raise NotImplementedError("red: A-runs")

    def windows(self, addr: str) -> list[RunWindow]:
        raise NotImplementedError("red: A-runs")

    def outcomes(self, addr: str) -> RunOutcomes:
        raise NotImplementedError("red: A-runs")

    def last_end(self, addr: str) -> float:
        raise NotImplementedError("red: A-runs")

    def facts(self, path: Path) -> JsonObject:
        raise NotImplementedError("red: A-runs")

    def tail(self, path: Path, max_bytes: int, max_lines: int) -> tuple[str, bool]:
        raise NotImplementedError("red: A-runs")

    def head(self, path: Path, max_bytes: int) -> str:
        raise NotImplementedError("red: A-runs")

    def all(self) -> dict[str, JsonObject]:
        raise NotImplementedError("red: A-runs")

    def record(self, addr: str, record: JsonObject) -> None:
        raise NotImplementedError("red: A-runs")

    def forget(self, *addrs: str) -> None:
        raise NotImplementedError("red: A-runs")

    def replace(self, records: Mapping[str, JsonObject]) -> None:
        raise NotImplementedError("red: A-runs")


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
