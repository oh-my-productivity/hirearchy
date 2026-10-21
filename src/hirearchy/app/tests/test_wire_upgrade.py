"""The wiring of ``upgrade``: the runtime carries the real upgrader, and the whole contract suite of ``RulesUpgrader`` passes over the real
ports (the file ORG.md, the ``git`` program) built by the composition root."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from hirearchy.app import wiring
from hirearchy.upgrade import RulesUpgrader
from hirearchy.upgrade._upgrader import TemplateRulesUpgrader
from hirearchy.upgrade.testing import UpgradeHarness
from hirearchy.upgrade.tests.test_contract_rules_upgrader import (  # the contract suite, run here over the real ports
    old,
    test_a_changed_org_md_is_committed_once,
    test_a_current_org_md_is_left_alone,
    test_a_dry_run_reports_and_writes_nothing,
    test_an_org_md_without_frontmatter_stays_without,
    test_the_report_is_a_view,
    test_the_upgrade_rewrites_the_body_and_keeps_the_frontmatter_and_the_mission,
    test_without_a_mission_section_it_refuses_and_changes_nothing,
)

__all__ = [
    "old", "test_a_changed_org_md_is_committed_once", "test_a_current_org_md_is_left_alone", "test_a_dry_run_reports_and_writes_nothing",
    "test_an_org_md_without_frontmatter_stays_without", "test_the_report_is_a_view",
    "test_the_upgrade_rewrites_the_body_and_keeps_the_frontmatter_and_the_mission",
    "test_without_a_mission_section_it_refuses_and_changes_nothing",
]


@pytest.fixture(autouse=True)
def isolated_git(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(tmp_path))
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", "/dev/null")
    monkeypatch.setenv("GIT_TERMINAL_PROMPT", "0")


@pytest.fixture
def h(tmp_path: Path) -> UpgradeHarness:
    root = tmp_path / "org"
    root.mkdir()
    runtime = wiring.open_runtime(root)
    runtime.snapshotter.init_repository()
    path = root / "ORG.md"

    def put(text: str) -> None:
        path.write_text(text, encoding="utf-8")

    def stored() -> str | None:
        return path.read_bytes().decode("utf-8") if path.is_file() else None

    def commits() -> list[str]:
        out = subprocess.run(["git", "log", "--reverse", "--format=%s"], cwd=root, capture_output=True, text=True, check=False)
        return out.stdout.splitlines()

    return UpgradeHarness(runtime.rules_upgrader, put, stored, commits)


def test_the_runtime_has_the_real_upgrader(tmp_path: Path) -> None:
    runtime = wiring.open_runtime(tmp_path)
    assert isinstance(runtime.rules_upgrader, TemplateRulesUpgrader) and isinstance(runtime.rules_upgrader, RulesUpgrader)
