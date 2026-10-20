"""Where the packaged SKILL.md is found: inside the installed package (wheel) or in the source checkout."""

from __future__ import annotations

from pathlib import Path

from ..kernel import OrgError
from ._target import SKILL_FILE, SKILL_NAME
from .api import SkillSource

NOT_FOUND = "the orgmcp skill file was not found in this installation (expected skills/orgmcp/SKILL.md)"
WHEEL_DIR = "_skill"  # pyproject.toml force-includes skills/orgmcp/SKILL.md as orgmcp/_skill/SKILL.md


class PackagedSkillSource(SkillSource):
    """The SKILL.md that ships with this install, searched from the directory of the ``orgmcp`` package.

    The directory is given (the composition root takes it from ``orgmcp.__file__``), never computed from the file that holds this
    class, so moving the class does not change what is found (ARCHITECTURE.md 10.1, risk 8)."""

    def __init__(self, package_dir: Path) -> None:
        self._package_dir = package_dir

    def path(self) -> Path:
        """The file: the wheel's copy next to the package, else the checkout's ``<repo>/skills/orgmcp/SKILL.md``."""
        here = self._package_dir.resolve()
        for candidate in (here / WHEEL_DIR / SKILL_FILE, here.parent.parent / "skills" / SKILL_NAME / SKILL_FILE):
            if candidate.is_file():
                return candidate
        raise OrgError(NOT_FOUND)

    def read(self) -> str:
        return self.path().read_text(encoding="utf-8")
