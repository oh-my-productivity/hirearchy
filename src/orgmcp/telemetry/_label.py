"""The name of this process."""

from __future__ import annotations

from .api import ProcessLabel


class MutableProcessLabel(ProcessLabel):
    def get(self) -> str:
        raise NotImplementedError("red: A-telemetry")

    def set(self, name: str) -> None:
        raise NotImplementedError("red: A-telemetry")
