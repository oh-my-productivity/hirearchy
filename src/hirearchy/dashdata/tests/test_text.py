"""The vocabulary of text: what a terminal can show, and the words of a pause."""

from __future__ import annotations

from hirearchy.dashdata import Section, clean_text, doc_text, pause_text


def test_a_log_with_control_characters_is_cleaned() -> None:
    assert clean_text("a\x1b[1;31mred\x1b[0m\x07b\x00c\tbell\r\nnext\rdone") == "aredbc\tbell\ndone"


def test_progress_lines_with_carriage_returns_are_reduced_to_their_end() -> None:
    assert clean_text("10%\r50%\r100%\nnext") == "100%\nnext"


def test_an_operating_system_command_loses_its_introducer_but_not_its_text() -> None:
    # characterization of what the dashboard has always done (the pattern for "ESC <one character>" takes the "ESC ]" before the pattern of a whole
    # command can): the ESC and the BEL go as control characters, the title and the charset letters stay. Reported, not fixed.
    assert clean_text("a\x1b]0;title\x07b\x1b(Bc") == "a0;titleb(Bc"


def test_a_pause_does_not_say_paused_twice() -> None:
    assert pause_text("broken") == "paused: broken" and pause_text("paused by the user: x") == "paused by the user: x"
    assert pause_text("Paused by hand") == "Paused by hand"


def test_a_document_is_titled_sections_of_lines() -> None:
    assert doc_text([Section("A", ["x", "y"]), Section("", ["z"])]) == "## A\nx\ny\n\nz\n"
    assert doc_text([]) == "\n"
