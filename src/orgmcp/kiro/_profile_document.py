"""The JSON document of a kiro agent profile."""

from __future__ import annotations

from collections.abc import Sequence

from ..kernel import JsonObject


def kiro_profile(
    name: str, description: str, tools: Sequence[str], mcp_server: JsonObject, *,
    allowed_tools: Sequence[str] | None = None, tools_settings: JsonObject | None = None,
) -> JsonObject:
    raise NotImplementedError
