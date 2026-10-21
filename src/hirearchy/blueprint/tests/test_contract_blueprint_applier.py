"""Contract of ``BlueprintApplier``: a checked blueprint becomes an organization - and when a step fails, no trace of it is left (but the error)."""

from __future__ import annotations

import copy
from pathlib import Path
from typing import cast

import pytest

from hirearchy.blueprint import BlueprintApplier, BlueprintError
from hirearchy.blueprint.testing import (
    IMPLEMENTATIONS,
    ApplierHarness,
    FlakyHiring,
    FlakyServiceCommands,
    FlakyTaskAssigner,
)
from hirearchy.kernel import OrgError, child_addr

from ._plans import base_dir, golden, load_text, scrub, template_at
from ._support import implementations, make

ROLLED_BACK = "blueprint apply failed midway; rolled back"


@pytest.fixture(params=implementations(IMPLEMENTATIONS[BlueprintApplier]))
def h(request: pytest.FixtureRequest, tmp_path: Path) -> ApplierHarness:
    made = make(request, tmp_path, ApplierHarness)
    assert isinstance(made.applier, BlueprintApplier)
    return made


def bp_of(key: str, h: ApplierHarness) -> dict[str, object]:
    label, _, variant = key.partition("/")
    return load_text(template_at(label, variant, base_dir(h.tmp)))


RESEARCH_TEAM = ["lead", "lead/researcher", "lead/writer", "lead/factcheck"]  # parents first, children in the order of the blueprint


def test_a_plain_task_hires_the_team_parents_first_and_gives_the_task_to_the_top_agent(h: ApplierHarness) -> None:
    bp, base = bp_of("research/filled", h), base_dir(h.tmp)
    summary = h.applier.apply(bp, allowed_roots=[base])
    assert h.log.names() == ["hire"] * 4 + ["delegate", "commit"]
    assert [c.args[:2] for c in h.log.of("hire")] == [("root", "lead"), ("lead", "researcher"), ("lead", "writer"), ("lead", "factcheck")]
    charters = golden()["charters"]["research"]
    assert {child_addr(str(c.args[0]), str(c.args[1])): scrub(str(c.args[3]), base) for c in h.log.of("hire")} == charters
    (delegate,) = h.log.of("delegate")
    assert delegate.args[:3] == ("root", "lead", "Sample text") and delegate.args[7] is None
    assert delegate.args[6] == 22 and str(delegate.args[4]).startswith("1. Covers exactly the items")  # the task's budget is the planned total
    assert summary.agents == RESEARCH_TEAM and summary.task_id == "task-1" and summary.to == "lead" and summary.budget == 22
    assert summary.services == [] and summary.service_request == ""
    assert summary.text().splitlines()[0] == "created 4 agents: lead, lead/researcher, lead/writer, lead/factcheck"


def test_the_agents_are_hired_with_what_the_plan_gave_them(h: ApplierHarness) -> None:
    h.applier.apply(bp_of("research/filled", h), allowed_roots=[base_dir(h.tmp)])
    researcher = next(c for c in h.log.of("hire") if c.args[1] == "researcher")
    assert researcher.args[2] == "Researcher" and researcher.kwargs["tools"] == ["web_fetch", "web_search"]  # (sorted)
    assert researcher.kwargs["model"] and researcher.kwargs["can_hire"] is False and researcher.kwargs["max_children"] == 0
    assert researcher.kwargs["workspace"] is None and researcher.kwargs["inputs"] is None
    lead = h.log.of("hire")[0]
    assert lead.kwargs["can_hire"] is True


def test_the_inputs_are_given_to_an_agent_that_has_some_or_may_read(h: ApplierHarness) -> None:
    base = base_dir(h.tmp)
    h.applier.apply(bp_of("documents/filled", h), allowed_roots=[base])
    by_name = {str(c.args[1]): c for c in h.log.of("hire")}
    assert by_name["reader"].kwargs["inputs"] == [str(base / "docs")]
    assert by_name["lead"].kwargs["inputs"] is None or by_name["lead"].kwargs["inputs"] == [str(base / "docs")]


def test_the_commit_says_how_many_agents_and_what_was_given(h: ApplierHarness) -> None:
    h.applier.apply(bp_of("research/filled", h), allowed_roots=[base_dir(h.tmp)])
    assert h.log.of("commit")[0].args == ("root: applied blueprint (4 agents), task task-1 -> lead",)


def test_services_are_defined_for_the_top_agent_with_their_contract_and_playbook(h: ApplierHarness) -> None:
    base = base_dir(h.tmp)
    summary = h.applier.apply(bp_of("research-service/filled", h), allowed_roots=[base])
    assert h.log.names() == ["hire"] * 4 + ["define_service", "commit"]
    (define,) = h.log.of("define_service")
    assert define.args == ("root", "lead", "my-service") and define.kwargs["budget"] == 22 and define.kwargs["locked"] is False
    assert define.kwargs["inputs"] == [{"name": "topic", "description": "Sample text", "required": True}]
    assert isinstance(define.kwargs["acceptance"], list) and define.kwargs["acceptance"] and define.kwargs["deliverable"]["format"] == "markdown"  # type: ignore[index]
    assert scrub(str(define.kwargs["playbook"]), base) == golden()["playbooks"]["research-service/my-service"]
    assert summary.services == ["my-service"] and summary.task_id == "" and summary.budget == 0 and summary.to == "lead"
    assert h.log.of("commit")[0].args == ("root: applied blueprint (4 agents), no task, services: my-service",)
    assert "no task was given: the services are ready and nothing runs yet." in summary.text()


def test_a_playbook_the_blueprint_gives_is_used_stripped_and_the_lock_is_kept(h: ApplierHarness) -> None:
    bp = bp_of("research-service/filled", h)
    bp["services"][0].update(playbook="\n## Steps\n1. Search.\n", locked=True)  # type: ignore[index]
    h.applier.apply(bp, allowed_roots=[base_dir(h.tmp)])
    (define,) = h.log.of("define_service")
    assert define.kwargs["playbook"] == "## Steps\n1. Search." and define.kwargs["locked"] is True


def test_a_first_request_is_made_as_root_and_reported(h: ApplierHarness) -> None:
    bp = bp_of("research-service/filled", h)
    bp["task"] = {"service": "my-service", "inputs": {"topic": "ai chips"}, "title": "First", "note": "n"}
    summary = h.applier.apply(bp, allowed_roots=[base_dir(h.tmp)])
    assert h.log.names() == ["hire"] * 4 + ["define_service", "request", "commit"]
    (request,) = h.log.of("request")
    assert request.args == ("root", "my-service", {"topic": "ai chips"}) and request.kwargs == {"title": "First", "note": "n"}
    assert summary.service_request == "my-service" and summary.task_id == "request-1" and summary.budget == 22
    assert summary.text().splitlines()[2] == "first request: service my-service, task request-1 -> lead (budget 22)"
    assert h.log.of("commit")[0].args == ("root: applied blueprint (4 agents), task request-1 -> lead, services: my-service",)


def test_the_warnings_of_the_plan_come_back_in_the_summary(h: ApplierHarness) -> None:
    summary = h.applier.apply(bp_of("research/filled", h), allowed_roots=[base_dir(h.tmp)])
    assert [w.code for w in summary.warnings] == ["path-delivery"] and summary.text().splitlines()[-1].startswith("warning: needs.deliverable.path")


def test_a_blueprint_with_errors_is_refused_before_anything_is_written(h: ApplierHarness) -> None:
    bp = bp_of("research/filled", h)
    cast(dict[str, object], bp["task"]).pop("acceptance")
    with pytest.raises(BlueprintError, match="blueprint has errors, nothing was created:\n- task.acceptance: ") as raised:
        h.applier.apply(bp, allowed_roots=[base_dir(h.tmp)])
    assert str(raised.value).startswith("blueprint has errors, nothing was created:\n- ") and h.log.calls == []


def test_a_name_that_is_taken_is_refused_before_anything_is_written(h: ApplierHarness) -> None:
    h.agents.create("lead", {"role": "someone"}, "x")
    with pytest.raises(BlueprintError, match="already exists"):
        h.applier.apply(bp_of("research/filled", h), allowed_roots=[base_dir(h.tmp)])
    assert h.log.calls == []


def test_applying_twice_is_refused_the_second_time(h: ApplierHarness) -> None:
    bp, base = bp_of("research/filled", h), base_dir(h.tmp)
    h.applier.apply(bp, allowed_roots=[base])
    count = len(h.log.calls)
    with pytest.raises(BlueprintError, match="already exists"):
        h.applier.apply(bp, allowed_roots=[base])
    assert len(h.log.calls) == count


def test_the_blueprint_is_not_changed(h: ApplierHarness) -> None:
    bp = bp_of("research-service/filled", h)
    before = copy.deepcopy(bp)
    h.applier.apply(bp, allowed_roots=[base_dir(h.tmp)])
    assert bp == before


# ------------------------------------------------------------------------------------------------ a step fails


@pytest.mark.parametrize("fail_on", [1, 2, 3, 4])
def test_a_hire_that_fails_leaves_no_agent_and_the_error_is_the_one_raised(h: ApplierHarness, fail_on: int) -> None:
    applier = h.with_ports(hiring=FlakyHiring(h.ports.hiring, fail_on=fail_on))
    with pytest.raises(OrgError, match="disk full"):
        applier.apply(bp_of("research/filled", h), allowed_roots=[base_dir(h.tmp)])
    assert not any(h.agents.exists(a) for a in RESEARCH_TEAM)
    assert h.log.of("commit") == [] and h.log.of("delegate") == []


@pytest.mark.parametrize("fail_on, retired", [(1, 0), (2, 1), (3, 1), (4, 1)])
def test_only_the_top_level_agents_that_were_made_are_retired_as_root_with_the_reason(h: ApplierHarness, fail_on: int, retired: int) -> None:
    applier = h.with_ports(hiring=FlakyHiring(h.ports.hiring, fail_on=fail_on))
    with pytest.raises(OrgError):
        applier.apply(bp_of("research/filled", h), allowed_roots=[base_dir(h.tmp)])
    assert [c.args for c in h.log.of("retire")] == [("root", "lead", ROLLED_BACK)] * retired


def test_a_service_that_cannot_be_defined_takes_the_hires_back(h: ApplierHarness) -> None:
    applier = h.with_ports(commands=FlakyServiceCommands(h.ports.commands, fail_define_on=1))
    with pytest.raises(OrgError, match="disk full"):
        applier.apply(bp_of("research-service/filled", h), allowed_roots=[base_dir(h.tmp)])
    assert not h.agents.exists("lead") and [c.args for c in h.log.of("retire")] == [("root", "lead", ROLLED_BACK)] and h.log.of("commit") == []


def test_a_task_that_cannot_be_given_takes_the_hires_back(h: ApplierHarness) -> None:
    applier = h.with_ports(tasks=FlakyTaskAssigner(h.ports.tasks))
    with pytest.raises(OrgError, match="delegate failed"):
        applier.apply(bp_of("research/filled", h), allowed_roots=[base_dir(h.tmp)])
    assert not any(h.agents.exists(a) for a in RESEARCH_TEAM) and h.log.of("commit") == []


def test_a_request_that_cannot_be_made_takes_the_hires_and_the_services_back(h: ApplierHarness) -> None:
    bp = bp_of("research-service/filled", h)
    bp["task"] = {"service": "my-service", "inputs": {"topic": "x"}}
    applier = h.with_ports(commands=FlakyServiceCommands(h.ports.commands, fail_request_on=1))
    with pytest.raises(OrgError, match="disk full"):
        applier.apply(bp, allowed_roots=[base_dir(h.tmp)])
    assert not h.agents.exists("lead") and len(h.log.of("define_service")) == 1 and [c.args for c in h.log.of("retire")] == [("root", "lead", ROLLED_BACK)]


# ------------------------------------------------------------------------------------------------ workspaces


def code_bp(h: ApplierHarness, workspace: Path) -> dict[str, object]:
    """The code blueprint with its workspace in ``workspace``; what is there already (the base directory) is known to the provisioner."""
    h.provisioner.ensure(base_dir(h.tmp))
    bp = bp_of("code/filled", h)
    bp["needs"]["workspace"] = str(workspace)  # type: ignore[index]
    return bp


def test_a_workspace_that_is_not_there_is_made_before_the_hire_that_needs_it(h: ApplierHarness) -> None:
    workspace = base_dir(h.tmp) / "fresh"
    h.applier.apply(code_bp(h, workspace), allowed_roots=[base_dir(h.tmp)])
    assert h.dir_exists(workspace)


def test_a_workspace_made_by_a_call_that_failed_is_removed_again(h: ApplierHarness) -> None:
    workspace = base_dir(h.tmp) / "fresh2"
    applier = h.with_ports(tasks=FlakyTaskAssigner(h.ports.tasks, error="nope"))
    with pytest.raises(OrgError, match="nope"):
        applier.apply(code_bp(h, workspace), allowed_roots=[base_dir(h.tmp)])
    assert not h.dir_exists(workspace) and h.dir_exists(base_dir(h.tmp)) and h.agents.children("root") == []


def test_a_workspace_that_was_there_stays(h: ApplierHarness) -> None:
    workspace = base_dir(h.tmp) / "proj"
    bp = code_bp(h, workspace)
    h.provisioner.ensure(workspace)
    applier = h.with_ports(tasks=FlakyTaskAssigner(h.ports.tasks))
    with pytest.raises(OrgError):
        applier.apply(bp, allowed_roots=[base_dir(h.tmp)])
    assert h.dir_exists(workspace)
