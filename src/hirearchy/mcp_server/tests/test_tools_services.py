"""``ServiceTools``: who gets which tools (decided when the server starts), and what each tool says."""

from __future__ import annotations

import asyncio
from pathlib import Path

from hirearchy.agents.testing import MemoryAgents
from hirearchy.kernel import ROOT, Message, OrgError
from hirearchy.mcp_server._instructions import InstructionText
from hirearchy.mcp_server._tools_services import DirectoryServiceRoles, ServiceTools
from hirearchy.mcp_server.testing import HeldBudgets, MemoryBinding, ScriptedReports, agents_in
from hirearchy.services import Contract, ServiceCatalog, ServiceCommands

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


class Commands(ServiceCommands):
    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[object, ...], dict[str, object]]] = []

    def define_service(self, actor: str, owner: str, name: str, **fields: object) -> str:
        self.calls.append(("define_service", (actor, owner, name), fields))
        return f"defined {name}"

    def retire_service(self, actor: str, owner: str, name: str, reason: str) -> str:
        return "retired"

    def request(self, actor: str, service: str, inputs: object, **fields: object) -> Message:
        self.calls.append(("request", (actor, service, inputs), fields))
        return Message(actor, "ceo", "task", "", budget=9, contract=2, playbook=3, service=service, id="req-1")

    def revise_playbook(self, actor: str, service: str, content: str, reason: str) -> int:
        self.calls.append(("revise_playbook", (actor, service, content, reason), {}))
        return 4

    def feedback(self, actor: str, task_id: str, verdict: str, note: str = "") -> Message:
        self.calls.append(("feedback", (actor, task_id, verdict, note), {}))
        return Message(actor, "ceo", "note", "", id="fb-1")


def tools(agents: MemoryAgents | None = None, offered: dict[str, list[str]] | None = None, exists: bool = True,
          reports: ScriptedReports | None = None) -> tuple[ServiceTools, Commands]:
    agents, commands = agents or agents_in("ceo", "ceo/eng", "ops"), Commands()
    roles = DirectoryServiceRoles(InstructionText(MemoryBinding(Path("/o"), exists=exists)), lambda: agents, lambda: agents, lambda: Catalog(offered or {}))
    return ServiceTools(roles, lambda: reports or ScriptedReports("SERVICES", {"req-1": "case total: 3 of 9"}), lambda: commands, lambda: HeldBudgets({"ceo": 5})), commands


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


def test_a_rework_also_states_the_case_total() -> None:
    out = call(serve(tools()[0], "ceo"), "request", service="brief", revises="old")
    assert out.endswith("Your budget is now 5.\ncase total: 3 of 9")


def test_feedback_says_who_it_did_not_wake() -> None:
    assert call(serve(tools()[0], "ceo"), "feedback", task_id="t1", verdict="accept") == (
        "feedback accept recorded on t1 for ceo (message fb-1); it does not wake ceo")


def test_revise_playbook_says_the_version_and_that_the_client_was_told_quietly() -> None:
    out = call(serve(tools(offered={"ceo/eng": ["brief"]})[0], "ceo/eng"), "revise_playbook", service="brief", content="c", reason="r")
    assert out == "playbook of `brief` is now v4; ceo was told without being woken"


def test_a_missing_organization_is_the_refusal_of_a_client_tool() -> None:
    def gone() -> object:
        raise OrgError("no organization at /o yet: call create_org(mission=...) first")

    roles = DirectoryServiceRoles(InstructionText(MemoryBinding(Path("/o"))), gone, gone, gone)  # type: ignore[arg-type]
    group = ServiceTools(roles, gone, gone, gone)  # type: ignore[arg-type]
    assert "call create_org" in fails(serve(group, ROOT), "services")
