"""The wiring of ``skill``: the runtime carries the real source, store and installer, built from the process environment."""

from __future__ import annotations

import importlib.util
from pathlib import Path

from orgmcp.app import wire_skill, wiring
from orgmcp.kernel import Environment
from orgmcp.kernel.testing import DictEnvironment
from orgmcp.skill import SkillInstaller, SkillSource, SkillStore
from orgmcp.skill._fs import FsSkillStore
from orgmcp.skill._install import CopySkillInstaller
from orgmcp.skill._source import PackagedSkillSource
from orgmcp.skill.testing import MemorySkillSource, MemorySkillStore

_spec = importlib.util.find_spec("orgmcp")
assert _spec is not None and _spec.origin is not None
PACKAGE = Path(_spec.origin).resolve().parent
SHIPPED = PACKAGE.parents[1] / "skills" / "orgmcp" / "SKILL.md"


def test_the_runtime_has_the_real_skill_parts(tmp_path: Path) -> None:
    runtime = wiring.open_runtime(tmp_path)
    assert isinstance(runtime.skill_source, PackagedSkillSource)
    assert isinstance(runtime.skill_store, FsSkillStore)
    assert isinstance(runtime.skill_installer, CopySkillInstaller)


def test_the_source_is_the_shipped_skill(tmp_path: Path) -> None:
    runtime = wiring.open_runtime(tmp_path)
    assert runtime.skill_source.read() == SHIPPED.read_text(encoding="utf-8")


def test_the_installer_installs_with_the_parts_of_the_runtime(tmp_path: Path) -> None:
    runtime = wiring.open_runtime(tmp_path / "org")
    message = runtime.skill_installer.install_skill(tmp_path / "skills")
    assert message == f"{(tmp_path / 'skills').resolve() / 'orgmcp' / 'SKILL.md'}\ninstalled the orgmcp skill"


def test_the_store_asks_the_environment_for_the_home(tmp_path: Path) -> None:
    home = tmp_path / "home"
    runtime = wiring.open_runtime(tmp_path / "org", {Environment: DictEnvironment(home=home)})
    assert runtime.skill_store.target(None) == home / ".kiro" / "skills" / "orgmcp" / "SKILL.md"


def test_an_override_replaces_a_port_and_the_installer_uses_it(tmp_path: Path) -> None:
    source, store = MemorySkillSource("faked\n"), MemorySkillStore()
    runtime = wiring.open_runtime(tmp_path, {SkillSource: source, SkillStore: store})
    assert runtime.skill_source is source and runtime.skill_store is store and isinstance(runtime.skill_installer, SkillInstaller)
    runtime.skill_installer.install_skill(Path("/skills"))
    assert store.read_file(Path("/skills/orgmcp/SKILL.md")) == "faked\n"


def test_the_package_directory_comes_from_the_package_not_from_the_wiring_module() -> None:
    assert wire_skill.package_dir() == PACKAGE
