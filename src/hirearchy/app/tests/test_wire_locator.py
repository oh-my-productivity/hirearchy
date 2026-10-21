"""``wire_locator``: the locator of the runtime, and ``find_org_root`` for the process that has no runtime yet (``Org.find_root`` is static)."""

from __future__ import annotations

from pathlib import Path

import pytest

from hirearchy.app import wiring
from hirearchy.app.wire_locator import find_org_root, os_locator
from hirearchy.locator import OrgLocator
from hirearchy.locator._env import EnvOrgLocator


def test_the_runtime_has_the_environment_locator(tmp_path: Path) -> None:
    assert isinstance(wiring.open_runtime(tmp_path).locator, EnvOrgLocator)
    assert isinstance(os_locator(), OrgLocator)


def test_find_org_root_takes_a_path_a_string_or_nothing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ORG_ROOT", raising=False)
    (tmp_path / "ORG.md").write_text("---\n---\n", encoding="utf-8")
    deep = tmp_path / "a" / "b"
    deep.mkdir(parents=True)
    monkeypatch.chdir(deep)
    root = tmp_path.resolve()
    assert find_org_root(deep) == find_org_root(str(deep)) == find_org_root() == find_org_root("") == find_org_root(None) == root


def test_find_org_root_answers_what_the_locator_of_the_process_answers(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ORG_ROOT", str(tmp_path / "named"))
    assert find_org_root(tmp_path) == os_locator().find_root(tmp_path) == (tmp_path / "named").resolve()
