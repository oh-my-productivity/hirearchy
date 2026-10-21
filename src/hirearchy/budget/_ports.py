"""The ports ``budget`` defines for what it consumes (consumer-owned, narrower than the provider's)."""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class RunCounter(Protocol):
    def count(self, addr: str) -> int:
        """The runs ``addr`` has used: its visible run logs (``RunLogReader.count`` is one, and so is the dashboard's per-refresh cache)."""
        ...
