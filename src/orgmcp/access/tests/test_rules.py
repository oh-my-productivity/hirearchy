"""The pure rule of ``access``: which charters are legacy (their built-in ``read`` is not confined)."""

from __future__ import annotations

import pytest

from orgmcp.access import unconfined_read

from ._support import RED

pytestmark = pytest.mark.xfail(strict=True, reason=RED)


@pytest.mark.parametrize(
    ("meta", "expected"),
    [
        ({}, True),
        ({"role": "R", "tools": ["read", "write"], "can_hire": True}, True),
        ({"workspace": None}, True),
        ({"workspace": ""}, True),
        ({"workspace": "/w"}, False),
        ({"inputs": []}, False),
        ({"inputs": None}, False),
        ({"inputs": ["/in"], "workspace": ""}, False),
        ({"workspace": "/w", "inputs": ["/in"]}, False),
    ],
)
def test_no_workspace_and_no_inputs_key_is_a_legacy_charter(meta: dict[str, object], expected: bool) -> None:
    assert unconfined_read(meta) is expected


def test_it_only_looks_at_the_mapping_it_is_given() -> None:
    meta: dict[str, object] = {"role": "R"}
    unconfined_read(meta)
    assert meta == {"role": "R"}
