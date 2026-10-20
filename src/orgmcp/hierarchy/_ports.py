"""The ports ``hierarchy`` defines for what it consumes (consumer-owned, narrower than the provider's)."""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class AgentSlots(Protocol):
    def occupied(self, addr: str) -> bool:
        """Something is at the place of the agent ``addr`` (a directory, a stray file): hiring there would collide. Wider than
        ``AgentDirectory.exists``, which is true only for a directory with an ``AGENT.md``."""
        ...
