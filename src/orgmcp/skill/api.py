"""The public surface of ``skill``: the assistant skill that ships with orgmcp and its installation into a kiro skills directory.

Three roles, one small interface each: where the packaged text comes from (``SkillSource``), where a skills directory keeps its
copy (``SkillStore``), and the decision between them (``SkillInstaller``: install, leave alone, or refuse to overwrite).
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable

__all__ = ["SkillInstaller", "SkillSource", "SkillStore"]


@runtime_checkable
class SkillSource(Protocol):
    def read(self) -> str:
        """The packaged SKILL.md (the wheel's ``_skill/`` first, the checkout's ``skills/orgmcp/`` second); ``OrgError`` if missing."""
        ...


@runtime_checkable
class SkillStore(Protocol):
    def target(self, dest: Path | None) -> Path:
        """Where the skill goes: ``<dest>/orgmcp/SKILL.md`` (``~`` expanded, resolved; ``dest=None``: the default skills directory)."""
        ...

    def read_existing(self, dest: Path | None) -> str | None:
        """The text installed at the target; ``None`` when nothing is there; ``OrgError`` when the target exists and is not a file."""
        ...

    def write(self, dest: Path | None, text: str) -> str:
        """Create the directories and write ``text`` at the target. Returns the target path."""
        ...


@runtime_checkable
class SkillInstaller(Protocol):
    def install_skill(self, dest: str | Path | None = None, force: bool = False) -> str:
        """Copy the skill to ``<dest>/orgmcp/SKILL.md`` (default dest: ``~/.kiro/skills``). Returns what to print.

        An identical file is left alone; a different existing file is only replaced with ``force`` (``OrgError`` otherwise)."""
        ...
