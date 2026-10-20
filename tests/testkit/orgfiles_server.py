"""The MCP server of an ``Org`` for the orgfiles tests of the ``write`` tool (the reply that lists the kept and changed keys of a charter).

``build_server(org, me)`` is what ``orgmcp.server.build_server`` was: the server for the identity ``me`` over the ports of ``org.runtime``, made by the
composition root (``wire_mcp_server.server_factory``) from a binding to that runtime.
"""

from __future__ import annotations

from orgmcp.app import wire_mcp_server
from orgmcp.app.wire_stalls import RuntimePorts
from orgmcp.mcp_server._binding import OrgBinding


def build_server(org, me: str):
    binding = OrgBinding(org.root, wire_mcp_server.RuntimeOrgOpener(), RuntimePorts(org.runtime), False)
    return wire_mcp_server.server_factory(binding).build(me)
