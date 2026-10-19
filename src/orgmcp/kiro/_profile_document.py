"""The JSON document of a kiro agent profile."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from typing import cast

from ..kernel import JsonObject


def kiro_profile(
    name: str, description: str, tools: Sequence[str], mcp_server: JsonObject, *,
    allowed_tools: Sequence[str] | None = None, tools_settings: JsonObject | None = None,
) -> JsonObject:
    """A kiro-cli agent profile that loads only the orgmcp server (not the user's global mcp.json).

    ``allowed_tools`` = the tools kiro runs without asking (default: all of ``tools``). A tool that is NOT in it and has
    ``tools_settings`` with ``allowedPaths`` runs unprompted only on those paths; anything else needs an approval,
    which a ``--no-interactive`` run cannot give, so it is refused. A tool in ``allowed_tools`` ignores its
    ``allowedPaths`` entirely (only ``deniedPaths`` still apply), so confined tools must be left out of it.
    """
    data = {
        "name": name,
        "description": description,
        "prompt": (
            "You are a member of a file-based agent organization. The user message contains your "
            "rules, charter, memory, state and new messages for this run. Follow it exactly, act "
            "through the orgmcp tools, and stop when the messages are handled."
        ),
        "mcpServers": {"orgmcp": mcp_server},
        "tools": tools,
        "allowedTools": tools if allowed_tools is None else allowed_tools,
        "resources": [],
        "hooks": {},
        "includeMcpJson": False,
    }
    if tools_settings:
        data["toolsSettings"] = tools_settings
    return data


def render_profile(data: Mapping[str, object]) -> str:
    """The text of a profile file: indented JSON and a final newline."""
    return json.dumps(data, indent=2) + "\n"


def parse_profile(text: str) -> dict[str, object] | None:
    """The profile in ``text``; ``None`` when it is not JSON or not a JSON object (a profile that is as good as missing)."""
    try:
        data = json.loads(text)
    except ValueError:
        return None
    return cast("dict[str, object]", data) if isinstance(data, dict) else None
