"""``OrgFingerprint`` and the plan id of an extension (design 5.4): the id covers the blueprint and the parts of the organization it touches."""

from __future__ import annotations

import copy
import re
from collections.abc import Callable
from pathlib import Path

import pytest
from testkit.reach.hirearchy.core import ROOT

from hirearchy.blueprint._fingerprint import OrgFingerprint
from hirearchy.blueprint._identity import HashPlanIdentity
from hirearchy.blueprint import BlueprintError

from . import _corpus
from ._extension_world import World, extension, reads_of, world


@pytest.fixture
def w(tmp_path: Path) -> World:
    made = world(tmp_path, lead_reports=4)
    made.org.define_service(ROOT, "lead", "weekly", description="d", inputs=[], acceptance=["Every row has a date."], deliverable={"description": "x"}, budget=9)
    return made


def plan(parent: str = "lead") -> dict[str, object]:
    """Add a checker under ``lead``, raise the service's budget, and retire the writer."""
    return extension(
        add_agents=[{"parent": parent, "name": "checker", "template": "reviewer", "tools": ["read"]}],
        budgets=[{"owner": "lead", "service": "weekly", "budget": 14}],
        retire=[{"agent": "lead/writer", "reason": "no longer needed"}],
    )


def fingerprint(w: World, bp: dict[str, object] | None = None) -> str:
    return OrgFingerprint(reads_of(w.org)).fingerprint(bp or plan())


def plan_id(w: World, bp: dict[str, object] | None = None) -> str:
    return HashPlanIdentity(OrgFingerprint(reads_of(w.org))).plan_id(bp or plan())


def test_an_untouched_organization_gives_the_same_fingerprint(w: World) -> None:
    assert fingerprint(w) == fingerprint(w) and plan_id(w) == plan_id(w)
    assert re.fullmatch(r"[0-9a-f]{12}", plan_id(w))
    again = copy.deepcopy(plan())
    assert plan_id(w, again) == plan_id(w)


def hire_under_lead(w: World) -> None:
    w.org.hire("lead", "second", "Second", "x", tools=["read"])


def retire_a_report(w: World) -> None:
    w.org.retire(ROOT, "lead/writer", "gone")


def amend_the_contract(w: World) -> None:
    w.org.define_service(ROOT, "lead", "weekly", add_acceptance=["At most 3 pages."], words="They want a page limit.")


def first_playbook(w: World) -> None:
    w.org.define_service(ROOT, "lead", "daily", description="d", inputs=[], acceptance=["Every row has a date."], deliverable={"description": "x"}, budget=9)


def edit_the_charter(w: World) -> None:
    meta, body = w.org.charter("lead")
    from hirearchy.kernel import join_frontmatter

    w.org.runtime.agent_registry.rewrite_charter("lead", join_frontmatter(meta, body + "\n\nAlso check the dates.\n"))


def change_the_depth(w: World) -> None:
    w.org.runtime.settings.write_raw(w.org.runtime.settings.read_raw().replace("max_depth: 4", "max_depth: 6"))


def take_the_address(w: World) -> None:
    w.org.hire("lead", "checker", "Taken", "x", tools=["read"])


def change_the_budget(w: World) -> None:
    w.org.define_service(ROOT, "lead", "weekly", budget=11)


@pytest.mark.parametrize(
    "touch", [hire_under_lead, retire_a_report, amend_the_contract, edit_the_charter, take_the_address, change_the_budget, change_the_depth],
    ids=lambda f: f.__name__,
)
def test_each_touching_change_changes_it(w: World, touch: Callable[[World], None]) -> None:
    before_fingerprint, before_id = fingerprint(w), plan_id(w)
    touch(w)
    assert fingerprint(w) != before_fingerprint and plan_id(w) != before_id


def test_a_playbook_revision_of_a_named_service_changes_it(w: World) -> None:
    before = plan_id(w)
    w.org.revise_playbook("lead", "weekly", "first", "The steps the team followed.", [], text="1. Write the note.\n2. Check the dates.")
    assert plan_id(w) != before


def test_a_hire_under_a_parent_it_does_not_name_changes_nothing(w: World) -> None:
    before = plan_id(w, extension(limits=[{"agent": "solo", "can_hire": True, "max_children": 2}]))
    hire_under_lead(w)
    w.org.define_service(ROOT, "solo", "elsewhere", description="d", inputs=[], acceptance=["Every row has a date."], deliverable={"description": "x"}, budget=5)
    assert plan_id(w, extension(limits=[{"agent": "solo", "can_hire": True, "max_children": 2}])) == before
    w.org.hire(ROOT, "other", "Other", "x", tools=["read"])  # a new team elsewhere in the organization
    assert plan_id(w, extension(limits=[{"agent": "solo", "can_hire": True, "max_children": 2}])) == before


def test_a_full_blueprints_plan_id_is_unchanged(w: World, tmp_path: Path) -> None:
    bp = _corpus.research(tmp_path)
    with_fingerprint, without = HashPlanIdentity(OrgFingerprint(reads_of(w.org))), HashPlanIdentity()
    assert with_fingerprint.plan_id(bp) == without.plan_id(bp)  # the plan goldens hold these exact ids
    hire_under_lead(w)
    assert with_fingerprint.plan_id(bp) == without.plan_id(bp)


def test_an_unreadable_organization_is_refused_in_plain_words(w: World) -> None:
    (w.org.root / "lead" / "AGENT.md").write_text("---\nrole: [broken\n---\nbody\n", encoding="utf-8")
    with pytest.raises(BlueprintError) as raised:
        fingerprint(w)
    text = str(raised.value)
    assert text.startswith("refused: the organization cannot be read (") and text.endswith("), so no plan can be made against it. Try again; if it persists, tell the user.")
