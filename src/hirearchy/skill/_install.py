"""Installing the packaged skill into a skills directory."""

from __future__ import annotations

from pathlib import Path

from ..kernel import OrgError
from .api import SkillCheck, SkillInstaller, SkillSource, SkillStore


class CopySkillInstaller(SkillInstaller, SkillCheck):
    """Copy the skill of a ``SkillSource`` into a ``SkillStore``: identical is left alone, different needs ``force``.

    It also says when the installed copy is out of date (``stale``), reading both and writing nothing."""

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

    def stale(self, dest: Path | None = None) -> Path | None:
        try:
            existing = self._store.read_existing(dest)
            if existing is None or existing == self._source.read():
                return None
            return self._store.target(dest)
        except (OrgError, OSError, UnicodeDecodeError):
            return None
