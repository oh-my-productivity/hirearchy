"""``RecordedContinuedCriteria``: the criteria of the retired copy a definition would continue."""

from __future__ import annotations

from pathlib import Path

import pytest

from hirearchy.app import Org
from hirearchy.app._continued_criteria import RecordedContinuedCriteria
from hirearchy.blueprint._protocols import ContinuedCriteria
from hirearchy.kernel import ROOT
from hirearchy.services._continue import RecordedContinuations
from hirearchy.services._places import OrgServicePlaces
from hirearchy.services._store import OsServiceFiles

CRITERIA = ["Every row has a date.", "At most 3 pages."]


@pytest.fixture
def org(tmp_path: Path) -> Org:
    made = Org.init(tmp_path / "org", "continued")
    made.hire(ROOT, "lead", "Lead", "Directs.", can_hire=True)
    made.define_service(ROOT, "lead", "weekly", description="d", inputs=[], acceptance=CRITERIA, deliverable={"description": "x"}, budget=5, playbook="s")
    return made


def criteria_of(org: Org) -> ContinuedCriteria:
    rt = org.runtime
    made = RecordedContinuedCriteria(RecordedContinuations(OrgServicePlaces(rt.paths), rt.retired_archive, rt.mailbox, OsServiceFiles()))
    assert isinstance(made, ContinuedCriteria)
    return made


def test_a_service_never_defined_or_live_continues_nothing(org: Org) -> None:
    assert criteria_of(org).criteria("lead", "monthly") is None and criteria_of(org).criteria("lead", "weekly") is None


def test_a_retired_service_with_a_recorded_request_continues_with_its_criteria(org: Org) -> None:
    task = org.request(ROOT, "weekly", {}, title="one")
    org.report("lead", task.id, "done", "ready", lessons="Nothing new.")
    org.feedback(ROOT, task.id, "accept")
    org.retire_service(ROOT, "lead", "weekly", "not needed")
    assert criteria_of(org).criteria("lead", "weekly") == tuple(CRITERIA)


def test_a_retired_service_that_was_never_requested_starts_fresh(org: Org) -> None:
    org.retire_service(ROOT, "lead", "weekly", "not needed")
    assert criteria_of(org).criteria("lead", "weekly") is None
