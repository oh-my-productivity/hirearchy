"""The shapes of the dictionaries that the budget estimate and the access report hand out (package-private data)."""

from __future__ import annotations

from typing import TypedDict

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
    inputs_via_orgmcp: bool  # inputs it can only open with orgmcp `read`
    shell: tuple[bool, str | None]  # (granted, where it is told to stay; not enforced)
    web: list[str]
