"""Applying an extension to a real temporary organization (design 5.5): the order of the writes, what each one records, and the stale refusal."""

from __future__ import annotations

from pathlib import Path

import pytest
from testkit.reach.hirearchy.app import wiring
from testkit.reach.hirearchy.core import ROOT

from hirearchy.blueprint import BlueprintError
from hirearchy.blueprint.testing import CallLog, RecordingSnapshots
from hirearchy.hierarchy import Hiring
from hirearchy.settings import OrgLimits
from hirearchy.snapshots import OrgSnapshotter

from ._extension_world import World, extension, world

CRITERIA = ["Every row has a date.", "At most 3 pages."]


@pytest.fixture
def w(tmp_path: Path) -> World:
    """lead (2 of 2 reports: writer, second) offers weekly at 9 runs; solo offers nothing; old is a top-level agent nobody names."""
    made = world(tmp_path)
    made.org.hire("lead", "second", "Second", "x", tools=["read"])
    made.org.define_service(ROOT, "lead", "weekly", description="A weekly note", inputs=[], acceptance=CRITERIA, deliverable={"description": "a note"}, budget=9, playbook="steps")
    made.org.hire(ROOT, "old", "Old", "x", tools=["read"])
    return made


def pid_of(w: World, bp: dict[str, object]) -> str:
    return str(w.org.runtime.plan_identity.plan_id(bp))


def apply(w: World, bp: dict[str, object], *, ports: dict[type, object] | None = None, plan_id: str | None = "ok") -> str:
    runtime = wiring.open_runtime(w.org.root, ports) if ports else w.org.runtime
    return str(runtime.extension_applier.apply(bp, plan_id=pid_of(w, bp) if plan_id == "ok" else plan_id, allowed_roots=[w.tmp]))


CHECKER = {"parent": "lead", "name": "checker", "template": "reviewer", "tools": ["read"], "charter_extra": "Check every date item by item."}


def checker_plan(**more: object) -> dict[str, object]:
    return extension(
        add_agents=[CHECKER], limits=[{"agent": "lead", "max_children": 3}], budgets=[{"owner": "lead", "service": "weekly", "budget": 20}], **more,
    )


class SpyHiring(Hiring):
    """Forwards to the real hiring and keeps the limits the lead has at the moment of each hire."""

    def __init__(self, inner: Hiring, org: object) -> None:
        self._inner = inner
        self._org = org
        self.seen: list[tuple[str, int]] = []

    def hire(self, actor: str, name: str, role: str, charter: str, **kw: object) -> str:
        self.seen.append((name, int(self._org.charter("lead")[0]["max_children"])))  # type: ignore[attr-defined]
        return self._inner.hire(actor, name, role, charter, **kw)  # type: ignore[arg-type]


class SpyLimits(OrgLimits):
    def __init__(self, inner: OrgLimits) -> None:
        self._inner = inner
        self.calls: list[int] = []

    def set_max_depth(self, value: int) -> int:
        self.calls.append(value)
        return self._inner.set_max_depth(value)


def test_limits_are_written_before_the_hires_so_the_hiring_rules_admit_them(w: World) -> None:
    spy = SpyHiring(w.org.runtime.hiring, w.org)
    pid = pid_of(w, checker_plan())
    reply = apply(w, checker_plan(), ports={Hiring: spy})
    assert spy.seen == [("checker", 3)]  # the lead already had room for a third report when the hire came
    assert w.org.agents().count("lead/checker") == 1 and w.org.charter("lead")[0]["max_children"] == 3
    assert reply.startswith(f"applied the change {pid} to {w.org.root}\nadded 1 agent(s): lead/checker\n") and reply.endswith("Nothing runs because of it.")


def test_max_depth_is_written_through_org_limits(w: World) -> None:
    spy = SpyLimits(w.org.runtime.org_limits)
    apply(w, extension(limits=[{"org": "max_depth", "value": 6}]), ports={OrgLimits: spy})
    assert spy.calls == [6] and w.org.runtime.settings.config()["max_depth"] == 6


def test_a_new_agent_has_kind_approved_in_change_and_the_extension_charter(w: World) -> None:
    bp = checker_plan()
    pid = pid_of(w, bp)
    apply(w, bp)
    meta, body = w.org.charter("lead/checker")
    assert meta["kind"] == "verifier" and meta["approved_in"] == f"change {pid}" and meta["hired_by"] == "lead" and meta["role"] == "Independent Reviewer"
    assert f"## Assignment (from the user's change {pid})" in body and "Reports to: lead" in body and body.rstrip().endswith("## Additional instructions\nCheck every date item by item.")


def test_a_new_service_has_sources_elicitation_and_approved_in_change(w: World) -> None:
    bp = {**extension(add_services=[{"owner": "solo", "name": "monthly", "description": "A monthly note", "acceptance": [
        {"text": "Notes in at most 3 pages.", "from": "At most 3 pages.", "asked": "How long?"}, {"text": "Every row has a date.", "default": True}],
        "deliverable": {"description": "a note", "format": "markdown"}}]), "needs": {"elicitation": "At most 3 pages. Notes please."}}
    pid = pid_of(w, bp)
    apply(w, bp)
    stored = w.org.runtime.service_store.read_contract("solo", "monthly")
    assert stored is not None
    meta = stored[0]
    assert meta["approved_in"] == f"change {pid}" and meta["elicitation"] == "At most 3 pages. Notes please."
    assert meta["sources"] == [{"from": "At most 3 pages.", "asked": "How long?"}, {"default": True}]
    assert w.org.runtime.service_catalog.read_playbook("solo", "monthly").version == 1


def test_an_added_line_goes_under_added_by_your_changes_with_its_tag(w: World) -> None:
    bp = extension(add_charter_lines=[{"agent": "lead/writer", "line": "Cite the source."}])
    pid = pid_of(w, bp)
    before = w.org.charter("lead/writer")
    apply(w, bp)
    meta, body = w.org.charter("lead/writer")
    assert meta == before[0] and body == before[1] + f"\n\n## Added by your changes\n- Cite the source. [change {pid}]"


def test_a_checker_adds_a_line_to_the_owner_and_the_limits_line_stays_last(w: World) -> None:
    bp = checker_plan()
    pid = pid_of(w, bp)
    apply(w, bp)
    body = w.org.charter("lead")[1]
    assert f"- lead/checker (Independent Reviewer) was added to your team to check weekly: Check every date item by item. [change {pid}]" in body
    assert body.rstrip().endswith(f"- Your hiring limits were set by the user's change: up to 3 direct reports; may hire: yes. [change {pid}]")  # the limits line stays last


def test_a_later_limits_change_replaces_the_limits_line(w: World) -> None:
    apply(w, extension(limits=[{"agent": "lead", "max_children": 3}]))
    second = extension(limits=[{"agent": "lead", "max_children": 4}])
    second_id = pid_of(w, second)
    apply(w, second)
    body = w.org.charter("lead")[1]
    assert body.count("Your hiring limits were set") == 1 and f"up to 4 direct reports; may hire: yes. [change {second_id}]" in body
    assert body.count("## Added by your changes") == 1


def test_remove_charter_lines_removes_the_line_and_an_empty_heading(w: World) -> None:
    before = w.org.charter("lead/writer")[1]
    apply(w, extension(add_charter_lines=[{"agent": "lead/writer", "line": "Cite the source."}, {"agent": "lead/writer", "line": "Date every row."}]))
    apply(w, extension(remove_charter_lines=[{"agent": "lead/writer", "line": "cite the source"}]))
    body = w.org.charter("lead/writer")[1]
    assert "Cite the source" not in body and "Date every row." in body and body.count("## Added by your changes") == 1
    apply(w, extension(remove_charter_lines=[{"agent": "lead/writer", "line": "Date every row."}]))
    assert w.org.charter("lead/writer")[1] == before  # the heading went with the last line


def test_a_budget_change_writes_the_next_contract_version(w: World) -> None:
    apply(w, extension(budgets=[{"owner": "lead", "service": "weekly", "budget": 14}]))
    contract = w.org.runtime.service_catalog.read_contract("lead", "weekly")
    assert contract is not None and (contract.version, contract.budget, contract.acceptance) == (2, 14, CRITERIA)
    assert [v for v, _, _ in w.org.runtime.service_store.versions("lead", "weekly", "SERVICE")] == [1, 2]


def test_service_and_agent_retires_carry_approved_in_change(w: World) -> None:
    bp = extension(retire_services=[{"owner": "lead", "service": "weekly", "reason": "unused"}], retire=[{"agent": "old", "reason": "no longer needed"}])
    pid = pid_of(w, bp)
    apply(w, bp)
    assert w.org.runtime.service_catalog.read_contract("lead", "weekly") is None and "old" not in w.org.agents()
    (tree,) = w.org.runtime.retired_archive.trees()
    record = w.org.runtime.retired_archive.record(tree)
    assert record["approved_in"] == f"change {pid}" and record["by"] == ROOT and record["reason"] == "no longer needed"
    copies = list((w.org.root / "lead" / "services" / ".retired").glob("weekly-*/RETIRED.md"))
    assert len(copies) == 1 and f"approved_in: change {pid}" in copies[0].read_text(encoding="utf-8")


def test_the_commit_subject_names_the_extension(w: World) -> None:
    log = CallLog()
    bp = checker_plan(retire=[{"agent": "old", "reason": "no longer needed"}])
    pid = pid_of(w, bp)
    apply(w, bp, ports={OrgSnapshotter: RecordingSnapshots(log)})
    assert [c.args for c in log.of("commit")] == [(f"root: applied extension {pid} (B1.1: a change): +1 agents, +0 services, 1 lines, 1 limits, -1 agents",)]


def test_a_stale_plan_id_is_extend_stale_and_nothing_is_written(w: World) -> None:
    bp = extension(add_charter_lines=[{"agent": "lead/writer", "line": "Cite the source."}], budgets=[{"owner": "lead", "service": "weekly", "budget": 14}])
    stale = pid_of(w, bp)
    w.org.hire(ROOT, "other", "Other", "x", tools=["read"])  # elsewhere in the organization: the id holds
    assert pid_of(w, bp) == stale
    w.org.define_service(ROOT, "lead", "weekly", budget=11)  # a service it names changes
    before = (w.org.charter("lead/writer"), w.org.runtime.service_catalog.read_contract("lead", "weekly"))
    with pytest.raises(BlueprintError) as raised:
        apply(w, bp, plan_id=stale)
    assert str(raised.value) == (
        "not applied: plan_id does not match this change against the organization as it is now (the blueprint, or something it names: an agent, a service, "
        'a limit or a schedule, changed since propose_org), so this is not the plan the user approved. Call propose_org(blueprint, extend="current") again, '
        "show the new PLAN FOR YOU block, and apply only after their approval."
    )
    assert (w.org.charter("lead/writer"), w.org.runtime.service_catalog.read_contract("lead", "weekly")) == before


def test_without_a_plan_id_step_2_is_skipped(w: World) -> None:
    bp = extension(add_charter_lines=[{"agent": "lead/writer", "line": "Cite the source."}])
    apply(w, bp, plan_id=None)
    assert "Cite the source." in w.org.charter("lead/writer")[1]


def test_an_extension_with_an_error_writes_nothing(w: World) -> None:
    with pytest.raises(BlueprintError, match="^blueprint has errors, nothing was created:\n- extend.limits\\[0\\]: ghost is not an agent"):
        apply(w, extension(limits=[{"agent": "ghost", "max_children": 3}]), plan_id=None)
