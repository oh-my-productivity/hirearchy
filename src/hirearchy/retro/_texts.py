"""The fixed texts of the retro brief (design 4.3, 4.7, 7), each a constant beside the module that uses it; a line that holds a value is a ``str.format`` template.

The questions are one sentence of at most 300 characters and end with ``?``; the words of the user that a question quotes are cut to ``QUOTE`` characters."""

from __future__ import annotations

from datetime import datetime, timezone

from ..kernel import clip_line

QUOTE = 80  # the characters of the user's words a question quotes
BLOCK_WORDS = 120  # the characters of the user's words the block shows of a rejection
BLOCK_LINES = 5  # the lines a section shows in the user's block
DETAIL_LINES = 20  # the lines a section shows in Details
BLOCK_MORE = "- and {j} more (Details)"
DETAIL_MORE = "- and {j} more: retro(since=...) lists them all for a shorter window"
NONE = "- none"
UNREADABLE = "- {service}: cannot be read ({error})"

HEADINGS = {
    "d1": "What you said", "d2": "What got past a check", "d3": "Rejections with no criterion yet", "d4": "Alarms and causes to settle",
    "d5": "Work you ask for again and again", "d6": "Idle or stranded agents",
}

CAUSE_UNTYPED = (
    '{ref} ({service}, {date}): "{words}". Was it a gap in the criteria (the team met them), a check that missed it, or a one-off?'
)
CAUSE_DISPUTED = "{ref} ({service}): the rules read it as {type} and as {also}. Was it {type_words}?"
TYPE_WORDS = {
    "contract-gap": "a gap in the criteria", "reviewer-miss": "a check that missed it", "relayed-error": "an error of the assistant's own reading",
    "relayed-carry-over": "carried over from the assistant's own rework", "untyped": "untyped",
}


def day(when: datetime | None) -> str:
    """The date of ``when`` (UTC) as ``YYYY-MM-DD``."""
    return "unknown date" if when is None else when.astimezone(timezone.utc).strftime("%Y-%m-%d")


def quoted(words: str, limit: int = QUOTE) -> str:
    """The user's words on one line, cut to ``limit`` characters."""
    return clip_line(words, limit)


def cause_question(ref: str, service: str, when: datetime | None, words: str, kind: str, also: tuple[str, ...]) -> str:
    """The one question of an escape whose cause is untyped or disputed (7.6)."""
    if kind == "untyped":
        return CAUSE_UNTYPED.format(ref=ref, service=service, date=day(when), words=quoted(words))
    return CAUSE_DISPUTED.format(ref=ref, service=service, type=kind, also=", ".join(also), type_words=TYPE_WORDS.get(kind, kind))
