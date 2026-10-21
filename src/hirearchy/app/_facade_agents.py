"""The registry of agents: existence, tree, charters, memory (agents).

The bodies call the ports of ``self.runtime`` (step A-agents; ARCHITECTURE.md 5.3 and 6.4)."""

from __future__ import annotations

from .runtime import OrgRuntime


class AgentsMixin:
    """The registry of agents: existence, tree, charters, memory (agents)."""

    runtime: OrgRuntime

    def exists(self, addr: str) -> bool:
        return self.runtime.agents.exists(addr)

    def require(self, addr: str) -> str:
        return self.runtime.agents.require(addr)

    def children(self, addr: str) -> list[str]:
        return self.runtime.agents.children(addr)

    def agents(self) -> list[str]:
        """Every agent except root, parents before children."""
        return self.runtime.agents.agents()

    def subtree(self, addr: str) -> list[str]:
        return self.runtime.agents.subtree(addr)

    def charter(self, addr: str) -> tuple[dict[str, object], str]:
        return self.runtime.charters.charter(addr)

    def memory(self, addr: str) -> str:
        return self.runtime.charters.memory(addr)
