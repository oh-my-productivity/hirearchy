"""The public surface of ``health``: how well each agent and each branch of the organization is doing, measured from the files alone.

Everything here is read-only and derived from message files and run logs (nothing is persisted):

* a run starts at the timestamp in its log file name and ends at the log's mtime;
* an *empty* run is one during which the agent sent no message. Runs that failed (crash, timeout, kiro missing) and runs woken only by
  runtime notes (stall reminders, reviews, refunds) are not the agent's doing and are left out of the waste and cost statistics
  (``expensive``); ``runs_used`` itself still counts every run (it is the budget);
* a task counts once, by its *latest* result: a ``blocked`` that was superseded by ``done`` is a ``done``;
* *rework* is a received task that carries ``revises`` (a manager sent earlier work back). Rework that comes from the client of a
  service case - a rework request after a delivery that was reported ``done``, and the re-checks the owner sends its team while it
  handles such a request - is counted apart (``client_rework``) and is not held against the agent: the client's rejection says nothing
  about the reviewer's or the writer's own quality.

* ``low_quality`` is judged on *escapes*, not on failed, blocked or reworked tasks: a delivery of a service that the human client rejected
  after the team reported it ``done``, counted for the owner and for the verifier that signed it off (``escapes``, ``judged``). The
  re-checks a FAIL caused and the author runs they cost (``rechecks``, ``rework_runs``) are shown next to it. Honest ``blocked`` and
  ``failed`` are never penalized, and an organization without service verdicts never gets the flag.

Thresholds come from ``HEALTH_DEFAULTS`` overridden by the ``health:`` mapping in ORG.md frontmatter. ``HealthAnalyzer`` measures,
``HealthRenderer`` writes the report as text (``OrgHealth.to_dict`` is the JSON form), ``HealthThresholds`` says where the flags start.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Protocol, cast, runtime_checkable

from ..kernel import ROOT, JsonObject
from ._json import plain

__all__ = [
    "FLAGS",
    "HEALTH_DEFAULTS",
    "AgentHealth",
    "BranchHealth",
    "HealthAnalyzer",
    "HealthRenderer",
    "HealthReport",
    "HealthThresholds",
    "OrgHealth",
]

HEALTH_DEFAULTS: dict[str, float] = {
    "stuck_after_seconds": 1800,  # open task older than this, with nothing in progress -> stuck
    "max_runs_per_task": 5,  # runs used per result sent -> expensive
    "max_runs_without_result": 6,  # runs since the last result while holding an open task -> expensive
    "max_escape_ratio": 0.5,  # escapes / judged deliveries it signed off -> low_quality
    "min_judged_for_quality": 3,  # judged deliveries before low_quality can fire
    "max_empty_run_ratio": 0.5,  # empty runs / runs used -> wasteful
    "min_runs_for_waste": 4,  # runs used before wasteful can fire
    "idle_after_seconds": 86400,  # no work and no activity for this long -> idle (candidate to retire)
    "stranded_after_seconds": 1800,  # budget left, no work and no activity for this long -> stranded_budget
}

FLAGS = ("stuck", "out_of_budget", "paused", "low_quality", "expensive", "wasteful", "stranded_budget", "idle")  # worst first


@dataclass
class AgentHealth:
    addr: str
    depth: int
    state: str
    budget_left: int | None
    budget_received: int
    runs_used: int
    tasks_received: int
    open_tasks: int
    oldest_open_age: float | None  # seconds
    done: int
    failed: int
    blocked: int
    runs_per_task: float | None  # runs used / results sent; None without results
    rework: int  # received tasks that revise an earlier one (client-driven ones excluded: see client_rework)
    empty_runs: int  # runs that sent no message (failed runs and runs that only handled runtime notes excluded)
    last_activity: datetime | None
    since_activity: float | None  # seconds
    flags: dict[str, str] = field(default_factory=dict)  # flag -> human reason
    failed_runs: int = 0  # runs that crashed, failed to start, timed out or were interrupted (not the agent's fault)
    runtime_runs: int = 0  # runs woken only by runtime notes (budget, stall, review): sending nothing is fine
    client_rework: int = 0  # received reworks that stem from the client of a service case (not counted in ``rework``)
    escapes: int = 0  # judged service deliveries it signed off (or owned) that the human client rejected after ``done``
    judged: int = 0  # service deliveries it signed off (or owned) that the human client gave a verdict on
    rechecks: int = 0  # received reworks of a check it had reported done, after the owner sent the author a rework (a FAIL)
    rework_runs: int = 0  # runs of the authors between each such FAIL and the re-check

    @property
    def worst_flag(self) -> str | None:
        return next((f for f in FLAGS if f in self.flags), None)


@dataclass
class BranchHealth:
    addr: str  # the branch root ("root" = the whole organization)
    agents: int
    runs_used: int
    open_tasks: int
    done: int
    failed: int
    blocked: int
    rework: int
    worst_flag: str | None


@runtime_checkable
class HealthReport(Protocol):
    """What a health report can show of itself besides its numbers: who is flagged, and the JSON-able form of all of it."""

    @property
    def flagged(self) -> list[AgentHealth]:
        """The agents with at least one flag."""
        ...

    def to_dict(self) -> JsonObject:
        """Plain JSON-able structure (datetimes as ISO strings), with ``flagged`` as the list of addresses."""
        ...


@dataclass
class OrgHealth(HealthReport):
    root: str
    now: datetime
    agents: list[AgentHealth]  # parents before children
    branches: dict[str, BranchHealth]  # branch root address -> totals over it and its subtree

    @property
    def flagged(self) -> list[AgentHealth]:
        return [a for a in self.agents if a.flags]

    def to_dict(self) -> JsonObject:
        """Plain JSON-able structure (datetimes as ISO strings)."""
        return cast(JsonObject, plain(asdict(self) | {"flagged": [a.addr for a in self.flagged]}))


@runtime_checkable
class HealthThresholds(Protocol):
    def thresholds(self) -> dict[str, float]:
        """``HEALTH_DEFAULTS`` merged with the ``health:`` mapping of ORG.md. A value that is not a finite number (a typo, a boolean, a
        word) falls back to its default, so that a mistake in ORG.md cannot break health. Numeric strings count as numbers."""
        ...


@runtime_checkable
class HealthAnalyzer(Protocol):
    def agent_health(self, addr: str, now: datetime | None = None, limits: Mapping[str, float] | None = None) -> AgentHealth:
        """Metrics and flags for one agent. ``now`` defaults to the clock (a naive one is taken as UTC), ``limits`` to the thresholds.
        Raises ``OrgError`` for ``root`` (the human has no health data) and for an agent that does not exist."""
        ...

    def org_health(self, root: str = ROOT, now: datetime | None = None) -> OrgHealth:
        """Health of ``root`` and everything below it (``root`` = the whole organization, the human excluded), with the totals of every
        branch: parents before children."""
        ...


@runtime_checkable
class HealthRenderer(Protocol):
    def render_text(self, health: OrgHealth) -> str:
        """The human report: a summary line, then one line per agent (indented by depth) with its branch totals, flags and reasons."""
        ...
