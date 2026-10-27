"""``ServiceTools``: who gets which tools (decided when the server starts), and what each tool says."""

from __future__ import annotations

import asyncio
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import pytest

from hirearchy.agents.testing import MemoryAgents
from hirearchy.kernel import ROOT, Message, OrgError
from hirearchy.mcp_server._instructions import InstructionText
from hirearchy.mcp_server._tools_services import DirectoryServiceRoles, ServiceTools
from hirearchy.mcp_server.testing import HeldBudgets, MemoryBinding, ScriptedReports, ScriptedSteps, agents_in
from hirearchy.services import BASE_HEADING, Admission, Contract, Criterion, Playbook, PlaybookChange, ServiceCatalog, ServiceCommands

from ._support import call, described, fails, names, serve


class Catalog(ServiceCatalog):
    """The services each owner offers are the names in ``offered``."""

    def __init__(self, offered: dict[str, list[str]]) -> None:
        self.offered = offered

    def service_names(self, addr: str) -> list[str]:
        return list(self.offered.get(addr, []))

    def read_contract(self, owner: str, name: str) -> Contract | None:
        return None

    def read_playbook(self, owner: str, name: str):  # type: ignore[no-untyped-def]
        raise OrgError("not scripted")

    def owned_services(self, owner: str) -> list[Contract]:
        return []

    def requestable_services(self, actor: str) -> list[Contract]:
        return []

    def criteria(self, owner: str, name: str) -> list[Criterion]:
        return []

    def playbook_versions(self, owner: str, name: str) -> list[Playbook]:
        return []


class Commands(ServiceCommands):
    def __init__(self, needs_base: bool = False) -> None:
        self.needs_base = needs_base  # a request that is given a ``base`` is answered with a task body that has the base section
        self.calls: list[tuple[str, tuple[object, ...], dict[str, object]]] = []

    def define_service(self, actor: str, owner: str, name: str, **fields: object) -> str:
        self.calls.append(("define_service", (actor, owner, name), fields))
        return f"defined {name}"

    def retire_service(self, actor: str, owner: str, name: str, reason: str) -> str:
        return "retired"

    def request(self, actor: str, service: str, inputs: object, **fields: object) -> Message:
        self.calls.append(("request", (actor, service, inputs), fields))
        based = f"{BASE_HEADING}the version the client judged\n..." if self.needs_base and fields.get("base") else ""
        return Message(actor, "ceo", "task", based, budget=9, contract=2, playbook=3, service=service, id="req-1")

    def revise_playbook(self, actor: str, service: str, op: str | None, reason: str, evidence: Sequence[str], **kw: Any) -> PlaybookChange:
        self.calls.append(("revise_playbook", (actor, service, op, reason, evidence), {k: v for k, v in kw.items() if v is not None}))
        return PlaybookChange(4, op or "", "P3", "step", Admission("b", ("R1", "C2"), "", why=("R1", "C2")), None, 3, client="ceo")

    def feedback(
        self, actor: str, task_id: str, verdict: str, note: str = "", *, source: str | None = None, criterion: Sequence[str] | None = None,
        confirms: str | None = None,
    ) -> Message:
        given = {"source": source, "criterion": criterion, "confirms": confirms}
        self.calls.append(("feedback", (actor, task_id, verdict, note), {k: v for k, v in given.items() if v is not None}))
        return Message(actor, "ceo", "note", "", id="fb-1", source=source, criterion=", ".join(criterion) if criterion else None)


def tools(agents: MemoryAgents | None = None, offered: dict[str, list[str]] | None = None, exists: bool = True,
          reports: ScriptedReports | None = None, steps: ScriptedSteps | None = None, needs_base: bool = False) -> tuple[ServiceTools, Commands]:
    agents, commands = agents or agents_in("ceo", "ceo/eng", "ops"), Commands(needs_base)
    roles = DirectoryServiceRoles(InstructionText(MemoryBinding(Path("/o"), exists=exists)), lambda: agents, lambda: agents, lambda: Catalog(offered or {}))
    return ServiceTools(
        roles, lambda: reports or ScriptedReports("SERVICES", {"req-1": "case total: 3 of 9"}), lambda: commands, lambda: HeldBudgets({"ceo": 5}),
        lambda: steps or ScriptedSteps(),
    ), commands


CLIENT = ["services", "define_service", "request", "feedback"]


def test_root_is_a_client() -> None:
    assert names(serve(tools()[0], ROOT)) == CLIENT


def test_an_agent_with_reports_or_the_right_to_hire_is_a_client() -> None:
    assert names(serve(tools(agents_in("ceo", "ceo/eng"))[0], "ceo")) == CLIENT
    assert names(serve(tools(agents_in("ceo", "ops", can_hire=("ops",)))[0], "ops")) == CLIENT


def test_a_plain_worker_sees_none_of_them() -> None:
    assert names(serve(tools()[0], "ceo/eng")) == []


def test_an_owner_gets_services_and_revise_playbook() -> None:
    assert names(serve(tools(offered={"ceo/eng": ["brief"]})[0], "ceo/eng")) == ["services", "revise_playbook"]


def test_an_owner_that_is_also_a_manager_gets_both_sets_once() -> None:
    assert names(serve(tools(offered={"ceo": ["brief"]})[0], "ceo")) == [*CLIENT, "revise_playbook"]


def test_before_the_organization_exists_only_root_has_the_client_tools() -> None:
    assert names(serve(tools(exists=False)[0], ROOT)) == CLIENT
    assert names(serve(tools(exists=False)[0], "ceo")) == []


def test_services_says_what_the_report_says_for_the_caller() -> None:
    assert call(serve(tools()[0], "ceo"), "services") == "SERVICES [ceo]"


def test_define_service_passes_every_field_and_returns_the_answer() -> None:
    group, commands = tools()
    out = call(serve(group, "ceo"), "define_service", owner="ceo/eng", name="brief", description="d", acceptance=["a"], budget=3, locked=True)
    assert out == "defined brief"
    ((_, args, fields),) = commands.calls
    assert args == ("ceo", "ceo/eng", "brief")
    assert fields == {"description": "d", "inputs": None, "acceptance": ["a"], "deliverable": None, "budget": 3, "playbook": None, "locked": True,
                      "notes": None, "add_acceptance": None, "remove_acceptance": None}


def test_request_says_the_task_the_versions_and_what_to_do_next() -> None:
    group, commands = tools()
    out = call(serve(group, "ceo"), "request", service="brief", inputs={"topic": "x"}, title="T")
    assert out == "requested service `brief` from ceo: task req-1, budget 9 (contract v2, playbook v3). Your budget is now 5."
    assert commands.calls[0][2] == {"title": "T", "note": "", "extra_acceptance": None, "budget": None, "revises": None}
    assert call(serve(group, ROOT), "request", service="brief").endswith("Call start() if the scheduler is not running.")


def params_of(server: object, tool: str) -> set[str]:
    return {t.name: set(t.inputSchema["properties"]) for t in asyncio.run(server.list_tools())}[tool]  # type: ignore[attr-defined]


def test_root_request_says_a_rework_after_the_users_rejection_is_human() -> None:
    text = " ".join(described(serve(tools()[0], ROOT))["request"].split())
    assert "a rework after their own rejection, carrying their corrections, is one" in text and 'source (with revises): "human" when the user asked for this rework' in text
    assert "source" in params_of(serve(tools()[0], ROOT), "request")


def test_agents_request_has_no_source_parameter() -> None:
    server = serve(tools()[0], "ceo")
    assert "source" not in params_of(server, "request") and "source" not in described(server)["request"]


def test_root_request_forwards_the_source_it_is_given() -> None:
    group, commands = tools()
    call(serve(group, ROOT), "request", service="brief", revises="old", source="human")
    call(serve(group, ROOT), "request", service="brief", revises="old")
    assert [c[2]["source"] for c in commands.calls] == ["human", None]  # no source: the sender stamps a root rework `relayed`


def test_root_request_has_base_and_the_reply_says_what_it_did() -> None:
    assert "base" in params_of(serve(tools()[0], ROOT), "request") and "base" not in params_of(serve(tools()[0], "ceo"), "request")
    text = " ".join(described(serve(tools()[0], ROOT))["request"].split())
    assert 'base (with revises and source="human"): "delivered" or "latest"' in text and "which version the user's corrections apply to" in text
    assert "base" not in described(serve(tools()[0], "ceo"))["request"]
    group, commands = tools(needs_base=True)
    delivered = call(serve(group, ROOT), "request", service="brief", revises="old", source="human", base="delivered")
    latest = call(serve(group, ROOT), "request", service="brief", revises="old", source="human", base="latest")
    assert [c[2]["base"] for c in commands.calls] == ["delivered", "latest"]
    assert delivered.endswith("\nbase delivered: the lead starts from the version the user judged.")
    assert latest.endswith("\nbase latest: the changes of your own relayed rework stay in it: tell the user so.")
    plain = call(serve(tools()[0], ROOT), "request", service="brief", revises="old", source="human", base="latest")
    assert plain.endswith("\nbase: not needed (no relayed rework changed the delivery the user judged).")
    unasked = call(serve(tools()[0], ROOT), "request", service="brief", revises="old", source="human")
    assert "base" not in unasked


def test_a_rework_also_states_the_case_total() -> None:
    out = call(serve(tools()[0], "ceo"), "request", service="brief", revises="old")
    assert out.endswith("Your budget is now 5.\ncase total: 3 of 9")


def test_feedback_says_who_it_did_not_wake() -> None:
    assert call(serve(tools()[0], "ceo"), "feedback", task_id="t1", verdict="accept") == (
        "feedback accept recorded on t1 for ceo (message fb-1); it does not wake ceo")


def test_revise_playbook_docstring_names_confirmed_amendments() -> None:
    text = " ".join(described(serve(tools(offered={"ceo/eng": ["brief"]})[0], "ceo/eng"))["revise_playbook"].split())
    assert (
        "or when the item is only the own words of a criterion your parent added to the contract by an amendment the client confirmed (your Reflect "
        "section and the amendment note name them); a link note id counts as its criterion; your lessons, relayed verdicts and an agent client's "
        "verdicts are not evidence." in text
    )


def test_revise_playbook_says_the_version_and_that_the_client_was_told_quietly() -> None:
    group, commands = tools(offered={"ceo/eng": ["brief"]})
    out = call(serve(group, "ceo/eng"), "revise_playbook", service="brief", op="add", kind="step", text="x", reason="r", evidence=["R1", "C2"])
    assert out == (
        "playbook of brief is now v4: added P3 (step), admitted (b) on R1, C2. It starts new and is watched: a related client rejection warns it, a "
        "second retires it. ceo was told without being woken."
    )
    assert commands.calls[-1] == ("revise_playbook", ("ceo/eng", "brief", "add", "r", ["R1", "C2"]), {"kind": "step", "text": "x"})


def test_a_missing_organization_is_the_refusal_of_a_client_tool() -> None:
    def gone() -> object:
        raise OrgError("no organization at /o yet: call create_org(mission=...) first")

    roles = DirectoryServiceRoles(InstructionText(MemoryBinding(Path("/o"))), gone, gone, gone)  # type: ignore[arg-type]
    group = ServiceTools(roles, gone, gone, gone, gone)  # type: ignore[arg-type]
    assert "call create_org" in fails(serve(group, ROOT), "services")


def test_root_feedback_passes_source_criterion_and_confirms_and_defaults_to_relayed() -> None:
    group, commands = tools()
    server = serve(group, ROOT)
    out = call(server, "feedback", task_id="t1", verdict="reject", note="No.", source="human", criterion=["C1", "R2"])
    assert out == "feedback reject recorded on t1 for ceo (message fb-1, source human, about C1, R2 (not confirmed)); it does not wake ceo"
    assert commands.calls[-1] == ("feedback", ("root", "t1", "reject", "No."), {"source": "human", "criterion": ["C1", "R2"]})
    assert call(server, "feedback", task_id="t1", verdict="accept") == "feedback accept recorded on t1 for ceo (message fb-1, source relayed); it does not wake ceo"
    assert commands.calls[-1] == ("feedback", ("root", "t1", "accept", ""), {"source": "relayed"})
    out = call(server, "feedback", task_id="t1", verdict="reject", note="Yes.", source="human", criterion=["C1"], confirms="m-9")
    assert out == "recorded: rejection m-9 is about C1 (source human; message fb-1); it does not wake ceo"
    assert commands.calls[-1][2] == {"source": "human", "criterion": ["C1"], "confirms": "m-9"}


def test_the_agents_feedback_passes_nothing_but_the_verdict() -> None:
    group, commands = tools()
    server = serve(group, "ceo")
    call(server, "feedback", task_id="t1", verdict="reject", note="No.")
    assert commands.calls[-1] == ("feedback", ("ceo", "t1", "reject", "No."), {})
    assert params_of(server, "feedback") == {"task_id", "verdict", "note"}


# ------------------------------------------------------------------------------ the next step, at the point of action (root only)

FEEDBACK_STEP = "NEXT: ask the user one question naming R1."
REWORK_STEP = "old's result asked the client: Keep Marta's row?. Ask the user these questions, unless the user asked for this change: a rework does not answer them."


def test_root_feedback_reply_marks_an_own_criterion_and_names_the_next_step() -> None:
    steps = ScriptedSteps(feedback=FEEDBACK_STEP)
    group, _ = tools(steps=steps)
    out = call(serve(group, ROOT), "feedback", task_id="t1", verdict="reject", note="No.", source="human", criterion=["C1"])
    assert out == f"feedback reject recorded on t1 for ceo (message fb-1, source human, about C1 (not confirmed)); it does not wake ceo\n{FEEDBACK_STEP}"
    assert steps.asked == [("feedback", "fb-1")]


def test_root_feedback_reply_without_a_step_or_a_criterion_is_the_bare_receipt() -> None:
    group, _ = tools(steps=ScriptedSteps())
    out = call(serve(group, ROOT), "feedback", task_id="t1", verdict="reject", note="No.", source="human")
    assert out == "feedback reject recorded on t1 for ceo (message fb-1, source human); it does not wake ceo"


def test_the_confirmation_receipt_carries_no_step() -> None:
    steps = ScriptedSteps(feedback=FEEDBACK_STEP)
    group, _ = tools(steps=steps)
    out = call(serve(group, ROOT), "feedback", task_id="t1", verdict="reject", note="Yes.", source="human", criterion=["C1"], confirms="m-9")
    assert out == "recorded: rejection m-9 is about C1 (source human; message fb-1); it does not wake ceo" and steps.asked == []


def test_root_define_service_reply_has_no_step() -> None:
    """An amendment can no longer precede the user's yes (the gate refuses it), so root is told nothing to do next: the reply is the service's own."""
    steps = ScriptedSteps(feedback=FEEDBACK_STEP, rework=REWORK_STEP)
    group, _ = tools(steps=steps)
    out = call(serve(group, ROOT), "define_service", owner="ceo", name="brief", add_acceptance=["x"])
    assert out == "defined brief" and steps.asked == []


@pytest.mark.parametrize("error", [OrgError("the cases cannot be read"), OSError("disk")], ids=["OrgError", "OSError"])
def test_a_failing_step_never_fails_the_call(error: BaseException) -> None:
    group, commands = tools(steps=ScriptedSteps(feedback=FEEDBACK_STEP, raises=error))
    server = serve(group, ROOT)
    out = call(server, "feedback", task_id="t1", verdict="reject", note="No.", source="human", criterion=["C1"])
    assert out == "feedback reject recorded on t1 for ceo (message fb-1, source human, about C1 (not confirmed)); it does not wake ceo"
    assert call(server, "define_service", owner="ceo", name="brief", add_acceptance=["x"]) == "defined brief"
    assert [c[0] for c in commands.calls] == ["feedback", "define_service"]  # both were recorded: the receipt is what happened


def test_a_bug_in_a_step_is_not_hidden() -> None:
    group, commands = tools(steps=ScriptedSteps(raises=ValueError("a bug in the step text")))
    server = serve(group, ROOT)
    assert "a bug in the step text" in fails(server, "feedback", task_id="t1", verdict="reject", note="No.", source="human", criterion=["C1"])
    assert call(server, "define_service", owner="ceo", name="brief", add_acceptance=["x"]) == "defined brief"  # no step is asked after an amendment


def test_an_agent_clients_replies_carry_no_step() -> None:
    steps = ScriptedSteps(feedback=FEEDBACK_STEP, rework=REWORK_STEP)
    group, _ = tools(steps=steps)
    server = serve(group, "ceo")
    assert call(server, "feedback", task_id="t1", verdict="reject", note="No.") == "feedback reject recorded on t1 for ceo (message fb-1); it does not wake ceo"
    assert call(server, "define_service", owner="ceo/eng", name="brief", add_acceptance=["x"]) == "defined brief"
    assert steps.asked == []


def test_a_relayed_rework_reply_repeats_the_client_questions() -> None:
    steps = ScriptedSteps(rework=REWORK_STEP)
    group, _ = tools(steps=steps)
    out = call(serve(group, ROOT), "request", service="brief", revises="old")
    assert out.endswith(f"Call start() if the scheduler is not running.\ncase total: 3 of 9\n{REWORK_STEP}")  # after the case total
    assert steps.asked == [("rework", "req-1")]
    plain = call(serve(group, ROOT), "request", service="brief")
    assert "asked the client" not in plain and steps.asked == [("rework", "req-1")]  # not a rework: no step is asked
    bare = call(serve(tools(steps=ScriptedSteps())[0], ROOT), "request", service="brief", revises="old")
    assert bare.endswith("Call start() if the scheduler is not running.\ncase total: 3 of 9")  # nothing to repeat: the reply is as before


def test_a_human_reworks_step_is_appended_after_the_case_total_like_the_relayed_one() -> None:
    """D-E5-1 (4.5): whatever the step is (the client questions of a relayed rework, the top-up of the user's), the reply puts it after the total."""
    steps = ScriptedSteps(rework=REWORK_STEP)
    group, commands = tools(steps=steps)
    out = call(serve(group, ROOT), "request", service="brief", revises="old", source="human")
    assert out.endswith(f"Call start() if the scheduler is not running.\ncase total: 3 of 9\n{REWORK_STEP}") and steps.asked == [("rework", "req-1")]


def test_an_agents_rework_reply_carries_no_client_questions() -> None:
    steps = ScriptedSteps(rework=REWORK_STEP)
    out = call(serve(tools(steps=steps)[0], "ceo"), "request", service="brief", revises="old")
    assert out.endswith("Your budget is now 5.\ncase total: 3 of 9") and steps.asked == []


@pytest.mark.parametrize("error", [OrgError("the result cannot be read"), OSError("disk")], ids=["OrgError", "OSError"])
def test_a_failing_rework_step_never_fails_the_request(error: BaseException) -> None:
    group, commands = tools(steps=ScriptedSteps(rework=REWORK_STEP, raises=error))
    out = call(serve(group, ROOT), "request", service="brief", revises="old")
    assert out.endswith("Call start() if the scheduler is not running.\ncase total: 3 of 9")
    assert [c[0] for c in commands.calls] == ["request"]  # the rework was sent: the reply is what happened
