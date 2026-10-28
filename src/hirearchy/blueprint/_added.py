"""The added section of a charter (design 5.1): ``## Added by your changes`` and its tagged lines. Only an extension writes it."""

from __future__ import annotations

import re
from collections.abc import Sequence

from ..services import line_key

ADDED_HEADING = "## Added by your changes"
TAG = " [change {plan_id}]"
LIMITS_LINE = "Your hiring limits were set by the user's change: up to {m} direct reports; may hire: {hire}."
_TAG_AT_END = re.compile(r" \[change [^\]]+\]$")
_HEADING = re.compile(r"^## ")


def untagged(line: str) -> str:
    """The text of a tagged line of the added section (``- {text} [change {id}]``) without its bullet and its tag."""
    text = line.strip()
    text = text[2:] if text.startswith("- ") else text
    return _TAG_AT_END.sub("", text).strip()


def added_section(body: str) -> tuple[int, int] | None:
    """The line numbers ``[start, end)`` of the lines under the heading of the added section, or None when there is no such heading."""
    lines = body.splitlines()
    for n, line in enumerate(lines):
        if line.strip() == ADDED_HEADING:
            end = next((m for m in range(n + 1, len(lines)) if _HEADING.match(lines[m])), len(lines))
            return n + 1, end
    return None


def added_lines(body: str) -> list[str]:
    """The untagged text of every line under the added section's heading (the lines of this change's tags and of earlier ones), in order."""
    found = added_section(body)
    if found is None:
        return []
    lines = body.splitlines()[found[0] : found[1]]
    return [untagged(x) for x in lines if x.strip()]


def holds_line(body: str, line: str) -> bool:
    """Whether the added section already has ``line`` (compared by ``line_key``)."""
    return line_key(line) in {line_key(x) for x in added_lines(body)}


def keys(lines: Sequence[str]) -> list[str]:
    return [line_key(x) for x in lines]


CHECKER_LINE = "{agent} ({role}) was added to your team to check {services}{why}"


def checker_line(agent: str, role: str, services: Sequence[str], extra: str) -> str:
    """The line an extension adds to the charter of the agent a new verifier joins (design 5.5 step 4): who joined, and what for (the first sentence of
    the verifier's own instructions, when it has any)."""
    first = re.split(r"(?<=[.!?])\s", " ".join(extra.split()), maxsplit=1)[0] if extra.strip() else ""
    return CHECKER_LINE.format(agent=agent, role=role, services=", ".join(services), why=f": {first}" if first else ".")
