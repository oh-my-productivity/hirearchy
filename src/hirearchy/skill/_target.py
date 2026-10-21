"""Where the skill lives: the names every part of the package agrees on."""

from __future__ import annotations

from pathlib import Path

SKILL_NAME = "hirearchy"
SKILL_FILE = "SKILL.md"
DEFAULT_SKILLS_DIR = (".kiro", "skills")  # below the home directory


def default_base(home: Path) -> Path:
    """The skills directory that kiro reads for a user: ``<home>/.kiro/skills``."""
    return home.joinpath(*DEFAULT_SKILLS_DIR)


def target_in(base: Path) -> Path:
    """The file of the skill inside a (resolved) skills directory."""
    return base / SKILL_NAME / SKILL_FILE
