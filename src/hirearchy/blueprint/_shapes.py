"""The shapes of the dictionaries that the budget estimate and the access report hand out (package-private data)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import TypedDict

from ..kernel import JsonObject
from .api import Agent, Issue

AgentRuns = TypedDict("AgentRuns", {"pass": int, "rework": int, "total": int})  # ``pass`` is a keyword: the functional form


class Estimate(TypedDict):
    """Runs one pass plus one rework cycle needs: per agent, and in total."""

    per: dict[str, AgentRuns]
    total: int


class Split(TypedDict):
    """What the parent hands down at first, and what the agent keeps for itself."""

    grant: int
    keeps: int


class AccessFacts(TypedDict):
    """What the runtime lets an agent reach with kiro's file tools."""

    write: tuple[bool, str | None]  # (granted, the only folder it may change)
    read: tuple[bool, list[str]]  # (granted, every folder kiro lets it read)
    org: bool  # can open the organization's own files (any tool)
    inputs: list[str]  # read-only folders
    inputs_via_hirearchy: bool  # inputs it can only open with hirearchy `read`
    shell: tuple[bool, str | None]  # (granted, where it is told to stay; not enforced)
    web: list[str]


@dataclass
class Built:
    """What an application has made so far: the one record the rollback works from (it grows step by step, so a failure leaves it as far as it got)."""

    created: list[str] = field(default_factory=list)  # addresses of the agents hired, parents first
    made_dirs: list[Path] = field(default_factory=list)  # directories made for workspaces, the deepest of each first
    defined: list[str] = field(default_factory=list)  # names of the services defined


@dataclass(frozen=True)
class Held:
    """What an existing agent holds and has (read from its charter): the bound on what a new report of it may be given."""

    addr: str
    tools: tuple[str, ...]
    workspace: str | None
    inputs: tuple[str, ...]
    can_hire: bool
    max_children: int
    reports: int  # its direct reports now
    verifier: bool


@dataclass(frozen=True)
class LimitChange:
    """A ``limits`` entry of an existing agent: the new values (None: kept) and the ones it has now."""

    agent: str
    can_hire: bool | None
    max_children: int | None
    was_can_hire: bool
    was_max_children: int


@dataclass(frozen=True)
class DepthChange:
    value: int
    was: int


@dataclass(frozen=True)
class Retiring:
    agent: str
    reason: str
    team: tuple[str, ...]  # the agent and everything below it, the agent first


@dataclass(frozen=True)
class AddedService:
    """A service an extension defines for an existing top-level agent."""

    owner: str
    name: str
    entry: JsonObject  # the entry as written (its criteria in their forms)
    where: str  # issue path
    budget: int  # runs per request, resolved against the owner's team after the extension
    continues: tuple[str, ...] | None = None  # the criteria of the retired copy the definition continues; None: a new service


@dataclass(frozen=True)
class BudgetChange:
    owner: str
    service: str
    budget: int
    was: int


@dataclass(frozen=True)
class ServiceRetire:
    owner: str
    service: str
    reason: str


@dataclass(frozen=True)
class CharterLine:
    """A line an extension adds to (or takes out of) the added section of an agent's charter."""

    agent: str
    line: str


@dataclass(frozen=True)
class AddedChecker:
    """A verifier an extension adds under an agent that offers services: the agent is told, and gets a line about it."""

    agent: str  # the verifier's address
    owner: str  # the agent that offers the services
    services: tuple[str, ...]


@dataclass(frozen=True)
class RootTask:
    """A one-off task of root as a criterion may be copied from it (design 5.2 ``criterion-tasks``)."""

    id: str
    created: datetime | None
    criteria: tuple[str, ...]  # the lines of its ``## Acceptance criteria`` section


@dataclass
class Extension:
    """An extension blueprint read against the organization (design 5.2): its problems, and what its entries mean once they are valid."""

    issues: list[Issue] = field(default_factory=list)
    reason: str = ""
    agents: list[Agent] = field(default_factory=list)  # the agents it adds, parents first, at their full addresses (``parent`` None: under root)
    extras: dict[str, str] = field(default_factory=dict)  # the ``charter_extra`` of an added agent, by address
    limits: list[LimitChange] = field(default_factory=list)
    depth: DepthChange | None = None
    retires: list[Retiring] = field(default_factory=list)
    services: list[AddedService] = field(default_factory=list)
    budgets: list[BudgetChange] = field(default_factory=list)
    service_retires: list[ServiceRetire] = field(default_factory=list)
    lines: list[CharterLine] = field(default_factory=list)  # added to the added section, in the order written
    removals: list[CharterLine] = field(default_factory=list)
    checkers: list[AddedChecker] = field(default_factory=list)
    teams: dict[str, list[Agent]] = field(default_factory=dict)  # owner -> its team after the extension (the agents that stay, then the added ones)
    cap: int | None = None  # needs.budget_runs


@dataclass(frozen=True)
class ExtensionText:
    """The plan of an extension as text: the block for the user, the details for the assistant, and the problems both came from."""

    block: str
    details: str
    issues: list[Issue]
