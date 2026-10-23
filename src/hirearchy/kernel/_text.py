"""Small pure text helpers."""

from __future__ import annotations

import itertools
import re
from collections.abc import Iterable

TITLE_MAX = 80  # default length of a title-like text

_FENCE_LINE = re.compile(r"\s*(?:`{3,}|~{3,})\S*\s*")
_LINE_MARKER = re.compile(r"\s*(?:>|#{1,6}(?=\s)|[-*+\u2022](?=\s)|\d{1,3}[.)](?=\s)|\[[ xX]\](?=\s))")
_MARKUP_ONLY = re.compile(r"[#*+=_~`>|:\-\u2022]+")


_QUESTIONS_MARKER = "questions for the client"
_LIST_PREFIX = re.compile(r"[-*+\u2022]\s+")
_LIST_LINE = re.compile(r"\s*(?:[-*+\u2022]|\d{1,3}[.)])\s+(.*)")
_NONE_WORDS = frozenset({"none", "no", "n/a", "-"})


def _is_none_word(word: str) -> bool:
    return word.strip(":*_").lower().rstrip(".") in _NONE_WORDS


def client_questions(body: str) -> list[str]:
    """The items of the first "Questions for the client:" block of a message body, in order (pure).

    The marker line (a leading list marker, ``#``, ``*`` and ``_`` are ignored) starts with "questions for the client" in any case. What
    follows the phrase on that line is one item, unless it is empty or its first word is a "none" word (``none``, ``no``, ``n/a``, ``-``).
    The list lines after it (``-``, ``*``, ``+``, ``\u2022``, ``1.`` or ``1)``), after any blank lines, are items too; the block ends at the
    first blank line, heading or non-list line. A list line that is only a "none" word is no item."""
    lines = body.splitlines()
    for start, line in enumerate(lines):
        text = _LIST_PREFIX.sub("", line.strip(), count=1).lstrip("#*_ ")
        if not text.lower().startswith(_QUESTIONS_MARKER):
            continue
        inline = text[len(_QUESTIONS_MARKER):].strip(":*_ ")
        first_word = next(iter(inline.replace(";", " ").replace(",", " ").split()), "")  # "" when the line holds only separators
        items = [inline] if first_word and not _is_none_word(first_word) else []
        following = iter(lines[start + 1:])
        for ln in itertools.dropwhile(lambda x: not x.strip(), following):  # blank lines right after the marker are skipped
            m = _LIST_LINE.fullmatch(ln)
            if m is None:
                break
            item = m.group(1).strip()
            if item and not _is_none_word(item):
                items.append(item)
        return items
    return []


def artifact_paths(body: str) -> list[str]:
    """The paths of the ``## Artifacts`` section of a result body (pure): its non-blank lines (the heading is read in any case; any other ``## ``
    heading ends the section), each stripped, without its ``-``/``*`` bullet, and cut at the first `` (`` (the runtime's word-count note)."""
    paths: list[str] = []
    inside = False
    for line in body.splitlines():
        if line.startswith("## "):
            inside = line[3:].strip().lower() == "artifacts"
        elif inside and line.strip():
            paths.append(line.strip().lstrip("-* ").split(" (", 1)[0])
    return paths


def strip_markers(line: str) -> str:
    """``line`` without its leading markdown markers (``>``, ``#``..``######``, ``-``, ``*``, ``+``, ``\u2022``, ``1.``/``1)`` up to 3 digits,
    ``[ ]``/``[x]``), removed repeatedly from the start, and the blanks that follow them; the words after are untouched (pure)."""
    while (m := _LINE_MARKER.match(line)) and m.end() > 0:
        line = line[m.end():]
    return line.lstrip()


def word_count(text: str) -> int:
    """Words of ``text`` for word limits: markdown markers (``#``, ``-``, ``*``, ``1.``, ``|``, ``---``, fence lines,
    ``>``, checkboxes) are not words; the words next to them are."""
    total = 0
    for line in text.splitlines():
        if _FENCE_LINE.fullmatch(line):
            continue
        if line.lstrip().startswith("|"):  # table row: the pipes are delimiters
            line = line.replace("|", " ")
        total += sum(1 for tok in strip_markers(line).split() if not _MARKUP_ONLY.fullmatch(tok))
    return total


def clip(value: object, limit: int = TITLE_MAX) -> str:
    """``value`` as text of at most ``limit`` characters (an ellipsis marks a cut)."""
    text = value if isinstance(value, str) else str(value)
    return text if len(text) <= limit else text[: max(0, limit - 1)] + "…"


def clip_line(text: object, limit: int) -> str:
    """``text`` on one line (blanks collapsed), at most ``limit`` characters (an ellipsis marks a cut)."""
    text = " ".join(str(text).split())
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def single(traces: Iterable[str | None]) -> str | None:
    """The one distinct non-null item of ``traces``, else None."""
    distinct = {t for t in traces if t}
    return next(iter(distinct)) if len(distinct) == 1 else None
