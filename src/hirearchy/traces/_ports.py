"""What ``traces`` needs to know about the agents, as a role of its own (the agents package is not one of its dependencies)."""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class AgentPresence(Protocol):
    def exists(self, addr: str) -> bool:
        """``addr`` is an agent of the organization (``agents.AgentDirectory`` answers this structurally)."""
        ...
