"""The skills directory on disk: ``<dest>/orgmcp/SKILL.md``."""

from __future__ import annotations

from pathlib import Path

from ..kernel import OrgError, Provider
from ._target import default_base, target_in
from .api import SkillStore

NOT_A_FILE = "{target} exists and is not a file; nothing was changed"


class FsSkillStore(SkillStore):
    def __init__(self, home: Provider[Path]) -> None:
        self._home = home  # asked on every use: HOME may change between two calls

    def _base(self, dest: Path | None) -> Path:
        if dest is None:
            return default_base(self._home()).resolve()
        if dest.parts[:1] == ("~",):
            return self._home().joinpath(*dest.parts[1:]).resolve()
        return dest.expanduser().resolve()

    def target(self, dest: Path | None) -> Path:
        return target_in(self._base(dest))

    def read_existing(self, dest: Path | None) -> str | None:
        target = self.target(dest)
        if target.is_file():
            return target.read_text(encoding="utf-8")
        if target.exists():
            raise OrgError(NOT_A_FILE.format(target=target))
        return None

    def write(self, dest: Path | None, text: str) -> str:
        target = self.target(dest)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
        return str(target)
