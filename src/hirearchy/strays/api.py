"""The public surface of ``strays``: org files that an agent's built-in ``write`` left in its workspace.

kiro's built-in ``write`` starts in the agent's workspace, so ``write("lead/MEMORY.md")`` lands in ``<workspace>/lead/`` and not in the
organization: the memory is lost. ``StrayProbe`` finds such files (before and after a run), ``StrayRegistry`` remembers them until the
agent has been told, once, in its next prompt. Nothing is ever moved or deleted.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Protocol, runtime_checkable

__all__ = [
    "StrayProbe",
    "StrayRegistry",
]


@runtime_checkable
class StrayProbe(Protocol):
    def probe(self, addr: str) -> dict[str, float]:
        """The mtimes of ``<workspace>/<address>`` (a directory) and of ``<workspace>/<address>/MEMORY.md``, whichever exist, keyed by
        path: the places where a built-in ``write`` of ``<address>/...`` lands. ``{}`` for an agent without the built-in ``write`` in
        its charter or without a workspace (then nothing can land there)."""
        ...

    def found_since(self, before: Mapping[str, float], after: Mapping[str, float]) -> list[str]:
        """The paths of ``after`` that were not in ``before``, and a ``MEMORY.md`` that was written meanwhile (newer mtime); a
        ``MEMORY.md`` is left out when its own directory is among them (the tree says it all)."""
        ...


@runtime_checkable
class StrayRegistry(Protocol):
    def record(self, addr: str, paths: Sequence[str]) -> None:
        """Remember the first 10 ``paths`` for ``addr`` (``.runtime/strays.json``) so that its next prompt tells it; ignored once the
        agent has been told (later strays are only logged by the caller)."""
        ...

    def take_notice(self, addr: str) -> str:
        """The one-time notice for the run prompt of ``addr``, naming (at most 5 of) the recorded paths and the agent's own write tool;
        marks it told. ``""`` when nothing is recorded for ``addr`` or it has been told already."""
        ...
