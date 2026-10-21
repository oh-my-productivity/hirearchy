# mypy: ignore-errors
# A test moved from tests/ by refactor step E1: not type-checked strictly (production code is). Delete the first line when this file is typed.

import asyncio

from testkit.mcp_server_world import build_server, resolve_binding


def call(server, tool, **args):
    result = asyncio.run(server.call_tool(tool, args))
    blocks = result[0] if isinstance(result, tuple) else result
    return "\n".join(getattr(b, "text", "") for b in blocks)


def test_hirearchy_write_and_read_say_they_are_organization_tools(org, monkeypatch):
    monkeypatch.setenv("ORG_ROOT", str(org.root))
    monkeypatch.setenv("ORG_AGENT", "ceo")
    server = build_server(*resolve_binding())
    tools = {t.name: t.description for t in asyncio.run(server.list_tools())}
    assert "ORGANIZATION file" in tools["write"] and "@hirearchy/write" in tools["write"] and "NOT kiro's built-in `write`" in tools["write"]
    assert "ORGANIZATION's read tool" in tools["read"] and "@hirearchy/read" in tools["read"]
    assert call(server, "write", path="ceo/MEMORY.md", content="notes") == "wrote ceo/MEMORY.md (organization file)"
    assert org.memory("ceo") == "notes"
