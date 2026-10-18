"""``FsSkillStore``: what only a real file system can show (symlinks, the working directory, the home asked when needed)."""

from __future__ import annotations

from pathlib import Path

import pytest

from orgmcp.skill._fs import FsSkillStore

pytestmark = pytest.mark.xfail(strict=True, reason="red: A-skill")


def test_a_symlinked_destination_is_resolved(tmp_path: Path) -> None:
    real = tmp_path / "real"
    real.mkdir()
    link = tmp_path / "link"
    link.symlink_to(real, target_is_directory=True)
    store = FsSkillStore(lambda: tmp_path)
    assert store.target(link) == real.resolve() / "orgmcp" / "SKILL.md"
    store.write(link, "x")
    assert (real / "orgmcp" / "SKILL.md").read_text(encoding="utf-8") == "x"


def test_a_relative_destination_is_taken_from_the_working_directory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    store = FsSkillStore(lambda: tmp_path / "home")
    assert store.target(Path("rel")) == tmp_path.resolve() / "rel" / "orgmcp" / "SKILL.md"


def test_the_home_is_asked_for_on_every_use(tmp_path: Path) -> None:
    homes = [tmp_path / "one", tmp_path / "two"]
    store = FsSkillStore(lambda: homes[0])
    assert store.target(None) == homes[0].resolve() / ".kiro" / "skills" / "orgmcp" / "SKILL.md"
    homes[0] = homes[1]
    assert store.target(None) == homes[1].resolve() / ".kiro" / "skills" / "orgmcp" / "SKILL.md"


def test_the_home_is_not_asked_for_when_a_destination_is_given(tmp_path: Path) -> None:
    def no_home() -> Path:
        raise AssertionError("the home directory was asked for")

    FsSkillStore(no_home).target(tmp_path)


def test_a_home_prefix_uses_the_given_home_not_the_environment(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path / "environment"))
    home = tmp_path / "given"
    assert FsSkillStore(lambda: home).target(Path("~/skills")) == home.resolve() / "skills" / "orgmcp" / "SKILL.md"


def test_the_text_is_written_as_utf8(tmp_path: Path) -> None:
    FsSkillStore(lambda: tmp_path).write(tmp_path, "naïve ✓\n")
    assert (tmp_path / "orgmcp" / "SKILL.md").read_bytes() == "naïve ✓\n".encode("utf-8")
