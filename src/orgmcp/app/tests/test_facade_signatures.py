"""The ``Org`` facade and ``Message`` keep every name, kind, parameter and default they had before the refactor (R12).

``tests/architecture/org_signatures.json`` was generated from the ``core.Org`` that existed before the pre-split; this guard
passes before it (characterization) and after it, and stays in place for every later step.
"""

from __future__ import annotations

import json

import pytest

from orgmcp.app.tests import _signatures

EXPECTED = json.loads(_signatures.SIGNATURES.read_text(encoding="utf-8"))
ACTUAL = _signatures.collect()


def test_the_recorded_surface_is_the_98_methods_of_org_and_the_members_of_message() -> None:
    assert len(EXPECTED["Org"]) == 98
    assert set(EXPECTED["Message"]) == {"__init__", "cut_body", "from_parts", "meta", "parse", "render", "to_text"}  # (``load`` went with the legacy file reader: E2-compat)


@pytest.mark.parametrize("cls", ["Org", "Message"])
def test_no_method_appears_or_disappears(cls: str) -> None:
    assert set(ACTUAL[cls]) == set(EXPECTED[cls])  # type: ignore[call-overload]


@pytest.mark.parametrize("name", sorted(EXPECTED["Org"]))
def test_org_method_keeps_its_signature(name: str) -> None:
    assert _signatures.comparable(ACTUAL["Org"][name]) == _signatures.comparable(EXPECTED["Org"][name])  # type: ignore[index]


@pytest.mark.parametrize("name", sorted(EXPECTED["Message"]))
def test_message_member_keeps_its_signature(name: str) -> None:
    assert _signatures.comparable(ACTUAL["Message"][name]) == _signatures.comparable(EXPECTED["Message"][name])  # type: ignore[index]


def test_message_keeps_its_fields_in_order() -> None:
    assert ACTUAL["MessageFields"] == EXPECTED["MessageFields"]
