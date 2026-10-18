"""``EnvOrgLocator`` over the real process environment, as ``Org.find_root`` uses it."""

from __future__ import annotations

from pathlib import Path

import pytest

from orgmcp.kernel.testing import DictEnvironment, os_environment
from orgmcp.locator import OrgLocator
from orgmcp.locator._env import EnvOrgLocator
from orgmcp.locator.tests._red import red


def test_it_is_an_org_locator() -> None:
    assert isinstance(EnvOrgLocator(DictEnvironment()), OrgLocator)


def test_building_it_asks_the_environment_nothing() -> None:
    class Forbidden(DictEnvironment):
        def get(self, name: str) -> str | None:
            raise AssertionError("no lookup while building")

        def cwd(self) -> Path:
            raise AssertionError("no lookup while building")

    EnvOrgLocator(Forbidden())


@red
def test_the_process_environment_and_working_directory_are_used(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / "ORG.md").write_text("x", encoding="utf-8")
    work = tmp_path / "ceo" / "work"
    work.mkdir(parents=True)
    monkeypatch.delenv("ORG_ROOT", raising=False)
    monkeypatch.chdir(work)
    locator = EnvOrgLocator(os_environment(tmp_path).env)
    assert locator.find_root() == tmp_path.resolve()
    monkeypatch.setenv("ORG_ROOT", str(tmp_path / "elsewhere"))
    assert locator.find_root() == (tmp_path / "elsewhere").resolve()


@red
def test_a_tilde_in_ORG_ROOT_is_the_home_directory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    environment = DictEnvironment({"ORG_ROOT": "~/orgs/main"})
    assert EnvOrgLocator(environment).find_root() == (tmp_path / "orgs" / "main").resolve()


@red
def test_the_working_directory_comes_from_the_environment_object(tmp_path: Path) -> None:
    (tmp_path / "ORG.md").write_text("x", encoding="utf-8")
    below = tmp_path / "a"
    below.mkdir()
    assert EnvOrgLocator(DictEnvironment(cwd=below)).find_root() == tmp_path.resolve()
