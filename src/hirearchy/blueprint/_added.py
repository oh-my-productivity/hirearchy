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


LIMITS_PREFIX = "Your hiring limits were set by the user's change:"


def tagged(line: str, plan_id: str) -> str:
    return f"- {line}{TAG.format(plan_id=plan_id)}"


def limits_line(max_children: int, can_hire: bool) -> str:
    return LIMITS_LINE.format(m=max_children, hire="yes" if can_hire else "no")


def with_changes(body: str, add: Sequence[str], remove: Sequence[str], limits: str | None, plan_id: str) -> str:
    """The charter body with the added section changed (design 5.1): ``remove`` takes out the lines whose ``line_key`` it names, ``add`` appends tagged
    lines, ``limits`` (the text of a limits line, see :func:`limits_line`) replaces the limits line, which stays last. The heading is created at the
    end of the body by the first line and goes when the section is empty; nothing outside the section is touched."""
    lines = body.splitlines()
    found = added_section(body)
    start, end = (found[0] - 1, found[1]) if found is not None else (len(lines), len(lines))
    kept = [x for x in lines[start + 1 : end] if x.strip()] if found is not None else []
    drop = {line_key(x) for x in remove}
    kept = [x for x in kept if line_key(untagged(x)) not in drop]
    limit = [x for x in kept if untagged(x).startswith(LIMITS_PREFIX)]
    others = [x for x in kept if not untagged(x).startswith(LIMITS_PREFIX)]
    others += [tagged(x, plan_id) for x in add]
    last = [tagged(limits, plan_id)] if limits is not None else limit
    section = [*others, *last]
    before = "\n".join(lines[:start]).rstrip()
    after = "\n".join(lines[end:]).strip("\n")
    if not section:
        return "\n\n".join(x for x in (before, after) if x)
    return "\n\n".join(x for x in (before, "\n".join([ADDED_HEADING, *section]), after) if x)
