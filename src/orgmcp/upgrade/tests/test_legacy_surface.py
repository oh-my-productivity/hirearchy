"""The names ``orgmcp.upgrade`` kept exporting when the module became a package (``LEGACY_EXPORTS``, until step E3).

Characterization: these tests passed on the module ``upgrade.py`` and must keep passing on the package."""

from __future__ import annotations

import importlib
import subprocess
from pathlib import Path
from typing import Any

import pytest

from orgmcp.kernel import OrgError
from orgmcp.templates.testing import static_document_templates
from orgmcp.upgrade import Upgrade

from ._legacy import legacy
from ._cases import COMMIT, MISSION, expected

upgrade = importlib.import_module("orgmcp.upgrade")  # as a module object: the tests read its attributes by name


def old_org(tmp_path: Path) -> Any:
    org = legacy("core").Org.init(tmp_path / "org", MISSION, {"poll_seconds": 0.05, "default_model": "m1"})
    (org.root / "ORG.md").write_bytes(expected("old_org_md.md").encode("utf-8"))
    return org


def test_the_old_names_are_still_exported() -> None:
    assert upgrade.MISSION_HEADING == "## Mission\n"
    assert upgrade.RULES_HEADING == "\n## How this organization works"
    assert callable(upgrade.extract_mission) and callable(upgrade.upgrade_rules)
    assert upgrade.Upgrade is Upgrade
    assert {"Upgrade", "RulesUpgrader"} <= set(upgrade.__all__)


def test_upgrade_rules_of_an_org_reports_and_writes(tmp_path: Path) -> None:
    org = old_org(tmp_path)
    dry = upgrade.upgrade_rules(org, dry_run=True)
    assert dry.text() == expected("dry_run_text.txt") and (org.root / "ORG.md").read_bytes().decode() == expected("old_org_md.md")
    done = upgrade.upgrade_rules(org)
    assert done.text() == expected("written_text.txt") and (org.root / "ORG.md").read_bytes().decode() == expected("new_org_md.md")
    assert upgrade.upgrade_rules(org).text() == expected("up_to_date_text.txt")
    log = subprocess.run(["git", "log", "--format=%s"], cwd=org.root, capture_output=True, text=True).stdout.splitlines()
    assert log == [COMMIT, "init organization"]


def test_upgrade_rules_refuses_an_org_md_without_a_mission(tmp_path: Path) -> None:
    org = legacy("core").Org.init(tmp_path / "org", "m")
    path = org.root / "ORG.md"
    front = path.read_text().split("\n---\n", 1)[0]
    path.write_text(front + "\n---\nMy own rules.\n")
    with pytest.raises(OrgError, match="Mission"):
        upgrade.upgrade_rules(org)
    assert path.read_text().endswith("My own rules.\n")


def test_extract_mission_keeps_headings_inside_the_mission() -> None:
    assert upgrade.extract_mission(static_document_templates().org_rules(MISSION)) == MISSION
