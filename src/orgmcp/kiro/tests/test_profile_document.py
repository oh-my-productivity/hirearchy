"""``kiro_profile``: the JSON document of a kiro agent profile (moved from ``templates``; the golden files are the ones captured there)."""

from __future__ import annotations

import json

import pytest

from orgmcp.kernel import JsonObject
from orgmcp.kiro._profile_document import kiro_profile

from ._support import GOLDEN

CASES: dict[str, tuple[tuple[object, ...], dict[str, object]]] = {
    "kiro_profile_plain": (
        ("orgmcp-ceo", "agent ceo", ["@orgmcp"], {"command": "orgmcp", "args": ["mcp"], "env": {"ORG_ROOT": "/org", "ORG_AGENT": "ceo"}}), {},
    ),
    "kiro_profile_allowed": (
        ("orgmcp-ceo-eng", "agent ceo/eng", ["@orgmcp", "read", "write"], {"command": "orgmcp", "args": ["mcp"]}),
        {"allowed_tools": ["@orgmcp"], "tools_settings": {"write": {"allowedPaths": ["/ws"]}, "read": {"allowedPaths": ["/ws", "/org"]}}},
    ),
    "kiro_profile_empty_settings": (
        ("orgmcp-ceo", "agent ceo", ["@orgmcp"], {"command": "orgmcp"}), {"allowed_tools": [], "tools_settings": {}},
    ),
}


def profile(name: str) -> JsonObject:
    args, kwargs = CASES[name]
    return kiro_profile(*args, **kwargs)  # type: ignore[arg-type]  # the cases pass keyword arguments from a table


@pytest.mark.parametrize("name", sorted(CASES))
def test_the_kiro_profile_is_unchanged(name: str) -> None:
    assert json.dumps(profile(name), indent=2) + "\n" == (GOLDEN / f"{name}.json").read_bytes().decode("utf-8")


def test_the_keys_come_in_the_order_kiro_documents_them() -> None:
    assert list(profile("kiro_profile_plain")) == ["name", "description", "prompt", "mcpServers", "tools", "allowedTools", "resources", "hooks", "includeMcpJson"]
    assert list(profile("kiro_profile_allowed")) == [
        "name", "description", "prompt", "mcpServers", "tools", "allowedTools", "resources", "hooks", "includeMcpJson", "toolsSettings"]


def test_without_allowed_tools_every_tool_is_allowed() -> None:
    data = profile("kiro_profile_plain")
    assert data["tools"] == data["allowedTools"] == ["@orgmcp"]


def test_an_empty_list_of_allowed_tools_is_not_the_default() -> None:
    assert profile("kiro_profile_empty_settings")["allowedTools"] == []


def test_empty_tool_settings_are_left_out() -> None:
    assert "toolsSettings" not in profile("kiro_profile_empty_settings")


def test_the_user_s_global_mcp_json_is_not_loaded() -> None:
    assert profile("kiro_profile_plain")["includeMcpJson"] is False
