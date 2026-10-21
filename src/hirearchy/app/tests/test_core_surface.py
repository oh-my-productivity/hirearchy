"""What does not change for anyone who uses ``hirearchy.core``: characterization that passes before and after the pre-split."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from hirearchy import core
from hirearchy.app import wiring
from hirearchy.app.tests import _signatures
from hirearchy.app.tests._mixins import MIXINS
from hirearchy.kernel import AtomicWriter, Clock
from hirearchy.kernel.testing import RecordingAtomicWriter
from testkit.clocks import ClockReading

FIXED = datetime(2031, 5, 6, 7, 8, 9, tzinfo=timezone.utc)


def test_org_ids_and_files_follow_the_ports_of_the_runtime(tmp_path: Path) -> None:
    org = getattr(core, "Org").init(tmp_path / "org", "mission")
    org.runtime = wiring.open_runtime(org.root, {Clock: ClockReading(lambda: FIXED)})
    assert org.new_id("ceo").startswith("20310506T070809000000-ceo-")
    written: list[Path] = []
    org.runtime = wiring.open_runtime(org.root, {AtomicWriter: RecordingAtomicWriter(lambda path, text: written.append(path))})
    org.save_ledger("probe", {})
    assert written == [org.root / ".runtime" / "probe.json"]


def test_every_def_of_the_old_org_is_in_exactly_one_mixin() -> None:
    recorded = set(json.loads(_signatures.SIGNATURES.read_text(encoding="utf-8"))["Org"])
    held = [m for _, _, methods in MIXINS for m in methods.split()]
    assert len(held) == len(set(held)) == len(recorded) == 98 and set(held) == recorded


def test_the_module_level_names_that_core_exported_are_still_there() -> None:
    for name in ("DEFAULT_CONFIG", "DEFAULT_MODEL", "LESSONS_MAX_CHARS", "Retired", "config_default_model", "charter_change_note",
                 "utcnow", "atomic_write", "_message_cap", "_short", "_fold", "_case_twin", "_FOLDED_RUNTIME_NAMES", "_EXACT_FILES",
                 "_PARSED", "_PARSED_MAX", "Message", "OrgError", "ROOT", "split_frontmatter", "join_frontmatter", "_visible", "_inside"):
        assert hasattr(core, name), name
    assert getattr(core, "Retired")._fields == ("addr", "refunded", "refunded_to")
