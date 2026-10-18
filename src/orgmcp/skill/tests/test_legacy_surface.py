"""The names ``orgmcp.skill`` kept exporting when the module became a package (``LEGACY_EXPORTS``, until step E3).

Characterization: these tests passed on the module ``skill.py`` and must keep passing on the package."""

from __future__ import annotations

import importlib
from pathlib import Path

import pytest

from orgmcp.kernel import OrgError

skill = importlib.import_module("orgmcp.skill")  # as a module object: the tests read its attributes by name
REPO = Path(__file__).resolve().parents[4]
SHIPPED = REPO / "skills" / "orgmcp" / "SKILL.md"


def test_the_old_names_are_still_exported() -> None:
    assert skill.SKILL_NAME == "orgmcp"
    assert callable(skill.skill_source) and callable(skill.install_skill)
    assert {"SkillSource", "SkillStore", "SkillInstaller"} <= set(skill.__all__)


def test_skill_source_is_the_shipped_file_as_a_path() -> None:
    path = skill.skill_source()
    assert isinstance(path, Path) and path == SHIPPED.resolve()
    assert path.read_text(encoding="utf-8") == SHIPPED.read_text(encoding="utf-8")


def test_install_skill_installs_and_reports(tmp_path: Path) -> None:
    target = (tmp_path / "skills").resolve() / "orgmcp" / "SKILL.md"
    assert skill.install_skill(tmp_path / "skills") == f"{target}\ninstalled the orgmcp skill"
    assert target.read_text(encoding="utf-8") == SHIPPED.read_text(encoding="utf-8")
    assert skill.install_skill(str(tmp_path / "skills")) == f"{target}\nalready installed and up to date"


def test_install_skill_refuses_a_different_file_without_force(tmp_path: Path) -> None:
    target = tmp_path / "skills" / "orgmcp" / "SKILL.md"
    target.parent.mkdir(parents=True)
    target.write_text("mine\n", encoding="utf-8")
    with pytest.raises(OrgError, match="exists and differs from this version of the skill; nothing was changed. Use --force to replace it"):
        skill.install_skill(tmp_path / "skills")
    assert target.read_text(encoding="utf-8") == "mine\n"
    assert skill.install_skill(tmp_path / "skills", force=True).endswith("installed the orgmcp skill")
    assert target.read_text(encoding="utf-8") == SHIPPED.read_text(encoding="utf-8")


def test_install_skill_refuses_a_target_that_is_not_a_file(tmp_path: Path) -> None:
    (tmp_path / "skills" / "orgmcp" / "SKILL.md").mkdir(parents=True)
    with pytest.raises(OrgError, match="exists and is not a file; nothing was changed"):
        skill.install_skill(tmp_path / "skills", force=True)


def test_install_skill_without_a_destination_uses_the_home_of_the_moment(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path / "first"))
    skill.install_skill()
    monkeypatch.setenv("HOME", str(tmp_path / "second"))
    skill.install_skill()
    for name in ("first", "second"):
        assert (tmp_path / name / ".kiro" / "skills" / "orgmcp" / "SKILL.md").is_file()
