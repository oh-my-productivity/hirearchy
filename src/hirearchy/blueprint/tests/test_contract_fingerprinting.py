"""Contract of ``Fingerprinting``: the parts of the organization an extension depends on, as text that is equal while none of them changes."""

from __future__ import annotations

from pathlib import Path

import pytest
from hirearchy.blueprint._fingerprint import OrgFingerprint
from hirearchy.blueprint._protocols import Fingerprinting
from hirearchy.blueprint.testing import IMPLEMENTATIONS, FingerprintHarness, ScriptedFingerprint

from ._extension_world import extension, reads_of, world
from ._support import implementations, make

BP = extension(limits=[{"agent": "lead", "max_children": 3}])


def over_files(tmp_path: Path) -> FingerprintHarness:
    w = world(tmp_path)
    def change() -> None:
        w.org.hire("lead", "extra", "Extra", "x", tools=["read"])

    return FingerprintHarness(OrgFingerprint(reads_of(w.org)), change)


def scripted(tmp_path: Path) -> FingerprintHarness:
    fake = ScriptedFingerprint("one")

    def change() -> None:
        fake.value = "two"

    return FingerprintHarness(fake, change)


@pytest.fixture(params=implementations([over_files, scripted]))
def h(request: pytest.FixtureRequest, tmp_path: Path) -> FingerprintHarness:
    made = make(request, tmp_path, FingerprintHarness)
    assert isinstance(made.fingerprinting, Fingerprinting)
    return made


def test_the_same_organization_gives_the_same_text(h: FingerprintHarness) -> None:
    assert h.fingerprinting.fingerprint(BP) == h.fingerprinting.fingerprint(BP)


def test_a_change_of_what_the_extension_names_changes_the_text(h: FingerprintHarness) -> None:
    before = h.fingerprinting.fingerprint(BP)
    h.change()
    assert h.fingerprinting.fingerprint(BP) != before


def test_the_text_is_a_string(h: FingerprintHarness) -> None:
    assert isinstance(h.fingerprinting.fingerprint(BP), str) and h.fingerprinting.fingerprint(BP) != ""
