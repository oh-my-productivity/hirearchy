"""RED skeleton (step A-skill): where the packaged SKILL.md is found."""

from __future__ import annotations

from pathlib import Path

from .api import SkillSource

NOT_FOUND = "the orgmcp skill file was not found in this installation (expected skills/orgmcp/SKILL.md)"


class PackagedSkillSource(SkillSource):
    def __init__(self, package_dir: Path) -> None:
        raise NotImplementedError

    def path(self) -> Path:
        raise NotImplementedError

    def read(self) -> str:
        raise NotImplementedError
