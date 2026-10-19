"""MCP server: the organization's system calls. The server is the package :mod:`orgmcp.mcp_server`; this module is a shim over it (until step E3).

The names below are what the tests and the old callers (``orgmcp.cli``'s ``mcp`` command, which calls ``serve``) import from here; every one is made by the
composition root (``orgmcp.app.wire_mcp_server``). ``start_scheduler`` is the patch point of the flat module: the tests replace it, and the ``start`` tool
of a server made through this module calls what it is then.
"""

from __future__ import annotations

from .app import wire_mcp_server as _wire
from .scheduler import start_scheduler as start_scheduler  # noqa: F401 - a patch point: the tests replace it

INSTRUCTIONS = _wire.INSTRUCTIONS
ROOT_INSTRUCTIONS = _wire.ROOT_INSTRUCTIONS
DS_STORE = _wire.DS_STORE
OrgBinding = _wire.LegacyOrgBinding
build_server = _wire.legacy_build_server
resolve_binding = _wire.legacy_resolve_binding
serve = _wire.serve
