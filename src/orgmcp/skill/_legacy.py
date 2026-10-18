"""The assistant skill (``skills/orgmcp/SKILL.md``) and its installation into a kiro skills directory."""

from __future__ import annotations

from pathlib import Path

from ..kernel import OrgError

SKILL_NAME = "orgmcp"


def skill_source() -> Path:
    """The SKILL.md that ships with this install: inside the package (wheel) or in the source checkout."""
    here = Path(__file__).resolve().parent.parent  # the package directory (orgmcp/): this file is one level deeper than skill.py was
    for candidate in (here / "_skill" / "SKILL.md", here.parent.parent / "skills" / SKILL_NAME / "SKILL.md"):
        if candidate.is_file():
            return candidate
    raise OrgError("the orgmcp skill file was not found in this installation (expected skills/orgmcp/SKILL.md)")


def install_skill(dest: str | Path | None = None, force: bool = False) -> str:
    """Copy the skill to ``<dest>/orgmcp/SKILL.md`` (default dest: ``~/.kiro/skills``). Returns what to print.

    An identical file is left alone; a different existing file is only replaced with ``force``.
    """
    base = Path(dest).expanduser() if dest else Path.home() / ".kiro" / "skills"
    target = base.resolve() / SKILL_NAME / "SKILL.md"
    text = skill_source().read_text(encoding="utf-8")
    if target.is_file():
        if target.read_text(encoding="utf-8") == text:
            return f"{target}\nalready installed and up to date"
        if not force:
            raise OrgError(f"{target} exists and differs from this version of the skill; nothing was changed. "
                           "Use --force to replace it")
    elif target.exists():
        raise OrgError(f"{target} exists and is not a file; nothing was changed")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")
    return f"{target}\ninstalled the orgmcp skill"
