"""The legacy-exports ledger (ARCHITECTURE.md 6.5): which legacy names a module still exports, and who removes them."""

from __future__ import annotations

import pytest

from . import legacy_exports
from .paths import SRC

pytestmark = pytest.mark.architecture

# Every legacy name leaves in E3 (ARCHITECTURE.md 6.4) except the permanent compatibility surface.
STEPS = {"E3", "permanent"}


def test_every_public_name_of_a_legacy_module_is_in_the_ledger():
    problems = legacy_exports.check(SRC)
    assert not problems, "\n".join(problems)


def test_a_new_public_name_and_a_stale_entry_are_reported(tmp_path, monkeypatch):
    # a table of its own, so that the test does not depend on which legacy modules the ledger still lists
    monkeypatch.setitem(legacy_exports.LEGACY_EXPORTS, "upgrade", legacy_exports._e3("MISSION_HEADING RULES_HEADING extract_mission upgrade_rules"))
    (tmp_path / "upgrade.py").write_text("def upgrade_rules(): ...\ndef sneaked_in(): ...\nclass Upgrade: ...\n", encoding="utf-8")
    problems = legacy_exports.check(tmp_path)
    assert any("sneaked_in" in p and "upgrade" in p for p in problems)
    assert any("extract_mission" in p and "no longer" in p for p in problems)  # in the ledger, gone from the module
    assert not any("upgrade_rules" in p for p in problems)


def test_the_permanent_entries_are_core_and_progress():
    assert legacy_exports.PERMANENT_MODULES == {"core"}
    assert legacy_exports.LEGACY_EXPORTS["progress"]["progress"] == "permanent"
    assert legacy_exports.LEGACY_EXPORTS["core"] == {"*": "permanent"}


def test_every_entry_names_the_step_that_removes_it():
    assert len(legacy_exports.LEGACY_EXPORTS) >= 12  # core, scheduler, server, cli, ... (one table per legacy module that is left)
    for module, names in legacy_exports.LEGACY_EXPORTS.items():
        for name, step in names.items():
            assert step in STEPS, f"{module}.{name}: unknown removal step {step!r}"


def test_a_converted_module_exports_its_ledger_names_as_a_package():
    for package, names in legacy_exports.exported_names_by_package(SRC).items():
        assert (SRC / package).is_dir() and names <= set(legacy_exports.LEGACY_EXPORTS[package]), package
