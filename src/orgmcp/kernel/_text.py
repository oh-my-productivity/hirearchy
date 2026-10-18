"""Small pure text helpers."""

from __future__ import annotations

import re
from collections.abc import Iterable

TITLE_MAX = 80  # default length of a title-like text

_FENCE_LINE = re.compile(r"\s*(?:`{3,}|~{3,})\S*\s*")
_LINE_MARKER = re.compile(r"\s*(?:>|#{1,6}(?=\s)|[-*+\u2022](?=\s)|\d{1,3}[.)](?=\s)|\[[ xX]\](?=\s))")
_MARKUP_ONLY = re.compile(r"[#*+=_~`>|:\-\u2022]+")


def word_count(text: str) -> int:
    """Words of ``text`` for word limits: markdown markers (``#``, ``-``, ``*``, ``1.``, ``|``, ``---``, fence lines,
    ``>``, checkboxes) are not words; the words next to them are."""
    total = 0
    for line in text.splitlines():
        if _FENCE_LINE.fullmatch(line):
            continue
        if line.lstrip().startswith("|"):  # table row: the pipes are delimiters
            line = line.replace("|", " ")
        while (m := _LINE_MARKER.match(line)) and m.end() > 0:
            line = line[m.end():]
        total += sum(1 for tok in line.split() if not _MARKUP_ONLY.fullmatch(tok))
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
