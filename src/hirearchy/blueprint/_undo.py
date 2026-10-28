"""``RetiringRollback``: what an application that failed midway takes back."""

from __future__ import annotations

from collections.abc import Sequence

from ..agents import AgentDirectory, AgentRegistry
from ..hierarchy import Retirement
from ..kernel import ROOT, OrgError
from ..kernel import depth as org_depth
from ..services import ServiceCommands
from ..settings import OrgLimits
from ._protocols import BuildUndoing, ExtensionUndoing
from ._shapes import Built, Undo
from .api import WorkspaceProvisioner


class RetiringRollback(BuildUndoing):
    def __init__(self, agents: AgentDirectory, retirement: Retirement, provisioner: WorkspaceProvisioner) -> None:
        self._agents = agents
        self._retirement = retirement
        self._provisioner = provisioner

    def undo(self, built: Built) -> None:
        for addr in reversed(built.created):
            if self._agents.exists(addr) and org_depth(addr) == 1:
                try:
                    self._retirement.retire(ROOT, addr, "blueprint apply failed midway; rolled back")
                except OrgError:
                    pass
        for p in built.made_dirs:  # directories this call created, if still empty
            if not self._provisioner.remove_if_empty(p):
                break


TAKEN_BACK = "the change {plan_id} was not applied"
NOT_APPLIED = "change {plan_id} (not applied)"
BUDGET_VERSIONS = "; {service} has versions v{one} and v{two} (the budget went back to {budget})"


class ExtensionUndo(ExtensionUndoing):
    """What an extension that failed midway takes back, write by write and newest first (design 5.5)."""

    def __init__(self, agents: AgentDirectory, retirement: Retirement, registry: AgentRegistry, commands: ServiceCommands, limits: OrgLimits) -> None:
        self._agents = agents
        self._retirement = retirement
        self._registry = registry
        self._commands = commands
        self._limits = limits

    def undo(self, journal: Sequence[Undo], plan_id: str) -> str:
        sentences: list[str] = []
        reason, approval = TAKEN_BACK.format(plan_id=plan_id), NOT_APPLIED.format(plan_id=plan_id)
        for w in reversed(journal):
            try:
                if w.kind == "charter":
                    self._registry.rewrite_charter(w.target, w.text)
                elif w.kind == "depth":
                    self._limits.set_max_depth(w.number)
                elif w.kind == "agent":
                    if self._agents.exists(w.target):  # a team retired with its parent is gone already
                        self._retirement.retire_team(ROOT, w.target, reason, approved_in=approval)
                elif w.kind == "service":
                    self._commands.retire_service(ROOT, w.target, w.name, reason, approved_in=approval)
                elif w.kind == "budget":
                    self._commands.define_service(ROOT, w.target, w.name, budget=w.number)
                    sentences.append(BUDGET_VERSIONS.format(service=w.name, one=w.version + 1, two=w.version + 2, budget=w.number))
            except (OrgError, OSError):
                continue  # best effort: the rest is still taken back
        return "".join(reversed(sentences))
