# mypy: ignore-errors
"""Text for the panes: sections and event lines as styled ``Text``."""

from __future__ import annotations

from rich.text import Text

from ..dashdata import EventLine, Section


def _plain(value: str) -> Text:
    """Literal text (never markup)."""
    return Text(value)


def doc_renderable(doc: list[Section]) -> Text:
    out = Text()
    for i, s in enumerate(doc):
        if i:
            out.append("\n")
        if s.title:
            out.append(s.title + "\n", style="bold underline")
        for n, line in enumerate(s.lines):
            out.append(line + "\n", style="red" if n in s.errors else "")
    return out


def event_text(lines: list[EventLine]) -> Text:
    """The event lines; refusals and failures in red. Long lines wrap in the pane (nothing is cut)."""
    out = Text()
    for line in lines:
        out.append(line.text + "\n", style="red" if line.error else "")
    return out


def _hidden(widget):
    widget.add_class("hidden")
    return widget
