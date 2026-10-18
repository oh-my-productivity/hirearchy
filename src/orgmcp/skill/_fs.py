"""RED skeleton (step A-skill): the skills directory on disk."""

from __future__ import annotations

from pathlib import Path

from ..kernel import Provider
from .api import SkillStore


class FsSkillStore(SkillStore):
    def __init__(self, home: Provider[Path]) -> None:
        raise NotImplementedError

    def target(self, dest: Path | None) -> Path:
        raise NotImplementedError

    def read_existing(self, dest: Path | None) -> str | None:
        raise NotImplementedError

    def write(self, dest: Path | None, text: str) -> str:
        raise NotImplementedError
