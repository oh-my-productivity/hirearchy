"""Contract of ``LegacyParts``: the objects the legacy functions ask for, over the runtime they are handed.

Its one real implementation is built by the composition root over a runtime (``app/tests/test_wire_progress.py``: the parts are the objects of the other packages
and follow the runtime in force); the fake that tests of the legacy functions use is held to the same contract here."""

from __future__ import annotations

from orgmcp.attention import HumanQueue, WaitingOnUser
from orgmcp.attention.testing import FixedWaiting, ListHumanQueue
from orgmcp.daemon import SchedulerStatus
from orgmcp.daemon.testing import FakeSchedulerStatus
from orgmcp.progress import LegacyParts
from orgmcp.progress.testing import FixedCaseTotals, FixedLegacyParts
from orgmcp.reflection import CaseHistory, ServiceReports
from orgmcp.reflection.testing import FixedCaseHistory


def parts() -> FixedLegacyParts:
    return FixedLegacyParts(ListHumanQueue(), FixedCaseHistory(), FixedCaseTotals(), FakeSchedulerStatus(), FixedWaiting())


def test_the_fake_is_a_set_of_legacy_parts() -> None:
    assert isinstance(parts(), LegacyParts)


def test_each_part_is_the_object_of_its_package_and_is_asked_for_by_name() -> None:
    fixed = parts()
    runtime = object()
    assert isinstance(fixed.human_queue(runtime), HumanQueue) and isinstance(fixed.case_history(runtime), CaseHistory)
    assert isinstance(fixed.service_reports(runtime), ServiceReports) and isinstance(fixed.scheduler_status(runtime), SchedulerStatus)
    assert isinstance(fixed.waiting_on_user(runtime), WaitingOnUser)
    assert fixed.asked == ["human_queue", "case_history", "service_reports", "scheduler_status", "waiting_on_user"]
