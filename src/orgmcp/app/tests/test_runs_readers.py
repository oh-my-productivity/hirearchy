"""The legacy readers of run logs (health, observe, the dashboard) and the scheduler's records go through the ports of the runtime.

The behaviour they have is covered by their own tests (``test_health``, ``test_observe``, ``test_dashboard_data``, ``test_wakes``,
``test_scheduler``); here each one is shown to ask the ports (a fake that is not on disk answers) and, for the dashboard's tail, to
read a log exactly as the function it replaces did (frozen in ``orgmcp.runs.tests._oracle``).
"""

from __future__ import annotations

import dataclasses
import os
import random
import sys
import time
from collections.abc import Callable, Iterator
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest

from orgmcp.app import Org, wire_dashdata
from orgmcp.dashdata._runlog import read_tail
from orgmcp.kernel import OrgPaths
from orgmcp.runs import RunLogReader, RunLogSink, log_failed_start
from orgmcp.runs._reader import FsRunLogReader
from orgmcp.runs._writer import FsRunLogWriter
from orgmcp.runs.testing import MemoryRuns
from orgmcp.runs.tests import _oracle
from orgmcp.runs.tests._legacy import legacy
from orgmcp.scheduler._orphans import LogRunNotes
from testkit.health_world import Scheduler

health, observe = legacy("health"), legacy("observe")

T1, T2, T3 = "20261018T100000000001", "20261018T110000000002", "20261018T120000000003"


@pytest.fixture
def org(tmp_path: Path) -> Org:
    made = Org.init(tmp_path / "org", "mission", {"poll_seconds": 0.05})
    made.hire("root", "ceo", "Chief", "Run it.", can_hire=True, max_children=2)
    return made


@pytest.fixture
def memory(org: Org) -> MemoryRuns:
    fake = MemoryRuns(root=org.root)
    fake.add_agent("ceo")
    return fake


def use(org: Org, **ports: Any) -> None:
    org.runtime = dataclasses.replace(org.runtime, **ports)


# ----------------------------------------------------------------------------------------------------------------- health


def test_health_reads_the_windows_and_outcomes_from_the_log_reader(org: Org, memory: MemoryRuns) -> None:
    memory.put_log("ceo", f"{T1}.log", "# run of ceo, 1 message(s)\n# senders: root\n# ---- prompt ----\nx\n# ---- output ----\n\n# exit 0 after 3s\n")
    memory.put_log("ceo", f"{T2}.log", "# run of ceo, 1 message(s)\n# senders: root\n# ---- prompt ----\nx\n# ---- output ----\n\n# exit 1 after 3s\n")
    memory.put_log("ceo", f"{T3}.log", "# run of ceo, 1 message(s)\n# senders: runtime\n# ---- prompt ----\nx\n# ---- output ----\n\n# exit 0 after 3s\n")
    use(org, run_log_reader=memory)
    report = health.agent_health(org, "ceo", datetime(2026, 10, 18, 13, 0, tzinfo=timezone.utc))
    assert (report.runs_used, report.failed_runs, report.runtime_runs, report.empty_runs) == (3, 1, 1, 1)
    assert list((org.root / "ceo" / "runs").glob("*.log")) == []  # none on disk: the fake answered


# ----------------------------------------------------------------------------------------------------------------- observe


def test_observe_reads_the_registry_the_log_files_and_the_facts_from_the_ports(org: Org, memory: MemoryRuns) -> None:
    path = memory.put_log("ceo", f"{T1}.log", "# run of ceo, 1 message(s)\n\n# exit 3 after 7s\n")
    memory.record("ceo", {"pgid": 5, "lstart": "x", "started": 1.0, "scheduler": 1, "log": f"ceo/runs/{T1}.log"})
    use(org, run_log_reader=memory, run_registry=memory)
    assert observe._running_ledger(org) == {"ceo": {"pgid": 5, "lstart": "x", "started": 1.0, "scheduler": 1, "log": f"ceo/runs/{T1}.log"}}
    assert observe._run_logs(org, "ceo") == [(T1, path)]
    (run,) = observe.collect_runs(org, None, None, {}, ["ceo"])
    assert (run.run, run.outcome, run.exit_code, run.duration_ms) == (f"ceo@{T1}", "failed", 3, 7000.0)


def test_observe_finds_a_start_that_failed_through_the_reader(org: Org, memory: MemoryRuns) -> None:
    path = memory.put_log("ceo", f"{T1}.log", "# run of ceo, 1 message(s)\n" + log_failed_start("no kiro"))
    use(org, run_log_reader=memory)
    (run,) = observe.collect_runs(org, None, None, {}, ["ceo"])
    assert run.outcome == "failed" and run.log == path and run.exit_code is None


# --------------------------------------------------------------------------------------------------------------- scheduler


def a_task(org: Org) -> None:
    org.delegate("root", "ceo", "Ship it", "Ship the thing", "It is shipped", budget=6)


Runner = Callable[[Org, str, str], tuple[list[str], Path, dict[str, str]]]


def sleeper(seconds: str) -> Runner:
    def runner(org: Org, addr: str, prompt: str) -> tuple[list[str], Path, dict[str, str]]:
        return [sys.executable, "-c", f"import time; time.sleep({seconds})"], org.dir(addr), dict(os.environ)

    return runner


def test_a_run_in_flight_is_recorded_and_forgotten_through_the_registry(org: Org, memory: MemoryRuns) -> None:
    a_task(org)
    use(org, run_registry=memory)
    sched = Scheduler(org, sleeper("0.4"), echo=lambda _: None)
    sched.acquire()
    try:
        sched.tick()
        record = memory.all()["ceo"]
        run = sched.runs["ceo"]
        assert list(record) == ["pgid", "lstart", "started", "scheduler", "log"]
        assert record["pgid"] == run.proc.pid and record["scheduler"] == os.getpid() and record["started"] == run.started
        assert record["log"] == str(run.log.relative_to(org.root))
        assert not (org.root / ".runtime" / "running.json").exists() or (org.root / ".runtime" / "running.json").read_text() == "{}\n"
        deadline = time.time() + 20
        while sched.tick() and time.time() < deadline:
            time.sleep(0.02)
    finally:
        sched.release()
    assert memory.all() == {}


def test_orphans_of_a_dead_scheduler_are_settled_through_the_registry(org: Org, memory: MemoryRuns) -> None:
    memory.record("ceo", {"pgid": 4_000_000, "lstart": "x", "started": 0.0, "scheduler": 1, "log": ""})
    memory.record("gone/agent", {"pgid": 0})
    use(org, run_registry=memory)
    sched = Scheduler(org, sleeper("0"), echo=lambda _: None)
    sched.acquire()
    sched.release()
    assert memory.all() == {}


def test_the_note_on_an_orphaned_run_goes_through_the_log_writer(org: Org, memory: MemoryRuns) -> None:
    path = memory.put_log("ceo", f"{T1}.log", "# run of ceo, 1 message(s)\n")
    use(org, run_log_writer=memory)
    notes = LogRunNotes(org.runtime.run_log_writer)
    notes.note({"log": str(path.relative_to(org.root))}, "killed: orphaned run of a scheduler that died")
    notes.note({"pgid": 1}, "no log recorded: nothing to note")
    assert memory.read_log(path) == b"# run of ceo, 1 message(s)\n\n# killed: orphaned run of a scheduler that died\n"


def test_the_end_of_the_last_run_comes_from_the_log_reader(org: Org, memory: MemoryRuns) -> None:
    memory.set_mtime(memory.put_log("ceo", f"{T1}.log", ""), 1_800_000_000.0)
    use(org, run_log_reader=memory)
    assert org.runtime.run_log_reader.last_end("ceo") == 1_800_000_000.0


class SpyWriter(FsRunLogWriter):
    def __init__(self, inner: FsRunLogWriter) -> None:
        self.inner = inner
        self.opened: list[Path] = []

    def create(self, addr: str) -> Path:
        return self.inner.create(addr)

    def open_sink(self, path: Path) -> RunLogSink:
        self.opened.append(path)
        return self.inner.open_sink(path)

    def append_note(self, rel_path: str, text: str) -> None:
        self.inner.append_note(rel_path, text)


def test_the_scheduler_writes_its_logs_through_the_log_writer(org: Org) -> None:
    a_task(org)
    spy = SpyWriter(FsRunLogWriter(OrgPaths(org.root), org.runtime.clock))
    use(org, run_log_writer=spy)
    sched = Scheduler(org, sleeper("0"), echo=lambda _: None)
    sched.acquire()
    try:
        deadline = time.time() + 20
        while sched.tick() and time.time() < deadline:
            time.sleep(0.02)
    finally:
        sched.release()
    logs = sorted((org.root / "ceo" / "runs").glob("*.log"))
    assert logs and spy.opened == logs[: len(spy.opened)] and len(spy.opened) == len(logs)
    assert all(p.read_text(encoding="utf-8").startswith("# run of ceo, ") for p in logs)


# ------------------------------------------------------------------------------------------------- the tail of the dashboard


def tail_corpus() -> Iterator[tuple[str, bytes]]:
    rng = random.Random(7)
    ansi = "\x1b[31mred\x1b[0m text\r\x1b[2Kprogress 50%\rprogress 100%"
    yield "empty", b""
    yield "one line", b"hello\n"
    yield "no final newline", b"# run of ceo, 1 message(s)\nsome output"
    yield "blank lines", b"\n\n\nx\n\n\n"
    yield "only a newline", b"\n"
    yield "escape codes and carriage returns", (ansi + "\nplain\n" + ansi).encode()
    yield "last line is an escape code", b"output\n\x1b[0m"
    yield "last line is a control character", b"output\nmore\n\x07"
    yield "exactly 2000 lines", b"".join(b"line %d\n" % i for i in range(2000))
    yield "2001 lines", b"".join(b"line %d\n" % i for i in range(2001))
    yield "2001 lines, the last is an escape code", b"".join(b"line %d\n" % i for i in range(2000)) + b"\x1b[0m"
    yield "2002 lines", b"".join(b"line %d\n" % i for i in range(2002))
    yield "2003 lines", b"".join(b"line %d\n" % i for i in range(2003))
    yield "5000 lines", b"".join(b"line %d\n" % i for i in range(5000))
    yield "5000 lines without final newline", b"".join(b"line %d\n" % i for i in range(5000)) + b"partial"
    yield "undecodable", b"ok \xff\xfe\n" + b"x" * 100
    big = b"".join(b"%06d " % i + bytes(rng.choices(b"abcdefghij ", k=90)) + b"\n" for i in range(14_000))
    yield "over a megabyte", b"# run of ceo, 3 message(s)\n# senders: root, runtime\n" + big
    yield "over a megabyte, one huge line", b"y" * 1_500_000
    yield "header and footer", (
        b"# run of ceo, 2 message(s)\n# senders: root, runtime\n# cwd: /w\n# cmd: kiro <prompt on stdin>\n"
        b"# ---- prompt ----\np\n# ---- output ----\nout\n\n# exit 0 after 3s\n"
    )
    yield "failed start", b"# run of ceo, 1 message(s)\n# senders: root\n\n# failed to start: boom\n"
    yield "killed", b"# run of ceo, 1 message(s)\n\n# killed: the agent was retired during its run\n\n# exit -9 after 2s\n"


@pytest.mark.parametrize("name, content", list(tail_corpus()), ids=[name for name, _ in tail_corpus()])
@pytest.mark.parametrize("live", [False, True])
def test_the_tail_of_a_log_is_what_the_dashboard_always_showed(tmp_path: Path, name: str, content: bytes, live: bool) -> None:
    path = tmp_path / f"{T1}.log"
    path.write_bytes(content)
    reader = FsRunLogReader(OrgPaths(tmp_path))
    assert read_tail(reader, path, f"x/{path.name}", live) == _oracle.read_tail(path, f"x/{path.name}", live)


def test_the_tail_of_a_log_that_cannot_be_read_is_a_note(tmp_path: Path) -> None:
    path = tmp_path / f"{T1}.log"
    reader = FsRunLogReader(OrgPaths(tmp_path))
    got = read_tail(reader, path, "x/missing.log", False)
    assert got == _oracle.read_tail(path, "x/missing.log", False) and got.note == "the run log could not be read"


def test_the_tail_of_a_log_that_is_a_directory_is_a_note(tmp_path: Path) -> None:
    path = tmp_path / f"{T1}.log"
    path.mkdir()
    got = read_tail(FsRunLogReader(OrgPaths(tmp_path)), path, "x/dir.log", True)
    assert got == _oracle.read_tail(path, "x/dir.log", True)


class TailSpy(FsRunLogReader):
    def __init__(self, paths: OrgPaths) -> None:
        super().__init__(paths)
        self.tails: list[Path] = []

    def tail(self, path: Path, max_bytes: int, max_lines: int) -> tuple[str, bool]:
        self.tails.append(path)
        return super().tail(path, max_bytes, max_lines)


def test_the_dashboard_reads_the_tail_through_the_log_reader_of_the_runtime(org: Org) -> None:
    path = org.start_run_log("ceo")
    path.write_text("# run of ceo, 1 message(s)\n# senders: root\nthe output\n\n# exit 0 after 3s\n", encoding="utf-8")
    spy = TailSpy(OrgPaths(org.root))
    data = wire_dashdata.dashboard_runtime(org.root, overrides={RunLogReader: spy}).agent_detail_query
    got = data.run_log("ceo", False)
    assert spy.tails == [path] and got.path == path and got.lines[-1] == "# exit 0 after 3s" and got.header[-1] == "exit 0 after 3s"
