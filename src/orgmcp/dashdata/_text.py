"""Terminal-safe text, and the words of a pause."""

from __future__ import annotations

import re

_ANSI = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]|\x1b[@-Z\\-_]|\x1b\].*?(?:\x07|\x1b\\)")
_CONTROL = re.compile(r"[\x00-\x08\x0b-\x1f\x7f]")


def clean_text(text: str) -> str:
    """Terminal-safe text: no ANSI escapes, no control characters, carriage-return progress lines reduced to their end."""
    text = _ANSI.sub("", text)
    if "\r" in text:
        text = "\n".join(line.rsplit("\r", 1)[-1] for line in text.replace("\r\n", "\n").split("\n"))
    return _CONTROL.sub("", text)


def pause_text(paused: str) -> str:
    """'paused: <reason>' - without saying 'paused' twice when the reason already does ('paused by the user: ...')."""
    return paused if paused.lower().startswith("paused") else f"paused: {paused}"
