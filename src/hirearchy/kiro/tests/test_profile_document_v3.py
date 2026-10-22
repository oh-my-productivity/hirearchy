"""``kiro_profile``: the V3 JSON document of a kiro agent profile (docs/design/kiro-runtime-v3.md 4.1 and 4.5; the golden files are the
hand-written examples of 4.5)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from hirearchy.kernel import JsonObject
from hirearchy.kiro import Confinement
from hirearchy.kiro._confinement import KiroConfinementPolicy
from hirearchy.kiro._profile_document import PROFILE_PROMPT, kiro_profile, parse_profile, render_profile

from ._support import GOLDEN

ORG = "/Users/u/acme/org"
SERVER: JsonObject = {"command": "/venv/bin/hirearchy", "args": ["mcp"], "env": {"ORG_ROOT": ORG, "ORG_REQUIRE_AGENT": "1"}}
DESCRIPTION = f"internal: used by the hirearchy scheduler for {ORG}; not a general-purpose agent"
MCP: JsonObject = {"capability": "mcp", "match": ["hirearchy/*"], "effect": "allow"}
SKILL: JsonObject = {"capability": "skill", "effect": "deny"}
CONTEXT: JsonObject = {"capability": "context", "effect": "deny"}
PROMPT = (
    "You are a member of a file-based agent organization. The user message contains your rules, charter, memory, state and new messages "
    "for this run. Follow it exactly, act through the hirearchy tools, and stop when the messages are handled. The hirearchy tools are "
    'deferred: load them with tool_load (tool_ids ["hirearchy::*"] loads all of them), then call each with tool_call and tool_id '
    '"hirearchy::<name>", for example hirearchy::whoami. Where the rules say @hirearchy/<name>, use hirearchy::<name>.'
)


def no_tools() -> JsonObject:
    c = Confinement(("@hirearchy",), (MCP, SKILL, CONTEXT), (), None)
    return kiro_profile("hirearchy-acme-org-1a2b3c", DESCRIPTION, SERVER, c)


def shell_web() -> JsonObject:
    rules: tuple[JsonObject, ...] = (
        MCP,
        {"capability": "shell", "match": ["*"], "effect": "allow"},
        {"capability": "web_fetch", "match": ["*"], "effect": "allow"},
        {"capability": "web_search", "match": ["*"], "effect": "allow"},
        SKILL,
        CONTEXT,
    )
    c = Confinement(("@hirearchy", "shell", "web"), rules, (), None)
    return kiro_profile(
        "hirearchy-acme-org-1a2b3c-shell-web-fetch-web-search", DESCRIPTION + " (built-in tools: shell, web_fetch, web_search)", SERVER, c
    )


def read_write_shell() -> JsonObject:
    c = KiroConfinementPolicy().file_confinement(
        Path(ORG), ["read", "write", "shell"], Path("/Users/u/proj"), [Path("/Users/u/handbook")]
    )
    return kiro_profile(
        "hirearchy-acme-org-1a2b3c-read-shell-write-x0badf00d", DESCRIPTION + " (built-in tools: read, shell, write)", SERVER, c
    )


EXAMPLES = {"kiro_profile_v3_no_tools": no_tools, "kiro_profile_v3_shell_web": shell_web, "kiro_profile_v3_read_write_shell": read_write_shell}


@pytest.mark.parametrize("name", sorted(EXAMPLES))
def test_each_4_5_example_is_the_document_byte_for_byte(name: str) -> None:
    assert render_profile(EXAMPLES[name]()) == (GOLDEN / f"{name}.json").read_bytes().decode("utf-8")


@pytest.mark.parametrize("name", sorted(EXAMPLES))
def test_no_legacy_keys(name: str) -> None:
    assert not {"allowedTools", "toolsSettings", "model"} & set(EXAMPLES[name]())


@pytest.mark.parametrize("name", sorted(EXAMPLES))
def test_the_fixed_fields_and_their_order(name: str) -> None:
    data = EXAMPLES[name]()
    assert list(data) == [
        "name", "description", "prompt", "mcpServers", "tools", "resources", "hooks", "includeMcpJson", "includePowers", "permissions"
    ]
    assert data["resources"] == [] and data["hooks"] == []
    assert data["includeMcpJson"] is False and data["includePowers"] is False
    assert data["mcpServers"] == {"hirearchy": SERVER}


def test_the_tools_and_rules_are_the_confinement_s() -> None:
    c = KiroConfinementPolicy().file_confinement(Path(ORG), ["read"], None, [])
    data = kiro_profile("n", "d", SERVER, c)
    assert data["tools"] == list(c.tools) and data["permissions"] == {"rules": list(c.rules)}


def test_the_prompt_is_PROFILE_PROMPT() -> None:
    assert PROFILE_PROMPT == PROMPT and "\n" not in PROFILE_PROMPT
    assert no_tools()["prompt"] == PROFILE_PROMPT
    for needle in ("tool_load", 'tool_ids ["hirearchy::*"]', "tool_call", "hirearchy::whoami", "@hirearchy/<name>"):
        assert needle in PROFILE_PROMPT


def test_the_document_does_not_share_the_confinement_s_lists() -> None:
    c = Confinement(("@hirearchy",), (MCP, SKILL, CONTEXT), (), None)
    data = kiro_profile("n", "d", SERVER, c)
    assert isinstance(data["tools"], list) and isinstance(data["permissions"], dict)
    data["tools"].append("x")
    assert c.tools == ("@hirearchy",)


def test_a_rendered_profile_is_indented_json_and_parses_back() -> None:
    text = render_profile(no_tools())
    assert text == json.dumps(no_tools(), indent=2) + "\n" and parse_profile(text) == no_tools()
    assert parse_profile("not json") is None and parse_profile("[1]") is None
