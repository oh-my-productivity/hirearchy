"""The collaborators the classes of ``blueprint`` use among themselves (package-private: nobody outside the package depends on them)."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Protocol, runtime_checkable

from ..kernel import JsonObject
from ._shapes import AccessFacts, Estimate, Split
from .api import Agent, Issue


@runtime_checkable
class OrgContext(Protocol):
    """What a blueprint is planned against: the organization it will be built in, or the defaults when there is none yet."""

    def config(self) -> JsonObject:
        """The ORG.md settings over the defaults (the defaults alone when there is no organization)."""
        ...

    def root(self) -> Path | None:
        """The organization directory; None when there is no organization (nothing for a workspace to overlap)."""
        ...

    def exists(self, addr: str) -> bool:
        """The agent ``addr`` exists in the organization."""
        ...

    def service_names(self) -> set[str]:
        """The names of the services offered by the organization's top-level agents (requests name the service only, so they are taken)."""
        ...


@runtime_checkable
class OrgContexts(Protocol):
    def context(self, org_exists: bool) -> OrgContext:
        """The organization when it exists, else the defaults of plan time before it does."""
        ...


@runtime_checkable
class TextFiles(Protocol):
    """The text files a blueprint is read from."""

    def is_file(self, path: Path) -> bool:
        """``path`` is an existing file."""
        ...

    def read(self, path: Path) -> str:
        """The text of the file (UTF-8)."""
        ...


@runtime_checkable
class WorkspaceRoots(Protocol):
    def roots(self, allowed: Sequence[str | Path] | None = None) -> list[Path]:
        """The directories workspaces and the deliverable path may be in: ``allowed`` (``~`` expanded, resolved) when given and not empty, else
        ``$ORGMCP_WORKSPACE_ROOTS``, else the home directory, the temp directory and the current directory."""
        ...


@runtime_checkable
class PathChecking(Protocol):
    def check(
        self, raw: object, where: str, issues: list[Issue], org: OrgContext, roots: Sequence[Path], *, what: str, dir_must_exist: bool,
    ) -> Path | None:
        """Resolve a user path and check it is absolute, inside an allowed root and away from the organization and ~/.kiro; the problems are
        added to ``issues``. None when it cannot be used."""
        ...


@runtime_checkable
class AgentResolution(Protocol):
    def resolve(self, bp: Mapping[str, object], org: OrgContext, roots: Sequence[Path], issues: list[Issue]) -> list[Agent]:
        """The agents of the blueprint, parents first, with their tools, workspace, inputs, authority and model settled."""
        ...


@runtime_checkable
class BudgetPlanning(Protocol):
    def estimate(self, agents: Sequence[Agent]) -> Estimate:
        """Runs one pass plus one rework cycle needs, per agent and in total."""
        ...

    def planned_total(self, bp: Mapping[str, object], est_total: int) -> int:
        """The runs of the task: its own ``budget``, else the estimate plus slack within the cap."""
        ...

    def budget_split(self, agents: Sequence[Agent], total: int) -> dict[str, Split]:
        """addr -> what the parent hands down at first, and what the agent keeps for itself."""
        ...

    def service_budget(self, sv: Mapping[str, object], est_total: int, cap: int | None) -> int:
        """The runs handed down with each request of a service: its own ``budget``, else the estimate plus slack within the cap."""
        ...

    def service_budgets(self, bp: Mapping[str, object], agents: Sequence[Agent]) -> dict[str, int]:
        """The runs per request of every service of the blueprint, by name."""
        ...


@runtime_checkable
class AccessReport(Protocol):
    def org_files_readable(self, a: Agent) -> bool:
        """The agent can open files in the organization (its own and its teammates' ``work/``) with the tools it holds."""
        ...

    def facts(self, a: Agent) -> AccessFacts:
        """What the runtime lets the agent reach with kiro's file tools: the one computation behind both lines of the plan about access."""
        ...

    def line(self, a: Agent) -> str:
        """One line on what the runtime lets the agent reach with kiro's file tools (and what it only instructs)."""
        ...


@runtime_checkable
class ServiceRules(Protocol):
    def check(
        self, bp: Mapping[str, object], agents: Sequence[Agent], tops: Sequence[Agent], cap: int | None, est_total: int, org: OrgContext,
        roots: Sequence[Path], issues: list[Issue],
    ) -> None:
        """The ``services:`` list and a first request in ``task``; the problems are added to ``issues``."""
        ...
