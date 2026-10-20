"""The public surface of ``locator``: finding the organization root a process should work on."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable

__all__ = ["OrgLocator"]


@runtime_checkable
class OrgLocator(Protocol):
    def find_root(self, start: str | Path | None = None) -> Path:
        """``$ORG_ROOT``, else the nearest directory with ORG.md at or above ``start`` (a path or a string; default, also for an empty
        one: the working directory), else ``start/org``; ``OrgError`` when there is none."""
        ...
