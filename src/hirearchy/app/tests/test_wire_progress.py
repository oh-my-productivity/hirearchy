"""``wire_progress``: the runtime has the reporter, built from the ports of the runtime."""

from __future__ import annotations

from pathlib import Path

from hirearchy.app import wiring
from hirearchy.attention import HumanQueue, WaitingOnUser
from hirearchy.attention.testing import FixedWaiting, ListHumanQueue
from hirearchy.daemon import SchedulerState, SchedulerStatus
from hirearchy.daemon.testing import FakeSchedulerStatus
from hirearchy.kernel import Clock
from hirearchy.kernel.testing import FakeClock
from hirearchy.mail import MailboxReader
from hirearchy.mail.testing import MemoryMailbox
from hirearchy.progress import ProgressReporter, QualityReport
from hirearchy.progress._quality import DerivedQualityReport
from hirearchy.progress._reporter import DerivedProgressReporter
from hirearchy.progress.testing import FixedProgressReporter, FixedQualityReport


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


def test_the_runtime_has_the_quality_report(tmp_path: Path) -> None:
    runtime = wiring.open_runtime(tmp_path)
    assert isinstance(runtime.quality_report, DerivedQualityReport) and isinstance(runtime.quality_report, QualityReport)
    assert list(tmp_path.iterdir()) == []  # building it does no I/O


def test_an_override_replaces_the_quality_report(tmp_path: Path) -> None:
    fake = FixedQualityReport()
    assert wiring.open_runtime(tmp_path, {QualityReport: fake}).quality_report is fake
