"""RED skeleton (step A-skill): installing the packaged skill into a skills directory."""

from __future__ import annotations

from pathlib import Path

from .api import SkillInstaller, SkillSource, SkillStore


class CopySkillInstaller(SkillInstaller):
    def __init__(self, source: SkillSource, store: SkillStore) -> None:
        raise NotImplementedError

    def install_skill(self, dest: str | Path | None = None, force: bool = False) -> str:
        raise NotImplementedError
