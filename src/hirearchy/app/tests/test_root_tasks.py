"""``MailRootTasks``: root's one-off tasks from its sent mail (the contract of ``RootTasks`` over files; the fake is in ``blueprint/tests``)."""

from __future__ import annotations

from pathlib import Path

import pytest

from hirearchy.app import Org
from hirearchy.app._root_tasks import MailRootTasks, criteria_lines
from hirearchy.blueprint._protocols import RootTasks
from hirearchy.kernel import ROOT, msg_time

ACCEPTANCE = "- Every row has a date.\n- At most 3 pages.\n"


@pytest.fixture
def org(tmp_path: Path) -> Org:
    made = Org.init(tmp_path / "org", "root tasks")
    made.hire(ROOT, "lead", "Lead", "Directs.", can_hire=True)
    return made


def tasks_of(org: Org) -> MailRootTasks:
    reader = MailRootTasks(org.runtime.mailbox)
    assert isinstance(reader, RootTasks)
    return reader


def test_a_one_off_task_of_root_is_read_with_its_time_and_its_criteria_lines(org: Org) -> None:
    sent = org.delegate(ROOT, "lead", "Weekly note", "Write the note.", ACCEPTANCE, budget=3)
    found = tasks_of(org).task(sent.id)
    assert found is not None and found.id == sent.id
    assert found.created == msg_time(sent) and found.created is not None
    assert found.criteria == ("- Every row has a date.", "- At most 3 pages.")


def test_a_rework_a_request_an_agents_task_and_an_unknown_id_are_none(org: Org) -> None:
    org.define_service(ROOT, "lead", "weekly", description="d", inputs=[], acceptance=["Every row has a date."], deliverable={"description": "x"}, budget=5, playbook="s")
    request = org.request(ROOT, "weekly", {}, title="r")
    head = org.delegate(ROOT, "lead", "One", "Goal.", ACCEPTANCE, budget=3)
    org.report("lead", head.id, "done", "ready")
    rework = org.delegate(ROOT, "lead", "One again", "Goal.", ACCEPTANCE, budget=2, revises=head.id)
    reader = tasks_of(org)
    assert reader.task(head.id) is not None
    assert reader.task(request.id) is None and reader.task(rework.id) is None
    assert reader.task("20260101T000000000000-nothing") is None and reader.task("../etc") is None


def test_the_criteria_lines_of_a_body_stop_at_the_next_heading() -> None:
    body = "## Goal\nx\n\n## Acceptance criteria\n- one\n\n  two  \n## Inputs\n- /a\n"
    assert criteria_lines(body) == ("- one", "two")
    assert criteria_lines("## Goal\nx") == ()
