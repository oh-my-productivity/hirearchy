"""The steps of an application, one class each: the team, the services, the first task and the rollback - over recording ports."""

from __future__ import annotations

from pathlib import Path

import pytest

from hirearchy.agents.testing import MemoryAgents
from hirearchy.blueprint._firsttask import FirstTaskGiver
from hirearchy.blueprint._playbooks import StepsPlaybookWriter
from hirearchy.blueprint._budgeting import BudgetPlanner
from hirearchy.blueprint._servicedef import PlaybookServiceDefiner
from hirearchy.blueprint._shapes import Built, Split
from hirearchy.blueprint._team import CharterTeamBuilder
from hirearchy.blueprint._undo import RetiringRollback
from hirearchy.blueprint.api import Agent
from hirearchy.blueprint.testing import (
    CallLog,
    MemoryWorkspaceProvisioner,
    RecordingHiring,
    RecordingRetirement,
    RecordingServiceCommands,
    RecordingTaskAssigner,
    FlakyHiring,
)
from hirearchy.kernel import OrgError
from hirearchy.services.testing import normalizer



class FixedCharters:
    """A charter that is the address of the agent: the builder is tested, not the text."""

    def charter(self, a: Agent, agents: object, bp: object, split: object) -> str:
        return f"charter of {a.addr}"


def agent(addr: str, **over: object) -> Agent:
    name = addr.rsplit("/", 1)[-1]
    parent = addr.rsplit("/", 1)[0] if "/" in addr else None
    values: dict[str, object] = {"role": name.title(), "model": "m", "kind": "author", "tools": [], "children": []}
    values.update(over)
    return Agent(addr=addr, name=name, parent=parent, where=f"agents[{addr}]", **values)  # type: ignore[arg-type]


SPLIT: dict[str, Split] = {"lead": {"grant": 9, "keeps": 5}, "lead/w": {"grant": 4, "keeps": 4}}


# ------------------------------------------------------------------------------------------------ the team


def team(tmp: Path, *, fail_on: int | None = None) -> tuple[CharterTeamBuilder, CallLog, MemoryWorkspaceProvisioner, MemoryAgents]:
    log, agents = CallLog(), MemoryAgents()
    hiring = RecordingHiring(agents, log)
    dirs = MemoryWorkspaceProvisioner(existing=[tmp])
    port = FlakyHiring(hiring, fail_on) if fail_on else hiring
    return CharterTeamBuilder(port, FixedCharters(), dirs), log, dirs, agents


def test_the_agents_are_hired_in_order_by_their_parent_with_the_charter_of_the_writer(tmp_path: Path) -> None:
    builder, log, _, _ = team(tmp_path)
    built = Built()
    lead = agent("lead", can_hire=True, max_children=3, children=["lead/w"], tools=["read"], inputs=["/in"])
    builder.build([lead, agent("lead/w", tools=["write"], workspace=str(tmp_path / "ws"))], {}, SPLIT, built, "plan 0123456789ab")
    assert built.created == ["lead", "lead/w"]
    first, second = log.of("hire")
    assert first.args == ("root", "lead", "Lead", "charter of lead")
    assert first.kwargs == {"model": "m", "tools": ["read"], "can_hire": True, "max_children": 3, "workspace": None, "inputs": ["/in"],
                            "approved": True, "kind": "author", "approved_in": "plan 0123456789ab"}  # commit 12: the kind and the approval
    assert second.args == ("lead", "w", "W", "charter of lead/w") and second.kwargs["workspace"] == str(tmp_path / "ws") and second.kwargs["inputs"] is None


def test_inputs_go_to_an_agent_that_has_some_or_may_read_even_if_it_has_none(tmp_path: Path) -> None:
    builder, log, _, _ = team(tmp_path)
    builder.build([agent("a", tools=["read"]), agent("b", tools=["write"])], {}, {}, Built())
    a, b = log.of("hire")
    assert a.kwargs["inputs"] == [] and b.kwargs["inputs"] is None


def test_a_workspace_that_is_not_there_is_made_first_and_remembered_deepest_first(tmp_path: Path) -> None:
    builder, log, dirs, _ = team(tmp_path)
    built = Built()
    ws = tmp_path / "x" / "y"
    builder.build([agent("a", workspace=str(ws))], {}, {}, built)
    assert built.made_dirs == [ws, ws.parent] and ws in dirs.dirs and log.names() == ["hire"]


def test_a_workspace_that_is_there_is_left_alone(tmp_path: Path) -> None:
    builder, _, dirs, _ = team(tmp_path)
    built, before = Built(), set(dirs.dirs)
    builder.build([agent("a", workspace=str(tmp_path))], {}, {}, built)
    assert built.made_dirs == [] and dirs.dirs == before


def test_what_was_made_before_a_failure_is_recorded_for_the_rollback(tmp_path: Path) -> None:
    builder, _, _, _ = team(tmp_path, fail_on=2)
    built = Built()
    with pytest.raises(OrgError, match="disk full"):
        builder.build([agent("a", workspace=str(tmp_path / "w1")), agent("b", workspace=str(tmp_path / "w2"))], {}, {}, built)
    assert built.created == ["a"] and built.made_dirs == [tmp_path / "w1", tmp_path / "w2"]  # the second workspace was made before its hire failed


# ------------------------------------------------------------------------------------------------ the services


def definer(log: CallLog) -> PlaybookServiceDefiner:
    return PlaybookServiceDefiner(RecordingServiceCommands(log), normalizer(Path("/")), StepsPlaybookWriter(BudgetPlanner()), BudgetPlanner())


SERVICE = {
    "name": "weekly", "description": "A brief.", "inputs": [{"name": "topic", "description": "what about", "required": True}],
    "acceptance": ["One page."], "deliverable": {"description": "A file", "format": "markdown", "path": "~/briefs"}, "budget": 9, "locked": True,
}


def test_a_service_is_defined_by_root_for_the_top_agent_with_a_contract_made_of_the_blueprint() -> None:
    log, built = CallLog(), Built()
    definer(log).define({"services": [SERVICE]}, [agent("lead", kind="manager")], built)
    (call,) = log.of("define_service")
    assert call.args == ("root", "lead", "weekly")
    assert call.kwargs["description"] == "A brief." and call.kwargs["acceptance"] == ["One page."] and call.kwargs["budget"] == 9
    assert call.kwargs["inputs"] == [{"name": "topic", "description": "what about", "required": True}]
    assert call.kwargs["deliverable"] == {"description": "A file", "format": "markdown", "path": str(Path("~/briefs").expanduser())}
    assert call.kwargs["locked"] is True and built.defined == ["weekly"]


def test_a_playbook_in_the_blueprint_is_used_stripped_and_otherwise_one_is_written() -> None:
    log = CallLog()
    definer(log).define({"services": [{**SERVICE, "playbook": "  ## Steps\n1. Go.\n\n"}]}, [agent("lead", kind="manager")], Built())
    assert log.of("define_service")[0].kwargs["playbook"] == "## Steps\n1. Go."
    log = CallLog()
    definer(log).define({"services": [SERVICE]}, [agent("lead", kind="manager")], Built())
    written = str(log.of("define_service")[0].kwargs["playbook"])
    assert written.startswith("## Steps\n1. Read the request in your prompt") and "Request budget: 9 runs (the contract's)." in written


def test_the_budget_of_a_service_without_one_is_the_estimate_with_slack() -> None:
    log = CallLog()
    definer(log).define({"services": [{k: v for k, v in SERVICE.items() if k != "budget"}]}, [agent("lead", kind="manager")], Built())
    assert log.of("define_service")[0].kwargs["budget"] == 5  # a lone manager: pass 2 + rework 2 = 4, with 25% slack


def test_every_service_is_defined_in_order_and_remembered_as_it_goes() -> None:
    log, built = CallLog(), Built()
    definer(log).define({"services": [SERVICE, {**SERVICE, "name": "daily"}]}, [agent("lead", kind="manager")], built)
    assert [c.args[2] for c in log.of("define_service")] == ["weekly", "daily"] and built.defined == ["weekly", "daily"]


def test_a_blueprint_without_services_defines_nothing() -> None:
    log = CallLog()
    definer(log).define({}, [agent("lead", kind="manager")], Built())
    assert log.calls == []


# ------------------------------------------------------------------------------------------------ the first task


def giver(log: CallLog) -> FirstTaskGiver:
    return FirstTaskGiver(RecordingTaskAssigner(log), RecordingServiceCommands(log))


def test_no_task_gives_nothing() -> None:
    log = CallLog()
    assert giver(log).give({}, agent("lead"), 5) is None and log.calls == []


def test_a_plain_task_is_delegated_by_root_with_numbered_criteria_and_the_deliverable_in_the_goal() -> None:
    log = CallLog()
    bp = {"needs": {"deliverable": {"description": "A report", "format": "markdown", "max_words": 500}},
          "task": {"title": " T ", "goal": "Do it.", "acceptance": ["one", "two"], "inputs": ["/a", "/b"]}}
    msg = giver(log).give(bp, agent("lead"), 12)
    (call,) = log.of("delegate")
    assert call.args == ("root", "lead", "T", "Do it.\n\nDeliverable: A report (markdown, at most 500 words). Report its path as an artifact.",
                         "1. one\n2. two", ["/a", "/b"], 12, None)
    assert msg is not None and msg.id == "task-1"


def test_a_plain_task_without_a_deliverable_has_just_its_goal() -> None:
    log = CallLog()
    giver(log).give({"task": {"title": "T", "goal": "Do it.", "acceptance": ["one"]}}, agent("lead"), 3)
    assert log.of("delegate")[0].args[3:] == ("Do it.", "1. one", [], 3, None)


def test_a_request_goes_through_the_services_as_root() -> None:
    log = CallLog()
    msg = giver(log).give({"task": {"service": "weekly", "inputs": {"topic": "x"}, "title": " First ", "note": "n"}}, agent("lead"), 12)
    (call,) = log.of("request")
    assert call.args == ("root", "weekly", {"topic": "x"}) and call.kwargs == {"title": "First", "note": "n"} and msg is not None and msg.service == "weekly"


def test_a_request_without_inputs_is_made_with_none() -> None:
    log = CallLog()
    giver(log).give({"task": {"service": "weekly"}}, agent("lead"), 12)
    assert log.of("request")[0].args == ("root", "weekly", {}) and log.of("request")[0].kwargs == {"title": "", "note": ""}


# ------------------------------------------------------------------------------------------------ the rollback


def rollback(tmp: Path) -> tuple[RetiringRollback, CallLog, MemoryAgents, MemoryWorkspaceProvisioner]:
    log, agents = CallLog(), MemoryAgents()
    dirs = MemoryWorkspaceProvisioner(existing=[tmp])
    return RetiringRollback(agents, RecordingRetirement(agents, log), dirs), log, agents, dirs


def test_the_top_level_agents_are_retired_last_first_and_the_ones_below_go_with_them(tmp_path: Path) -> None:
    undo, log, agents, _ = rollback(tmp_path)
    for addr in ("a", "a/x", "b"):
        agents.create(addr, {"role": "r"}, "c")
    undo.undo(Built(created=["a", "a/x", "b"]))
    assert [c.args for c in log.of("retire")] == [("root", "b", "blueprint apply failed midway; rolled back"),
                                                  ("root", "a", "blueprint apply failed midway; rolled back")]
    assert not agents.exists("a") and not agents.exists("a/x") and not agents.exists("b")


def test_an_agent_that_is_gone_already_is_not_retired(tmp_path: Path) -> None:
    undo, log, _, _ = rollback(tmp_path)
    undo.undo(Built(created=["ghost"]))
    assert log.calls == []


def test_a_refused_retirement_is_not_an_error_and_the_others_go_on(tmp_path: Path) -> None:
    undo, log, agents, _ = rollback(tmp_path)
    agents.create("b", {"role": "r"}, "c")
    agents.create("a", {"role": "r"}, "c")

    class Refusing(RecordingRetirement):
        def retire_team(self, actor: str, name: str, reason: str):  # type: ignore[no-untyped-def]
            if name == "a":
                raise OrgError("no way")
            return super().retire_team(actor, name, reason)

    RetiringRollback(agents, Refusing(agents, log), MemoryWorkspaceProvisioner()).undo(Built(created=["b", "a"]))
    assert not agents.exists("b") and agents.exists("a")


def test_the_directories_made_are_removed_while_they_are_empty_and_the_first_that_cannot_go_ends_it(tmp_path: Path) -> None:
    undo, _, _, dirs = rollback(tmp_path)
    inner, outer = tmp_path / "o" / "i", tmp_path / "o"
    dirs.ensure(inner)
    dirs.occupied.add(outer)
    other = tmp_path / "p"
    dirs.ensure(other)
    undo.undo(Built(made_dirs=[inner, outer, other]))
    assert inner not in dirs.dirs and outer in dirs.dirs and other in dirs.dirs  # (outer holds a file: nothing after it is tried)
