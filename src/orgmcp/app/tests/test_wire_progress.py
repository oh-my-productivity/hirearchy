"""``wire_progress``: the runtime has the reporter, built from the ports of the runtime."""

from __future__ import annotations

from pathlib import Path

from orgmcp.app import wiring
from orgmcp.attention import HumanQueue, WaitingOnUser
from orgmcp.attention.testing import FixedWaiting, ListHumanQueue
from orgmcp.daemon import SchedulerState, SchedulerStatus
from orgmcp.daemon.testing import FakeSchedulerStatus
from orgmcp.kernel import Clock
from orgmcp.kernel.testing import FakeClock
from orgmcp.mail import MailboxReader
from orgmcp.mail.testing import MemoryMailbox
from orgmcp.progress import ProgressReporter
from orgmcp.progress._reporter import DerivedProgressReporter
from orgmcp.progress.testing import FixedProgressReporter


def test_the_runtime_has_the_reporter(tmp_path: Path) -> None:
    runtime = wiring.open_runtime(tmp_path)
    assert isinstance(runtime.progress_reporter, DerivedProgressReporter) and isinstance(runtime.progress_reporter, ProgressReporter)


def test_building_the_ports_does_no_io(tmp_path: Path) -> None:
    runtime = wiring.open_runtime(tmp_path)
    assert runtime.progress_reporter is not None
    assert list(tmp_path.iterdir()) == []


def test_an_override_replaces_the_reporter(tmp_path: Path) -> None:
    fake = FixedProgressReporter("lines")
    assert wiring.open_runtime(tmp_path, {ProgressReporter: fake}).progress_reporter is fake


def test_every_runtime_has_its_own_reporter(tmp_path: Path) -> None:
    assert wiring.open_runtime(tmp_path).progress_reporter is not wiring.open_runtime(tmp_path).progress_reporter


def test_every_collaborator_of_the_reporter_comes_from_the_runtime(tmp_path: Path) -> None:
    """The whole reporter over fakes: nothing of the organization directory is read or written."""
    runtime = wiring.open_runtime(tmp_path, {
        MailboxReader: MemoryMailbox(), HumanQueue: ListHumanQueue([("m1", "Needs you: x (message m1)")]),
        SchedulerStatus: FakeSchedulerStatus(SchedulerState("running", 1, "x")), WaitingOnUser: FixedWaiting(), Clock: FakeClock(),
    })
    assert runtime.progress_reporter.progress() == "No open tasks.\nNeeds you: x (message m1)"
    assert runtime.progress_reporter.describe_progress() == "No open tasks.\nNeeds you: x (message m1)\nscheduler: running (pid 1, since x)"
    assert runtime.progress_reporter.work_in_flight() is False
    assert list(tmp_path.iterdir()) == []
