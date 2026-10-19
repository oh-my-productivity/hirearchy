"""The words of a message as one line: the first line of a body, the summary of a result, a line cut to a length (moved from ``progress``)."""

from __future__ import annotations

SHORT = 110  # characters of a reason or a note shown on a line


def section(body: str, heading: str) -> list[str]:
    raise NotImplementedError("red: C-attention")


def summary(body: str) -> str:
    raise NotImplementedError("red: C-attention")


def short(text: str, limit: int = SHORT) -> str:
    raise NotImplementedError("red: C-attention")
