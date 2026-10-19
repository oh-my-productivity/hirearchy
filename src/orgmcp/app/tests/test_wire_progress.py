"""``wire_progress``: the runtime has the reporter and the parts of the legacy functions, built from the ports of the runtime; and the parts follow the
runtime in force (one the dashboard's lenient ``Org`` or a test replaced a part of)."""

from __future__ import annotations

import dataclasses
from pathlib import Path

import pytest

from orgmcp.app import Org, wire_progress, wiring
from orgmcp.attention import HumanQueue, Waiting, WaitingOnUser
from orgmcp.attention.testing import FixedWaiting, ListHumanQueue
from orgmcp.dashboard_data import LenientOrg
from orgmcp.daemon import SchedulerState, SchedulerStatus
from orgmcp.daemon.testing import FakeSchedulerStatus
from orgmcp.kernel import ROOT, Clock
from orgmcp.kernel.testing import FakeClock
from orgmcp.mail import MailboxReader
from orgmcp.mail.testing import MemoryMailbox
from orgmcp.progress import LegacyParts, ProgressReporter
from orgmcp.progress._reporter import DerivedProgressReporter
from orgmcp.progress.testing import FixedProgressReporter
from orgmcp.reflection import CaseHistory, ServiceReports

RED = pytest.mark.xfail(strict=True, reason="red: C-progress", raises=NotImplementedError)


def test_the_runtime_has_the_reporter_and_the_parts(tmp_path: Path) -> None:
    runtime = wiring.open_runtime(tmp_path)
    assert isinstance(runtime.progress_reporter, DerivedProgressReporter) and isinstance(runtime.progress_reporter, ProgressReporter)
    assert isinstance(runtime.progress_parts, wire_progress.RuntimeParts) and isinstance(runtime.progress_parts, LegacyParts)


def test_building_the_ports_does_no_io(tmp_path: Path) -> None:
    runtime = wiring.open_runtime(tmp_path)
    assert runtime.progress_reporter is not None and runtime.progress_parts is not None
    assert list(tmp_path.iterdir()) == []


def test_an_override_replaces_the_reporter(tmp_path: Path) -> None:
    fake = FixedProgressReporter("lines")
    assert wiring.open_runtime(tmp_path, {ProgressReporter: fake}).progress_reporter is fake


def test_every_runtime_has_its_own_reporter(tmp_path: Path) -> None:
    assert wiring.open_runtime(tmp_path).progress_reporter is not wiring.open_runtime(tmp_path).progress_reporter


@RED
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


# ------------------------------------------------------------------------------ the parts of the legacy functions


@pytest.fixture
def org(tmp_path: Path) -> Org:
    made = Org.init(tmp_path / "org", "mission")
    made.hire("root", "ceo", "Chief", "Run it.")
    return made


def test_the_parts_are_the_objects_of_the_other_packages(org: Org) -> None:
    parts = org.runtime.progress_parts
    assert isinstance(parts.human_queue(org.runtime), HumanQueue) and isinstance(parts.case_history(org.runtime), CaseHistory)
    assert isinstance(parts.service_reports(org.runtime), ServiceReports) and isinstance(parts.scheduler_status(org.runtime), SchedulerStatus)
    assert isinstance(parts.waiting_on_user(org.runtime), WaitingOnUser)


def test_the_queue_reads_the_mailboxes_of_the_runtime_in_force(org: Org) -> None:
    org.send("ceo", ROOT, "kept apart", title="hello")
    other = MemoryMailbox()
    org.runtime = dataclasses.replace(org.runtime, mailbox=other)
    assert org.runtime.progress_parts.human_queue(org.runtime).items() == []


def test_the_queue_of_a_lenient_org_skips_what_it_cannot_read(org: Org) -> None:
    good = org.send("ceo", ROOT, "I need 2 more runs", title="Budget request")
    (org.root / "inbox" / "20260101T000000000000-ceo-bad0.md").write_text("---\nfrom: [oops\n---\nx\n", encoding="utf-8")
    lenient = LenientOrg(org.root)
    assert [mid for mid, _ in lenient.runtime.progress_parts.human_queue(lenient.runtime).items()] == [good.id]
