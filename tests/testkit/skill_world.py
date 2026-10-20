"""What the tests of the skill (and of the tools that name it) need from the application: the packaged SKILL.md, its installation, and an MCP server over an ``Org``.

All of it is made by the composition root; none of it goes through the former module names (``orgmcp.skill.skill_source``, ``orgmcp.skill.install_skill``,
``orgmcp.server.build_server``). The skill ports need no organization, so they are taken from the runtime of the working directory (nothing is read there).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from orgmcp.app import wire_mcp_server, wire_skill, wire_stalls, wiring
from orgmcp.mcp_server._binding import OpenerBindings
from orgmcp.skill._source import PackagedSkillSource


def skill_source() -> Path:
    """The SKILL.md that ships with this install: inside the package (wheel) or in the source checkout."""
    return PackagedSkillSource(wire_skill.package_dir()).path()


def install_skill(dest: str | Path | None = None, force: bool = False) -> str:
    """Copy the skill to ``<dest>/orgmcp/SKILL.md`` (default dest: ``~/.kiro/skills``). Returns what to print."""
    return wiring.open_runtime(Path.cwd()).skill_installer.install_skill(dest, force)


def build_server(org: Any, me: str) -> Any:
    """The MCP server for ``me`` over the runtime of ``org`` (as the CLI's ``orgmcp mcp`` builds it, with the organization already opened)."""
    binding = OpenerBindings(wire_mcp_server.RuntimeOrgOpener()).bind(org.root, wire_stalls.RuntimePorts(org.runtime))
    return wire_mcp_server.server_factory(binding).build(me)
