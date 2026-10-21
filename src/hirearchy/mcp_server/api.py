"""The public surface of ``mcp_server``: the organization's tools served over MCP for one identity.

Identity is assigned, not claimed: the scheduler starts each run with ``ORG_AGENT=<address>``. Without ``ORG_AGENT`` (e.g. registered in your own
kiro ``mcp.json``) you act as ``root``, the human.

A root server may start before any organization exists (setup mode): it then offers ``create_org`` and every other tool answers "no organization
yet". The server is bound to exactly one root path for its lifetime and never falls back to another organization. Agent servers (``ORG_AGENT``
set) still fail fast without an organization.

The entry point publishes the binding of a server to its organization (``OrgBindingPort``), the resolution of that binding and of the identity from
the environment (``BindingResolver``), the construction of the server for an identity (``McpServerFactory``) and the process that serves it
(``McpServerRunner``). Every tool group, the recorder of tool calls and the texts are private (``_tools_*``, ``_recorder``, ``_instructions``).
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable

__all__ = ["BindingResolver", "McpServerFactory", "McpServerRunner", "OrgBindingPort"]


@runtime_checkable
class OrgBindingPort(Protocol):
    """The one organization root path a server is bound to, and the organization there once it exists."""

    @property
    def root(self) -> Path | None:
        """The bound path; None only when ``ORG_ROOT`` is unset and no organization was found from the working directory (``create`` then binds it, once)."""
        ...

    @property
    def pinned(self) -> bool:
        """Bound by ``ORG_ROOT``: ``create`` may not choose another path."""
        ...

    def peek(self) -> object | None:
        """The ports of the organization if it exists (now), else None."""
        ...

    def get(self) -> object:
        """The ports of the organization, or an ``OrgError`` that says what to do while there is none."""
        ...

    def location(self) -> Path | None:
        """The root of the organization if it exists now (as the organization knows it), else None."""
        ...

    def missing_message(self) -> str:
        """Why there is no organization yet, and what to do about it."""
        ...

    def create(self, mission: str, default_model: str | None = None, path: str | None = None) -> object:
        """Create the organization this server is bound to (``create_org``): at the bound path, or at ``path`` (absolute) when the server is not
        bound to one. Refuses, with an ``OrgError`` that says why and what to do, when one exists, when the mission is empty, when the path is
        not absolute or is not the bound one, or when the directory is a file or is not empty. The binding is then fixed for the server's life."""
        ...


@runtime_checkable
class BindingResolver(Protocol):
    def resolve(self) -> tuple[OrgBindingPort, str]:
        """(binding, identity) from ``ORG_AGENT`` / ``ORG_REQUIRE_AGENT`` / ``ORG_ROOT``. Fails closed: ``ORG_REQUIRE_AGENT`` without an agent is an
        ``OrgError`` (an internal profile of the scheduler used outside it must not act as root), and an agent needs its organization."""
        ...


@runtime_checkable
class McpServerFactory(Protocol):
    def build(self, me: str) -> object:
        """The server (a ``FastMCP``) for ``me``: the tools of its role, instrumented so that every call emits a ``tool.call`` event. Root may start
        before an organization exists (setup mode); an agent that does not exist is an ``OrgError``."""
        ...


@runtime_checkable
class McpServerRunner(Protocol):
    def run(self) -> None:
        """Name the process ``mcp``, resolve the binding and the identity from the environment, build the server and serve it over stdio."""
        ...
