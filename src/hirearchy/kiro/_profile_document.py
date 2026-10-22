"""The JSON document of a kiro agent profile."""

from __future__ import annotations

import json
from collections.abc import Mapping
from copy import deepcopy
from typing import cast

from ..kernel import JsonObject
from .api import Confinement


PROFILE_PROMPT = (
    "You are a member of a file-based agent organization. The user message contains your rules, charter, memory, state and new messages "
    "for this run. Follow it exactly, act through the hirearchy tools, and stop when the messages are handled. The hirearchy tools are "
    'deferred: load them with tool_load (tool_ids ["hirearchy::*"] loads all of them), then call each with tool_call and tool_id '
    '"hirearchy::<name>", for example hirearchy::whoami. Where the rules say @hirearchy/<name>, use hirearchy::<name>.'
)


def kiro_profile(name: str, description: str, server: JsonObject, confinement: Confinement) -> JsonObject:
    """A kiro-cli V3 agent profile that loads only the hirearchy server and whatever ``confinement`` selects and allows.

    No pre-V3 tool-permission keys (V3 rejects them) and no ``model`` (``--model`` is always passed); nothing from the user's
    global configuration is included (``includeMcpJson`` and ``includePowers`` are false, no resources, no hooks).
    """
    return {
        "name": name,
        "description": description,
        "prompt": PROFILE_PROMPT,
        "mcpServers": {"hirearchy": deepcopy(server)},
        "tools": list(confinement.tools),
        "resources": [],
        "hooks": [],
        "includeMcpJson": False,
        "includePowers": False,
        "permissions": {"rules": deepcopy(list(confinement.rules))},
    }


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
