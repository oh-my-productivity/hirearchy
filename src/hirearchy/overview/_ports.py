"""The ports ``overview`` defines for what it consumes (consumer-owned, narrower than the provider's)."""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class ServiceNames(Protocol):
    def service_names(self, addr: str) -> list[str]:
        """The (non-retired) services ``addr`` offers, by name; root offers none."""
        ...
