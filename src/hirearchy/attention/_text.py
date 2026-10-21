"""The words of a message as one line: the first line of a body, the summary of a result, a line cut to a length (moved from ``progress``)."""

from __future__ import annotations

SHORT = 110  # characters of a reason or a note shown on a line


def section(body: str, heading: str) -> list[str]:
    out, inside = [], False
    for line in body.splitlines():
        if line.startswith("## "):
            inside = line[3:].strip().lower() == heading
        elif inside and line.strip():
            out.append(line.strip())
    return out


def summary(body: str) -> str:
    lines = section(body, "summary")
    return lines[0] if lines else (body.splitlines() or [""])[0]


def short(text: str, limit: int = SHORT) -> str:
    text = " ".join(text.split())
    text = text if len(text) <= limit else text[: limit - 1].rstrip() + "…"
    return text.rstrip(".")
