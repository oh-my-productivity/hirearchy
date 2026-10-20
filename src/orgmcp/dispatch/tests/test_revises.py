# mypy: ignore-errors
# A test moved from tests/ by tools/relocate_tests.py: untyped until it is converted. Delete the first line when this file is typed.

from datetime import datetime, timezone

import pytest
from testkit.legacy.orgmcp.app import wiring
from testkit.legacy.orgmcp.core import ROOT, OrgError

from orgmcp.kernel import Clock
from orgmcp.kernel.testing import FakeClock

T0 = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
ENG = "ceo/eng"


@pytest.fixture(autouse=True)
def clock(org):
    """The clock of the org: message ids, `created` stamps and hire times are deterministic."""
    c = FakeClock(T0)
    org.runtime = wiring.open_runtime(org.root, {Clock: c})
    return c


# --------------------------------------------------------------------- revises
def test_revises_is_stored_and_rendered(org):
    first = org.delegate(ROOT, "ceo", "Plan", "g", "a")
    second = org.delegate(ROOT, "ceo", "Plan v2", "g", "a", revises=first.id)
    assert second.revises == first.id
    loaded = org.runtime.message_parser.parse(org.dir("ceo") / "inbox" / f"{second.id}.md")
    assert loaded.revises == first.id
    assert f"revises: {first.id}" in loaded.render()
    assert org.runtime.message_parser.parse(org.dir("ceo") / "inbox" / f"{first.id}.md").revises is None


def test_revises_must_be_an_earlier_task_to_the_same_assignee(org):
    org.hire("ceo", "ops", "Ops", "Operate.")
    org.send(ROOT, "ceo", "budget", budget=20)
    for_eng = org.delegate("ceo", ENG, "Build", "g", "a", budget=1)
    with pytest.raises(OrgError, match="revises"):
        org.delegate("ceo", "ceo/ops", "Build", "g", "a", revises=for_eng.id)  # other assignee
    with pytest.raises(OrgError, match="revises"):
        org.delegate("ceo", ENG, "Build", "g", "a", revises="nope")  # unknown id
    with pytest.raises(OrgError, match="revises"):
        org.delegate(ROOT, "ceo", "Build", "g", "a", revises=for_eng.id)  # not sent by this delegator
    note = org.send("ceo", ENG, "just a note")
    with pytest.raises(OrgError, match="revises"):
        org.delegate("ceo", ENG, "Build", "g", "a", revises=note.id)  # not a task
    assert org.delegate("ceo", ENG, "Build again", "g", "a", revises=for_eng.id).revises == for_eng.id
