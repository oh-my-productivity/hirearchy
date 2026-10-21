"""Golden: the MCP tool surface (names, parameters with types and defaults, docstrings) and the server instructions,
for root, a manager, a worker, a service owner and agents holding built-in read/write."""

import asyncio
import json

import pytest
from golden_support import check
from scenarios import BRIEF, company, dirs

from hirearchy.core import ROOT
from testkit.mcp_server_world import OrgBinding, build_server


def surface(server) -> str:
    """Instructions, then every tool in registration order: its input/output schema and its description, verbatim."""
    parts = ["### server instructions\n" + (server.instructions or "(none)")]
    for tool in asyncio.run(server.list_tools()):
        extra = {k: v for k, v in tool.model_dump(mode="json", exclude_none=True).items()
                 if k not in ("name", "description", "inputSchema", "outputSchema")}
        parts.append(
            f"### tool: {tool.name}\n"
            f"input: {json.dumps(tool.inputSchema, indent=2)}\n"
            f"output: {json.dumps(tool.outputSchema, indent=2)}\n"
            f"other: {json.dumps(extra, sort_keys=True)}\n"
            f"description:\n{tool.description}"
        )
    return "\n\n".join(parts) + "\n"


@pytest.fixture
def team(tmp_path, clock, norm):
    org = company(tmp_path, clock)
    ws, inputs = dirs(tmp_path)
    norm.add(ws, "<WS>")
    norm.add(inputs, "<INPUTS>")
    kw = dict(workspace=str(ws), inputs=[str(inputs)])
    org.hire(ROOT, "rw", "Read and write", "x", tools=["read", "write"], **kw)
    org.hire(ROOT, "rd", "Reader", "x", tools=["read"], **kw)
    org.hire(ROOT, "wr", "Writer", "x", tools=["write"], **kw)
    org.hire(ROOT, "sh", "Shell", "x", tools=["shell"], **kw)
    org.define_service(ROOT, "ceo", "weekly-brief", **BRIEF)
    norm.add(org.root, "<ORG>")
    return org


@pytest.mark.parametrize("label, who", [
    ("root", ROOT),
    ("manager", "ceo"),  # also offers a service here: the owner tools
    ("worker", "ceo/eng"),
    ("builtin_read_write", "rw"),
    ("builtin_read", "rd"),
    ("builtin_write", "wr"),
    ("builtin_shell", "sh"),
])
def test_tool_surface(label, who, team, norm):
    check(f"mcp/surface_{label}.txt", norm(surface(build_server(team, who))))


def test_tool_surface_of_a_service_free_manager(tmp_path, clock, norm):
    org = company(tmp_path, clock)
    norm.add(org.root, "<ORG>")
    check("mcp/surface_manager_without_service.txt", norm(surface(build_server(org, "ceo"))))


def test_root_surface_before_an_organization_exists(tmp_path, norm):
    where = tmp_path / "later" / "org"
    norm.add(where, "<FUTURE_ORG>")
    check("mcp/surface_root_setup_mode.txt", norm(surface(build_server(OrgBinding(where, None, pinned=True), ROOT))))
    unbound = norm(surface(build_server(OrgBinding(None, None), ROOT)))
    check("mcp/surface_root_unbound.txt", unbound)


def test_agent_instructions_are_the_short_ones(team):
    assert build_server(team, "ceo/eng").instructions.startswith("You are a member of a file-based organization of agents.")
