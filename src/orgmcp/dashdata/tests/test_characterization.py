# mypy: ignore-errors
# A test moved from tests/ by tools/relocate_tests.py: untyped until it is converted. Delete the first line when this file is typed.

from __future__ import annotations

import os
import stat
import sys
import threading
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
import testkit
from testkit.dash_fixtures import DEMO_NOW, big_org, demo_org
from testkit.dashdata_world import dd
from testkit.legacy.orgmcp.app import wire_dashdata, wiring
from testkit.legacy.orgmcp.core import ROOT
from testkit.obs_fixtures import T0
from testkit.scheduler import scheduler_is

from orgmcp.daemon import SchedulerState
from orgmcp.kernel import BOXES, AtomicWriter, EventSink
from orgmcp.mail import MessageParser

EXPECTED = testkit.EXPECTED_DASH
BIG_NOW = T0 + timedelta(seconds=400)


@pytest.fixture(autouse=True)
def scheduler_up(monkeypatch: pytest.MonkeyPatch) -> None:
    scheduler_is(monkeypatch, SchedulerState("running", 7000, "2026-10-18 10:00:00Z"))


def golden(name: str, text: str, root: Path) -> None:
    assert text.replace(str(root), "<ROOT>") == (EXPECTED / f"{name}.txt").read_text(encoding="utf-8")


# ------------------------------------------------------------------------------------------ the text of dash --once
def test_once_of_the_demo_organization_is_what_it_always_was(tmp_path: Path) -> None:
    ns = demo_org(tmp_path)
    data = dd.DashData(ns.org.root, now=lambda: DEMO_NOW)
    golden("demo_110", dd.render_once(data), ns.org.root)
    golden("demo_60", dd.render_once(data, 60), ns.org.root)


def test_once_of_the_big_organization_is_what_it_always_was(tmp_path: Path) -> None:
    org = big_org(tmp_path, agents=50, messages=2000)
    golden("big_110", dd.render_once(dd.DashData(org.root, now=lambda: BIG_NOW)), org.root)


# ------------------------------------------------------------------------------------------ the caches, by counts
class CountingParser(MessageParser):
    """The parser of the runtime, counting the files it is asked to read."""

    def __init__(self, inner: MessageParser) -> None:
        self.inner = inner
        self.paths: list[Path] = []

    def parse(self, path: Path) -> Any:
        self.paths.append(path)
        return self.inner.parse(path)


def quiet(root: Path) -> None:
    """An organization that has existed for a while: its directories were not modified just now (the 2 s guard of the caches does not apply)."""
    old = datetime.now().timestamp() - 3600
    for dirpath, dirnames, _ in os.walk(root):
        for n in dirnames:
            os.utime(os.path.join(dirpath, n), (old, old))


def test_a_second_snapshot_reads_no_message_file(tmp_path: Path) -> None:
    org = big_org(tmp_path, agents=50, messages=2000)
    quiet(org.root)
    counting = CountingParser(wiring.open_runtime(org.root).message_parser)
    runtime = wire_dashdata.dashboard_runtime(org.root, lambda: BIG_NOW, overrides={MessageParser: counting})
    first = runtime.snapshot_query.snapshot()
    read_first = len(counting.paths)
    assert read_first > 1000  # the first snapshot did read the mailboxes
    second = runtime.snapshot_query.snapshot()
    assert len(counting.paths) == read_first
    assert second.agents.keys() == first.agents.keys() and {a: r.word for a, r in second.agents.items()} == {a: r.word for a, r in first.agents.items()}


def test_a_mailbox_that_changed_is_read_again_and_no_other(tmp_path: Path) -> None:
    org = big_org(tmp_path, agents=50, messages=2000)
    quiet(org.root)
    counting = CountingParser(wiring.open_runtime(org.root).message_parser)
    runtime = wire_dashdata.dashboard_runtime(org.root, lambda: BIG_NOW, overrides={MessageParser: counting})
    runtime.snapshot_query.snapshot()
    before = len(counting.paths)
    org.send(ROOT, "lead1", "new mail")
    runtime.snapshot_query.snapshot()
    read_again = counting.paths[before:]
    # the message is in the inbox of lead1 and in the sent box of root: those two directories, nothing else
    assert read_again and {p.parent.relative_to(org.root).as_posix() for p in read_again} <= {"lead1/inbox", "sent"}, read_again[:3]


def looked_at_directories(monkeypatch: pytest.MonkeyPatch, root: Path, by: str | None = None) -> Counter[str]:
    """Count the ``stat`` calls on the directories of the organization, by path (only those made by the module ``by``, when given)."""
    seen: Counter[str] = Counter()
    real = os.stat

    def counting(path: Any, *args: Any, **kwargs: Any) -> Any:
        result = real(path, *args, **kwargs)
        if isinstance(path, (str, os.PathLike)) and str(path).startswith(str(root)) and stat.S_ISDIR(result.st_mode):
            if by is None or sys._getframe(1).f_code.co_filename.endswith(by):
                seen[str(path)] += 1
        return result

    monkeypatch.setattr(os, "stat", counting)
    return seen


def test_each_mailbox_directory_is_looked_at_once_per_tick(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    org = big_org(tmp_path, agents=50, messages=2000)
    quiet(org.root)
    data = dd.DashData(org.root, now=lambda: BIG_NOW)
    data.snapshot()  # warm
    for tick in range(3):
        seen = looked_at_directories(monkeypatch, org.root, by="dashdata/_probe.py")
        data.snapshot()
        boxes = {p: n for p, n in seen.items() if Path(p).name in BOXES}
        assert len(boxes) >= 50 * 3, f"tick {tick} looked at {len(boxes)} mailbox directories"
        assert max(boxes.values()) == 1, {p: n for p, n in boxes.items() if n > 1}
        # nobody else asks the file system about a mailbox of an agent (the tree of the root lists its own directory, which is not a mailbox)
        everyone = looked_at_directories(monkeypatch, org.root)
        data.snapshot()
        agent_boxes = {p: n for p, n in everyone.items() if Path(p).name in BOXES and Path(p).parent != org.root}
        assert agent_boxes and max(agent_boxes.values()) == 1, {p: n for p, n in agent_boxes.items() if n > 1}


def test_the_probe_answers_from_its_memo_until_the_next_tick(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    org = big_org(tmp_path, agents=10, messages=40)
    probe = wire_dashdata.DirMtimeProbe(wiring.open_runtime(org.root).paths)
    seen = looked_at_directories(monkeypatch, org.root)
    first = probe.mtime("lead0", "inbox")
    assert [probe.mtime("lead0", "inbox") for _ in range(5)] == [first] * 5
    assert seen[str(org.root / "lead0" / "inbox")] == 1
    probe.tick()
    probe.mtime("lead0", "inbox")
    assert seen[str(org.root / "lead0" / "inbox")] == 2


# ------------------------------------------------------------------------------------------ read-only
class Raising(AtomicWriter, EventSink):
    """A writer and an event sink that must never be asked for anything."""

    def write(self, path: Path, text: str) -> None:
        raise AssertionError(f"the dashboard wrote {path}")

    def emit(self, kind: str, /, **fields: Any) -> None:
        raise AssertionError(f"the dashboard emitted {kind}")


def tree(root: Path) -> dict[str, tuple[int, int, bytes | None]]:
    """Every path under ``root`` with its size, its modification time (ns) and, for a file, its bytes."""
    out: dict[str, tuple[int, int, bytes | None]] = {}
    for dirpath, dirnames, filenames in os.walk(root):
        for name in [*dirnames, *filenames]:
            p = Path(dirpath) / name
            st = p.stat()
            out[str(p.relative_to(root))] = (st.st_size, st.st_mtime_ns, None if p.is_dir() else p.read_bytes())
    return out


def ask_everything(runtime: Any, report_task: str | None = None) -> None:
    snapshots, details, requests = runtime.snapshot_query, runtime.agent_detail_query, runtime.request_query
    snap = snapshots.snapshot()
    for addr in snap.order:
        details.agent_detail(addr, snap)
        details.agent_detail(addr, snap, True)
        details.run_log(addr, True)
        details.run_log(addr, False)
        for row in details.agent_detail(addr, snap).messages:
            details.message_text(row)
    requests.requests(snap)
    runtime.service_query.services(snap)
    runtime.service_query.service_detail("research", "market-brief")
    runtime.health_query.health(snap)
    runtime.health_query.run_check()
    runtime.snapshot_renderer.render_once(110)
    feed = runtime.event_feed_factory.create()
    feed.poll(DEMO_NOW)
    if report_task:
        requests.trace_text(report_task)
        requests.request_line(report_task)


def test_every_query_over_a_writer_and_a_sink_that_raise_writes_nothing(tmp_path: Path) -> None:
    ns = demo_org(tmp_path)
    before = tree(ns.org.root)
    both = Raising()
    runtime = wire_dashdata.dashboard_runtime(ns.org.root, lambda: DEMO_NOW, overrides={AtomicWriter: both, EventSink: both})
    ask_everything(runtime, ns.report_task.id)
    ask_everything(runtime, ns.report_task.id)  # warm: the cached paths too
    assert tree(ns.org.root) == before


def test_the_dashboard_runtime_of_a_big_organization_writes_nothing(tmp_path: Path) -> None:
    org = big_org(tmp_path, agents=20, messages=300)
    before = tree(org.root)
    both = Raising()
    runtime = wire_dashdata.dashboard_runtime(org.root, lambda: BIG_NOW, overrides={AtomicWriter: both, EventSink: both})
    ask_everything(runtime)
    assert tree(org.root) == before


# ------------------------------------------------------------------------------------------ one thread at a time
def test_the_data_of_a_dashboard_says_it_is_not_thread_safe() -> None:
    assert "not thread-safe" in (dd.DashData.__doc__ or "").lower()
    from orgmcp.dashdata._cache import DashCache

    assert "not thread-safe" in (DashCache.__doc__ or "").lower()


def test_refreshes_from_worker_threads_that_are_waited_for_one_at_a_time_agree_with_the_main_thread(tmp_path: Path) -> None:
    ns = demo_org(tmp_path)
    data = dd.DashData(ns.org.root, now=lambda: DEMO_NOW)
    expected = {a: r.word for a, r in data.snapshot().agents.items()}
    answers: list[dict[str, Any]] = []

    def refresh() -> None:
        answers.append({a: r.word for a, r in data.snapshot().agents.items()})

    for _ in range(3):  # what the Textual app does: one worker, joined before the next
        worker = threading.Thread(target=refresh)
        worker.start()
        worker.join()
    assert answers == [expected] * 3
