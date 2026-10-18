"""Small pure text helpers."""

from __future__ import annotations

from collections.abc import Iterable

TITLE_MAX = 80  # default length of a title-like text


def word_count(text: str) -> int:
    """Words of ``text`` for word limits: markdown markers are not words; the words next to them are."""
    raise NotImplementedError("red: K1")


def clip(value: object, limit: int = TITLE_MAX) -> str:
    """``value`` as text of at most ``limit`` characters (an ellipsis marks a cut)."""
    raise NotImplementedError("red: K1")


def clip_line(text: object, limit: int) -> str:
    """``text`` on one line (blanks collapsed), at most ``limit`` characters (an ellipsis marks a cut)."""
    raise NotImplementedError("red: K1")


def single(traces: Iterable[str | None]) -> str | None:
    """The one distinct non-null item of ``traces``, else None."""
    raise NotImplementedError("red: K1")
