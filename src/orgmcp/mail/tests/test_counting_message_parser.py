"""``CountingMessageParser``: the parser whose cache behaviour a test can read (``loaded`` files asked for, ``parses`` actually parsed)."""

from __future__ import annotations

from pathlib import Path

import pytest

from orgmcp.mail import MessageParser
from orgmcp.mail.testing import CountingMessageParser

from ._support import message_text, mid


pytestmark = pytest.mark.xfail(strict=True, reason="red: A-mail")


def write(directory: Path, n: int) -> Path:
    path = directory / f"{mid(n)}.md"
    path.write_text(message_text(mid(n)), encoding="utf-8")
    return path


def test_it_is_a_message_parser() -> None:
    assert isinstance(CountingMessageParser(), MessageParser)


def test_it_counts_the_files_asked_for_and_the_files_parsed(tmp_path: Path) -> None:
    parser = CountingMessageParser()
    a, b = write(tmp_path, 1), write(tmp_path, 2)
    for path in (a, b, a, a, b):
        parser.parse(path)
    assert parser.loaded == [a, b, a, a, b] and parser.parses == 2


def test_a_changed_file_counts_as_another_parse(tmp_path: Path) -> None:
    parser = CountingMessageParser()
    path = write(tmp_path, 1)
    parser.parse(path)
    path.write_text(message_text(mid(1), body="a longer body than before"), encoding="utf-8")
    parser.parse(path)
    assert parser.parses == 2 and len(parser.loaded) == 2


def test_it_has_the_limit_it_is_given(tmp_path: Path) -> None:
    parser = CountingMessageParser(max_entries=3)
    for n in range(6):
        parser.parse(write(tmp_path, n))
    assert parser.max_entries == 3 and len(parser.cache) == 3 and parser.parses == 6
