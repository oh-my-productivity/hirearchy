"""The lines of a charter the user approved (design 6.6, CHARTER-ADDED): the section ``## Added by your changes``, which only an extension writes."""

from __future__ import annotations

import re

ADDED_HEADING = "## Added by your changes"
CHARTER_ADDED = (
    'refused: the lines under "## Added by your changes" are the user\'s (approved in a plan); keep them exactly as they are, and put your own text under '
    "another heading. Nothing was written."
)
_HEADING = re.compile(r"^## ")


def _key(line: str) -> str:
    """The words of a line, case-folded (its letters and digits): spacing, bullets and punctuation never make two lines differ, a change of a word does.
    (``services.line_key`` strips list numbering and checkboxes too; ``orgfiles`` does not depend on ``services``, and the section has neither.)"""
    return "".join(ch for ch in line.casefold() if ch.isalnum())


def added_keys(text: str) -> list[str]:
    """The keys of the lines under the heading of the added section of the charter ``text`` (blank lines aside), in order; ``[]`` without the section."""
    lines = text.splitlines()
    start = next((n for n, line in enumerate(lines) if line.strip() == ADDED_HEADING), None)
    if start is None:
        return []
    end = next((n for n in range(start + 1, len(lines)) if _HEADING.match(lines[n])), len(lines))
    return [key for line in lines[start + 1 : end] if (key := _key(line))]
