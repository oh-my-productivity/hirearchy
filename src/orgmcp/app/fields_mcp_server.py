"""Runtime fields of the ``mcp_server`` entry point (ARCHITECTURE.md 6.3): none."""

from __future__ import annotations

from dataclasses import dataclass

STEP: str | None = "D-mcp"  # set to the step's name when the step fills this part (see test_runtime_fields)
NOT_A_FIELD: dict[str, str] = {
    "McpServerFactory": (
        "a server is made per binding and per identity: app.wire_mcp_server.server_factory(binding) makes the factory over the ports of the "
        "organization the binding opens when a tool is first called (a factory, not a port every runtime has)"
    ),
    "BindingResolver": "it makes the binding of a process from its environment, before any runtime exists: app.wire_mcp_server.binding_resolver()",
    "OrgBindingPort": "the binding is what opens the runtime (the organization may not exist yet): app.wire_mcp_server.RuntimeOrgOpener",
    "McpServerRunner": "the process that serves one identity over stdio: app.wire_mcp_server.mcp_server_runner()",
}


@dataclass(frozen=True)
class Fields:
    """No field: the server is built by ``wire_mcp_server.server_factory`` over the ports of the runtime its binding opens."""
