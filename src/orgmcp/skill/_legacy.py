"""The old module-level functions of ``orgmcp.skill``, as thin adapters over the Protocol implementations.

Exported by ``__init__`` until step E3 (``LEGACY_EXPORTS``). They build the real parts themselves: no runtime is at hand for the
callers that still import them (the ``install-skill`` command)."""

from __future__ import annotations

from pathlib import Path

from ._fs import FsSkillStore
from ._install import CopySkillInstaller
from ._source import PackagedSkillSource
from ._target import SKILL_NAME

__all__ = ["SKILL_NAME", "install_skill", "skill_source"]


def skill_source() -> Path:
    """The SKILL.md that ships with this install: inside the package (wheel) or in the source checkout."""
    # parents[1]: the directory of the ``orgmcp`` package (this file is orgmcp/skill/_legacy.py)
    return PackagedSkillSource(Path(__file__).resolve().parents[1]).path()


def install_skill(dest: str | Path | None = None, force: bool = False) -> str:
    """Copy the skill to ``<dest>/orgmcp/SKILL.md`` (default dest: ``~/.kiro/skills``). Returns what to print.

    An identical file is left alone; a different existing file is only replaced with ``force``.
    """
    return CopySkillInstaller(PackagedSkillSource(Path(__file__).resolve().parents[1]), FsSkillStore(Path.home)).install_skill(dest, force)
