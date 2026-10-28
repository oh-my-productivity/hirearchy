"""The roles the server is made of (private: this package is their only consumer).

A tool group is one class with one Protocol (``ToolGroup``); it receives what it needs as ``Provider`` thunks of the narrow ports of the features, which
call the binding at tool-call time, so a server opens the runtime of its organization on its first tool call and a root server may start before there
is one. The rest are the small roles around the groups: the texts, the recorder of tool calls, the resolution of the request a call belongs to, who
gets the service tools, and where the examples of blueprints go.

The docstring of a tool is the description the client is shown, byte for byte (golden): the continuation lines of the docstrings in ``_tools_*`` keep the column
they had when the tools were the closures of one function, which is why they do not line up with the ``def`` above them.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import TYPE_CHECKING, Protocol, TypeVar, runtime_checkable

from .api import McpServerFactory, OrgBindingPort

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

T = TypeVar("T")


@runtime_checkable
class OrgPorts(Protocol):
    """An opened organization: its root and the one object of each port (the runtime of the composition root answers so)."""

    @property
    def root(self) -> Path: ...

    def get(self, port: type[T]) -> T: ...


@runtime_checkable
class OrgOpener(Protocol):
    def open(self, root: Path) -> OrgPorts:
        """The ports of the organization at ``root``; an ``OrgError`` ("not an organization (no ORG.md)") when there is none."""
        ...

    def initialize(self, root: Path, mission: str, config: Mapping[str, object] | None) -> None:
        """Make ``root`` an organization (``OrgError`` if it already is; ``OSError`` if it cannot be written)."""
        ...


@runtime_checkable
class BindingFactory(Protocol):
    def bind(self, root: Path | None, ports: OrgPorts | None = None, pinned: bool = False) -> OrgBindingPort:
        """The binding of a server to ``root`` (``ports``: the organization there, if it is known to exist)."""
        ...


@runtime_checkable
class ServerFactories(Protocol):
    def factory_for(self, binding: OrgBindingPort) -> McpServerFactory:
        """The factory of servers bound to ``binding``."""
        ...


@runtime_checkable
class ToolGroup(Protocol):
    def register(self, mcp: FastMCP, me: str) -> None:
        """Register this group's tools for ``me`` (decided when the server starts, which is at the start of each run)."""
        ...


@runtime_checkable
class ToolRecorder(Protocol):
    def instrument(self, mcp: FastMCP, me: str) -> None:
        """Make every tool registered afterwards (by anyone) emit a ``tool.call`` event."""
        ...


@runtime_checkable
class CallTrace(Protocol):
    def of(self, me: str, arguments: Mapping[str, object], seen: Sequence[str | None]) -> str | None:
        """The request a tool call belongs to: the trace of the message it delivered (``seen``), else of the message it names (``task_id`` /
        ``reply_to`` / ``revises``), else the one trace of the caller's current batch. None when unknown."""
        ...


@runtime_checkable
class ServerInstructions(Protocol):
    def for_identity(self, me: str) -> str:
        """The instructions the server sends on every connection: the short ones for an agent, the workflow of the human's seat for root."""
        ...


@runtime_checkable
class SetupMode(Protocol):
    def active(self) -> bool:
        """No organization exists (yet): a root server offers ``create_org`` and the other tools say so."""
        ...

    def state(self) -> str:
        """What ``whoami`` / ``status`` / ``progress`` say before an organization exists."""
        ...


@runtime_checkable
class ServiceRoles(Protocol):
    def manager(self, me: str) -> bool:
        """``me`` is root, or has direct reports, or may hire: it gets the tools of a client of services."""
        ...

    def owner(self, me: str) -> bool:
        """``me`` offers a service: it gets the tool that revises its playbook."""
        ...


@runtime_checkable
class ExampleLocation(Protocol):
    def base(self) -> Path:
        """Where the examples put ``deliverables/`` and project folders: the user's current directory, unless that is the organization itself or a
        filesystem root (then the home directory)."""
        ...


@runtime_checkable
class ExampleText(Protocol):
    def example(self, kind: str, service: bool) -> str:
        """``blueprint_example``: the template of ``kind`` with its paths under the base of the examples."""
        ...


@runtime_checkable
class PlanProposal(Protocol):
    def propose(self, blueprint: str, extend: str | None = None) -> str:
        """``propose_org``: validate the blueprint text and return the plan the user must approve (works before the organization exists). With
        ``extend`` (``"current"`` or the path of the bound organization) the blueprint is an extension of that organization (design 5), and any other
        use of an extension, or of ``extend``, is refused with the texts of 5.6."""
        ...


@runtime_checkable
class PlanApplication(Protocol):
    def apply(self, blueprint: str, approved: bool, plan_id: str | None) -> str:
        """``apply_org``: create what the approved blueprint describes. Refuses, with what to do, unless the user approved it, the ``plan_id`` is
        the one of this blueprint, and the organization exists. An extension is applied by the extension applier, which makes the ``plan_id``
        comparison itself against the organization as it is now (design 5.5 step 2)."""
        ...


@runtime_checkable
class PlanTarget(Protocol):
    def line(self, extending: bool = False) -> str:
        """The ``Target organization:`` line of a proposal: where it will be applied, and whether that exists (``extending``: the plan changes it)."""
        ...

    def bound(self) -> Path | None:
        """The organization this server is bound to when it exists, else None."""
        ...


@runtime_checkable
class StructureGuard(Protocol):
    def hire(self, me: str) -> None:
        """Refuse, with an ``OrgError`` that says what to do instead, a ``hire`` that ``me`` may not make over MCP (root's: a new agent changes the
        organization, so the user approves it in a plan). Returns when ``me`` may hire."""
        ...

    def retire(self, me: str, name: str) -> None:
        """The same for ``retire`` of ``name`` (a short name or an address)."""
        ...

    def new_service(self, me: str, owner: str, name: str) -> None:
        """The same for ``define_service`` of ``name`` for ``owner``, when ``owner`` offers no service of that name (a first definition). An
        amendment of a service that exists is never refused here."""
        ...


@runtime_checkable
class InstalledSkill(Protocol):
    def stale(self) -> Path | None:
        """The installed assistant skill when it differs from the one this server ships; None otherwise."""
        ...
