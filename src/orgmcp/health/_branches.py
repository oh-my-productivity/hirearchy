"""The totals of every branch of the organization: a pure function of the agents' health."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from .api import AgentHealth, BranchHealth


def branch_totals(top: str, addrs: Sequence[str], by_addr: Mapping[str, AgentHealth]) -> dict[str, BranchHealth]:
    raise NotImplementedError("red: C-health")
