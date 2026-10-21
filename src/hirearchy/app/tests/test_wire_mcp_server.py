"""``wire_mcp_server``: the server over the ports of a real organization - its tools by role, the runtime opened by the binding and never by the server before
it is asked, the plan before there is an organization, the control of the scheduler, the binding of the environment, the process that serves."""

from __future__ import annotations

import asyncio
import dataclasses
import sys
from pathlib import Path
from typing import Any, cast

import pytest
from mcp.server.fastmcp import FastMCP

from hirearchy.app import Org, wire_mcp_server, wiring
from hirearchy.daemon import SchedulerControl
from hirearchy.daemon.testing import FakeSchedulerControl
from hirearchy.kernel import ROOT, OrgError
from hirearchy.mcp_server import BindingResolver, McpServerFactory, McpServerRunner, OrgBindingPort
from hirearchy.mcp_server._instructions import INSTRUCTIONS, ROOT_INSTRUCTIONS
from hirearchy.telemetry import ProcessLabel
from testkit.mcp_server_world import OrgBinding, build_server, resolve_binding


def call(server: FastMCP, tool: str, **arguments: Any) -> str:
    result = asyncio.run(server.call_tool(tool, arguments))
    blocks = result[0] if isinstance(result, tuple) else result
    return "\n".join(getattr(block, "text", "") for block in blocks)


def tool_names(server: FastMCP) -> list[str]:
    return [tool.name for tool in asyncio.run(server.list_tools())]


@pytest.fixture
def team(tmp_path: Path) -> Org:
    made = Org.init(tmp_path / "org", "mission")
    made.hire(ROOT, "ceo", "Chief", "Lead.", can_hire=True)
    made.hire("ceo", "eng", "Engineer", "Build.")
    return made


@pytest.fixture
def opened(monkeypatch: pytest.MonkeyPatch) -> list[Path]:
    """The roots ``open_runtime`` was called for, by the opener of the server."""
    roots: list[Path] = []
    real = wiring.open_runtime

    def counting(root: Path, overrides: Any = None) -> Any:
        roots.append(root)
        return real(root, overrides)

    monkeypatch.setattr(wire_mcp_server, "open_runtime", counting)
    return roots


def test_the_wiring_makes_the_four_roles_of_the_entry_point(team: Org) -> None:
    binding = OrgBinding(team.root, team)
    assert isinstance(binding, OrgBindingPort)
    assert isinstance(wire_mcp_server.server_factory(binding), McpServerFactory)
    assert isinstance(wire_mcp_server.binding_resolver(), BindingResolver)
    assert isinstance(wire_mcp_server.mcp_server_runner(), McpServerRunner)


def test_the_tools_of_each_role(team: Org) -> None:
    def tools(me: str) -> list[str]:
        return tool_names(cast(FastMCP, wire_mcp_server.server_factory(OrgBinding(team.root, team)).build(me)))

    assert tools(ROOT) == ["whoami", "inbox", "delegate", "report", "send", "reclaim", "hire", "retire", "read", "write", "status", "health", "services",
                           "define_service", "request", "feedback", "observe", "create_org", "start", "stop", "blueprint_example", "propose_org",
                           "apply_org", "progress"]
    assert tools("ceo") == ["whoami", "inbox", "delegate", "report", "send", "reclaim", "hire", "retire", "read", "write", "status", "health", "services",
                            "define_service", "request", "feedback"]
    assert tools("ceo/eng") == ["whoami", "inbox", "delegate", "report", "send", "reclaim", "hire", "retire", "read", "write", "status", "health"]


def test_the_instructions_are_the_texts_of_the_package(team: Org) -> None:
    factory = wire_mcp_server.server_factory(OrgBinding(team.root, team))
    assert cast(FastMCP, factory.build("ceo")).instructions == INSTRUCTIONS
    assert cast(FastMCP, factory.build(ROOT)).instructions == ROOT_INSTRUCTIONS.format(where=f"The organization is at {team.root}.")


def test_a_server_before_the_organization_exists_opens_nothing(tmp_path: Path, opened: list[Path]) -> None:
    binding = OrgBinding(tmp_path / "later", None, pinned=True)
    server = cast(FastMCP, wire_mcp_server.server_factory(binding).build(ROOT))
    assert call(server, "whoami").startswith("Setup: no organization exists")
    assert call(server, "progress").startswith("Setup: no organization exists")
    assert opened == [] and not (tmp_path / "later").exists()


def test_the_runtime_is_opened_once_and_the_ports_when_a_tool_first_needs_them(team: Org, opened: list[Path]) -> None:
    server = cast(FastMCP, wire_mcp_server.server_factory(OrgBinding(team.root, None)).build("ceo"))
    assert opened == [team.root]  # to know that the agent exists
    call(server, "whoami")
    call(server, "status")
    call(server, "inbox")
    assert opened == [team.root]  # one runtime for the life of the server, whatever the tools


def test_a_root_server_finds_the_organization_when_it_appears(tmp_path: Path) -> None:
    binding = OrgBinding(tmp_path / "org", None)
    server = cast(FastMCP, wire_mcp_server.server_factory(binding).build(ROOT))
    with pytest.raises(Exception, match="no organization at"):
        call(server, "inbox")
    Org.init(tmp_path / "org", "made by someone else")
    assert call(server, "inbox") == "(no new messages)"


def test_the_plan_is_proposed_before_there_is_an_organization_and_applied_after_create_org(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HIREARCHY_WORKSPACE_ROOTS", str(tmp_path))
    monkeypatch.chdir(tmp_path)
    binding = OrgBinding(tmp_path / "org", None, pinned=True)
    server = cast(FastMCP, wire_mcp_server.server_factory(binding).build(ROOT))
    blueprint = call(server, "blueprint_example", kind="research")
    proposal = call(server, "propose_org", blueprint=blueprint)
    assert "PLAN FOR YOU" in proposal and f"Target organization: {tmp_path / 'org'} (none yet:" in proposal
    plan_id = next(line.split(": ", 1)[1] for line in proposal.splitlines() if line.startswith("plan_id: "))
    with pytest.raises(Exception, match="there is no organization yet"):
        call(server, "apply_org", blueprint=blueprint, approved=True, plan_id=plan_id)
    call(server, "create_org", mission="A mission")
    applied = call(server, "apply_org", blueprint=blueprint, approved=True, plan_id=plan_id)
    assert applied.startswith(f"applied the blueprint to {(tmp_path / 'org').resolve()}")
    assert f"Target organization: {(tmp_path / 'org').resolve()} (exists," in call(server, "propose_org", blueprint=blueprint)


def test_plan_time_parts_are_the_defaults_of_an_organization_that_does_not_exist_yet() -> None:
    parts = wire_mcp_server.plan_time_parts()
    assert parts.identity.plan_id({"mission": "m"}) == parts.identity.plan_id({"mission": "m"})
    assert wire_mcp_server.CachedPlanTime().get().renderer is not None


def test_the_start_tool_calls_the_control_of_the_runtime(team: Org) -> None:
    team.delegate(ROOT, "ceo", "T", "g", "a", budget=2)
    fake = FakeSchedulerControl()
    team.runtime = _replace(team, fake)
    server = cast(FastMCP, wire_mcp_server.server_factory(OrgBinding(team.root, team)).build(ROOT))
    assert "scheduler started (pid 4242" in call(server, "start", max_runs=1)
    assert fake.starts == [(1, True)]


def _replace(org: Org, scheduler_control: SchedulerControl) -> Any:
    """The runtime of ``org`` with another control of the scheduler."""
    return dataclasses.replace(org.runtime, scheduler_control=scheduler_control)


def test_a_binding_over_an_org_or_over_a_root_that_may_not_exist_creates_it(tmp_path: Path) -> None:
    unbound = OrgBinding(None, None)
    assert unbound.root is None and not unbound.pinned and unbound.peek() is None
    binding = OrgBinding(tmp_path / "org", pinned=True)
    created = binding.create("A mission", "a-model")
    assert isinstance(created, Org) and created.config["default_model"] == "a-model"
    assert binding.get().root == created.root and binding.pinned
    org = Org(created.root)
    assert OrgBinding(org.root, org).get().root == org.root


def test_the_binding_is_found_from_the_environment(team: Org, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ORG_ROOT", str(team.root))
    monkeypatch.delenv("ORG_AGENT", raising=False)
    monkeypatch.delenv("ORG_REQUIRE_AGENT", raising=False)
    binding, me = resolve_binding()
    assert isinstance(binding, OrgBinding) and me == ROOT and binding.pinned and binding.get().root == team.root
    monkeypatch.setenv("ORG_AGENT", "ceo/eng")
    binding, me = resolve_binding()
    assert me == "ceo/eng" and binding.pinned
    monkeypatch.setenv("ORG_REQUIRE_AGENT", "1")
    monkeypatch.setenv("ORG_AGENT", "")
    with pytest.raises(OrgError, match="ORG_REQUIRE_AGENT is set but ORG_AGENT does not name an agent"):
        resolve_binding()


def test_an_agent_that_does_not_exist_cannot_be_served(team: Org) -> None:
    with pytest.raises(OrgError, match="no such agent: nobody"):
        build_server(team, "nobody")
    with pytest.raises(OrgError, match="no organization at"):
        build_server(OrgBinding(team.root.parent / "missing"), "ceo")


def test_the_process_that_serves_is_named_mcp_and_runs_the_server_of_the_environment(team: Org, monkeypatch: pytest.MonkeyPatch) -> None:
    ran: list[tuple[str, str | None]] = []
    monkeypatch.setattr(FastMCP, "run", lambda self, *a, **k: ran.append((self.name, self.instructions)))
    monkeypatch.setenv("ORG_ROOT", str(team.root))
    monkeypatch.setenv("ORG_AGENT", "ceo")
    monkeypatch.delenv("ORG_REQUIRE_AGENT", raising=False)
    wire_mcp_server.serve()
    assert wiring.process_resources().process_label.get() == "mcp" and isinstance(wiring.process_resources().process_label, ProcessLabel)
    assert ran == [("hirearchy", INSTRUCTIONS)]


def test_the_heavy_modules_are_loaded_when_a_server_is_made_not_when_the_application_is() -> None:
    import subprocess

    code = ("import sys; import hirearchy.app; "
            "print('mcp.server.fastmcp' in sys.modules, 'hirearchy.mcp_server._factory' in sys.modules, 'hirearchy.mcp_server._tools_services' in sys.modules)")
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True).stdout.strip()
    assert out == "False False False"
