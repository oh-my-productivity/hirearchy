"""The text of the panes: sections and event lines as styled ``Text``, and the helper that hides a widget until it is needed."""

from __future__ import annotations

from textual.widgets import Static

from hirearchy.dashboard._render import _hidden, doc_renderable, event_text
from hirearchy.dashdata import EventLine, Section


def styles(text: object) -> list[tuple[str, str]]:
    """(text, style) of every styled stretch."""
    plain = getattr(text, "plain")
    return [(plain[span.start:span.end], str(span.style)) for span in getattr(text, "spans")]


def test_a_section_is_its_title_in_bold_underline_and_its_lines() -> None:
    text = doc_renderable([Section("Needs you (1)", ["a note", "another"])])
    assert text.plain == "Needs you (1)\na note\nanother\n"
    assert ("Needs you (1)\n", "bold underline") in styles(text)


def test_sections_are_apart_by_a_blank_line_and_a_section_without_title_has_none() -> None:
    text = doc_renderable([Section("", ["first"]), Section("Second", ["x"])])
    assert text.plain == "first\n\nSecond\nx\n"


def test_the_lines_that_are_errors_are_red() -> None:
    text = doc_renderable([Section("Cases", ["ok", "broken", "fine"], frozenset({1}))])
    assert ("broken\n", "red") in styles(text)
    assert "ok\n" not in [t for t, _ in styles(text)]


def test_no_sections_is_no_text() -> None:
    assert doc_renderable([]).plain == ""


def test_event_lines_are_one_per_row_and_refusals_and_failures_are_red() -> None:
    text = event_text([EventLine("10:00:01 ceo inbox ok", False), EventLine("10:00:02 ceo delegate REFUSED: no budget", True)])
    assert text.plain == "10:00:01 ceo inbox ok\n10:00:02 ceo delegate REFUSED: no budget\n"
    assert styles(text) == [("10:00:02 ceo delegate REFUSED: no budget\n", "red")]


def test_a_widget_is_hidden_by_a_class_and_handed_back() -> None:
    widget = Static("x")
    assert _hidden(widget) is widget and widget.has_class("hidden")
