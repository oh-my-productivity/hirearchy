"""Membership of the agent tree: hire and retire (hierarchy).

The bodies call the ports of ``self.runtime`` (step B-hierarchy; ARCHITECTURE.md 5.3 and 6.4). ``Retired`` lives in ``hirearchy.hierarchy`` and is re-exported
here, where ``hirearchy.core`` finds it."""

from __future__ import annotations

from ..hierarchy import Retired
from .runtime import OrgRuntime

__all__ = ["HierarchyMixin", "Retired"]


class HierarchyMixin:
    """Membership of the agent tree: hire and retire (hierarchy)."""

    runtime: OrgRuntime

    def hire(
        self,
        actor: str,
        name: str,
        role: str,
        charter: str,
        *,
        model: str | None = None,  # None = the org's default model (DEFAULT_MODEL unless ORG.md sets another)
        tools: list[str] | None = None,
        can_hire: bool = False,
        max_children: int = 5,
        workspace: str | None = None,
        inputs: list[str] | None = None,
    ) -> str:
        return self.runtime.hiring.hire(
            actor, name, role, charter, model=model, tools=tools, can_hire=can_hire, max_children=max_children, workspace=workspace,
            inputs=inputs,
        )

    def retire(self, actor: str, name: str, reason: str) -> str:
        """Remove a direct report and its team; returns the retired address. See :meth:`retire_team`."""
        return self.runtime.retirement.retire(actor, name, reason)

    def retire_team(self, actor: str, name: str, reason: str) -> Retired:
        """Retire a direct report (short name or full address; root: any agent by full address) and its team.

        Open tasks the team owes the outside are closed as failed, and the team's unspent budget is returned to the
        retired agent's parent as a non-waking runtime note carrying the budget (nothing when the parent is root, who has no
        limit), so budget stays derived from files and is neither destroyed nor minted.
        """
        return self.runtime.retirement.retire_team(actor, name, reason)
