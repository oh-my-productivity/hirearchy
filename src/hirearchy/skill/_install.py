"""Installing the packaged skill into a skills directory."""

from __future__ import annotations

from pathlib import Path

from ..kernel import OrgError
from .api import SkillInstaller, SkillSource, SkillStore


class CopySkillInstaller(SkillInstaller):
    """Copy the skill of a ``SkillSource`` into a ``SkillStore``: identical is left alone, different needs ``force``."""

    def __init__(self, source: SkillSource, store: SkillStore) -> None:
        self._source = source
        self._store = store

    def install_skill(self, dest: str | Path | None = None, force: bool = False) -> str:
        base = Path(dest) if dest else None
        text = self._source.read()
        target = self._store.target(base)
        existing = self._store.read_existing(base)
        if existing is not None:
            if existing == text:
                return f"{target}\nalready installed and up to date"
            if not force:
                raise OrgError(f"{target} exists and differs from this version of the skill; nothing was changed. "
                               "Use --force to replace it")
        self._store.write(base, text)
        return f"{target}\ninstalled the hirearchy skill"
