"""The public surface of ``bootstrap``: bringing a new organization directory into existence.

One port, ``OrgInitializer``. It is the only code that creates the root's skeleton: ``ORG.md`` (written through ``settings``), the four
root mailbox directories, ``.runtime/``, and the ``.gitignore`` and the git repository (through ``snapshots``) -- the creator exception of
ARCHITECTURE.md 2.3: directories, never content.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Protocol, runtime_checkable

__all__ = ["INITIAL_IGNORE_LINES", "OrgInitializer"]

# What a new organization's .gitignore starts with: files that change constantly stay out of the snapshots (``git add -A`` runs after every
# run). ``IgnoreList.ensure_runtime_files`` adds the rest when a scheduler or an event needs it.
INITIAL_IGNORE_LINES: tuple[str, ...] = (".tmp-*", "runs/", ".kiro/", ".runtime/scheduler.pid", ".runtime/events/")


@runtime_checkable
class OrgInitializer(Protocol):
    def init(self, root: Path, mission: str | None = None, config: Mapping[str, object] | None = None) -> None:
        """Make ``root`` an organization: ``ORG.md`` (``config`` over the defaults, the rules with ``mission``), the root boxes, ``.runtime/``,
        ``.gitignore`` with ``INITIAL_IGNORE_LINES``, ``git init`` and the first commit ``init organization`` (no repository, no commit when
        git does not exist). ``OrgError`` ("already an organization: <root>") when ``ORG.md`` exists. ``root`` is the directory that the
        initializer's own ports (``ORG.md``, ``.gitignore``, the repository) are bound to."""
        ...
