"""The totals of every branch of the organization: a pure function of the agents' health."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from ..kernel import ROOT
from .api import FLAGS, AgentHealth, BranchHealth


def branch_totals(top: str, addrs: Sequence[str], by_addr: Mapping[str, AgentHealth]) -> dict[str, BranchHealth]:
    """The branch of ``top`` and of each agent in ``addrs`` (parents before children), over it and everything below it.

    ``top`` = ``root`` is the whole organization: its branch holds every agent."""
    branches = {}
    for b in dict.fromkeys([top, *addrs]):
        members = [by_addr[a] for a in addrs if a == b or b == ROOT or a.startswith(b + "/")]
        branches[b] = BranchHealth(
            addr=b, agents=len(members), runs_used=sum(h.runs_used for h in members),
            open_tasks=sum(h.open_tasks for h in members), done=sum(h.done for h in members),
            failed=sum(h.failed for h in members), blocked=sum(h.blocked for h in members),
            rework=sum(h.rework for h in members),
            worst_flag=min((f for h in members for f in h.flags), key=FLAGS.index, default=None),
        )
    return branches
