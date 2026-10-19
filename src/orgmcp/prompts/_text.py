"""Small pure helpers of the texts."""

from __future__ import annotations


def indent(text: str, n: int) -> str:
    return "\n".join(" " * n + line for line in text.splitlines())
