"""Contract of ``ProfileStore``: profiles by name, written atomically, unreadable ones are as good as missing."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from orgmcp.kiro import ProfileStore
from orgmcp.kiro.testing import IMPLEMENTATIONS, StoreHarness

from ._support import RED, make

pytestmark = pytest.mark.xfail(strict=True, reason=RED)

PROFILE = {"name": "orgmcp-a-123456", "tools": ["@orgmcp", "read"], "hooks": {}, "includeMcpJson": False, "näme": "ü ✓"}


@pytest.fixture(params=IMPLEMENTATIONS[ProfileStore], ids=lambda factory: factory.__name__)
def h(request: pytest.FixtureRequest, tmp_path: Path) -> StoreHarness:
    made = make(request, tmp_path, StoreHarness)
    assert isinstance(made.store, ProfileStore)
    return made


def test_a_profile_that_was_never_written_is_none(h: StoreHarness) -> None:
    assert h.store.read("orgmcp-a-123456") is None
    assert h.names() == []


def test_what_was_written_is_read_back(h: StoreHarness) -> None:
    h.store.write("orgmcp-a-123456", PROFILE)
    assert h.store.read("orgmcp-a-123456") == PROFILE
    assert h.names() == ["orgmcp-a-123456.json"]


def test_the_profile_is_indented_json_with_a_final_newline(h: StoreHarness) -> None:
    h.store.write("orgmcp-a-123456", PROFILE)
    assert h.text("orgmcp-a-123456") == json.dumps(PROFILE, indent=2) + "\n"


def test_a_second_write_replaces_the_first(h: StoreHarness) -> None:
    h.store.write("orgmcp-a-123456", PROFILE)
    h.store.write("orgmcp-a-123456", {"name": "second"})
    assert h.store.read("orgmcp-a-123456") == {"name": "second"}
    assert h.names() == ["orgmcp-a-123456.json"]


def test_profiles_do_not_see_each_other(h: StoreHarness) -> None:
    h.store.write("orgmcp-a-111111", {"name": "a"})
    h.store.write("orgmcp-b-222222", {"name": "b"})
    assert h.store.read("orgmcp-a-111111") == {"name": "a"} and h.store.read("orgmcp-b-222222") == {"name": "b"}
    assert h.names() == ["orgmcp-a-111111.json", "orgmcp-b-222222.json"]


def test_a_profile_that_is_not_json_is_none_and_can_be_replaced(h: StoreHarness) -> None:
    h.put_raw("orgmcp-a-123456", "{ not json")
    assert h.store.read("orgmcp-a-123456") is None
    h.store.write("orgmcp-a-123456", PROFILE)
    assert h.store.read("orgmcp-a-123456") == PROFILE


@pytest.mark.parametrize("raw", ["[1, 2]", '"text"', "3", "null", ""])
def test_a_profile_that_is_not_an_object_is_none(h: StoreHarness, raw: str) -> None:
    h.put_raw("orgmcp-a-123456", raw)
    assert h.store.read("orgmcp-a-123456") is None


def test_a_profile_is_not_changed_by_a_later_change_of_what_was_written(h: StoreHarness) -> None:
    data: dict[str, object] = {"name": "x", "tools": ["a"]}
    h.store.write("orgmcp-a-123456", data)
    tools = data["tools"]
    assert isinstance(tools, list)
    tools.append("b")
    assert h.store.read("orgmcp-a-123456") == {"name": "x", "tools": ["a"]}


def test_a_profile_that_was_read_is_a_copy(h: StoreHarness) -> None:
    h.store.write("orgmcp-a-123456", PROFILE)
    first = h.store.read("orgmcp-a-123456")
    assert first is not None
    first["name"] = "changed"
    assert h.store.read("orgmcp-a-123456") == PROFILE
