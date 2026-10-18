"""Contract of ``MessageParser``: the caching parser and its counting variant pass the same tests."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from orgmcp.kernel import Message
from orgmcp.mail import MessageParser
from orgmcp.mail.testing import IMPLEMENTATIONS, ParserHarness

from ._support import make_parser, message_text, mid, raises_a_parse_error


pytestmark = pytest.mark.xfail(strict=True, reason="red: A-mail")

FILE = message_text(mid(1), title="Title: with colon", budget=3, body="line1\nline2")


@pytest.fixture(params=IMPLEMENTATIONS[MessageParser], ids=lambda factory: factory.__name__)
def h(request: pytest.FixtureRequest, tmp_path: Path) -> ParserHarness:
    made = make_parser(request, tmp_path)
    assert isinstance(made.parser, MessageParser)
    return made


def write(directory: Path, text: str = FILE, name: str | None = None) -> Path:
    path = directory / (name or f"{mid(1)}.md")
    path.write_text(text, encoding="utf-8")
    return path


def test_a_parsed_file_equals_the_pure_parse_of_its_text(h: ParserHarness, tmp_path: Path) -> None:
    path = write(tmp_path)
    parsed = h.parser.parse(path)
    assert parsed == Message.parse(FILE, path) and parsed.path == path and parsed.budget == 3 and parsed.title == "Title: with colon"


def test_crlf_files_parse_like_read_text(h: ParserHarness, tmp_path: Path) -> None:
    path = tmp_path / f"{mid(2)}.md"
    path.write_bytes(b"---\r\nfrom: root\r\nto: ceo\r\ntype: note\r\n---\r\nline1\r\nline2\r\n")
    parsed = h.parser.parse(path)
    assert parsed.body == "line1\nline2" and parsed.sender == "root"


def test_an_unchanged_file_is_parsed_once_and_every_call_gets_a_fresh_message(h: ParserHarness, tmp_path: Path) -> None:
    path = write(tmp_path)
    first, second = h.parser.parse(path), h.parser.parse(path)
    assert h.parses() == 1 and first == second and first is not second
    first.body = "mutated"  # messages are mutable: the cache holds the parts, not the object
    assert h.parser.parse(path).body == "line1\nline2"


def test_a_changed_file_is_parsed_again(h: ParserHarness, tmp_path: Path) -> None:
    path = write(tmp_path)
    h.parser.parse(path)
    path.write_text(FILE.replace("line1", "LINE1!"), encoding="utf-8")  # same path, new size
    assert h.parser.parse(path).body.startswith("LINE1!") and h.parses() == 2


def test_the_same_size_with_a_new_mtime_is_parsed_again(h: ParserHarness, tmp_path: Path) -> None:
    path = write(tmp_path)
    h.parser.parse(path)
    stat = path.stat()
    os.utime(path, ns=(stat.st_atime_ns, stat.st_mtime_ns + 1_000_000_000))
    h.parser.parse(path)
    assert h.parses() == 2


def test_two_files_are_two_parses(h: ParserHarness, tmp_path: Path) -> None:
    h.parser.parse(write(tmp_path, name=f"{mid(1)}.md"))
    h.parser.parse(write(tmp_path, name=f"{mid(2)}.md"))
    assert h.parses() == 2


def test_the_id_of_a_file_without_one_is_its_name(h: ParserHarness, tmp_path: Path) -> None:
    path = write(tmp_path, "---\nfrom: root\nto: ceo\ntype: note\n---\nhi\n", name=f"{mid(3)}.md")
    assert h.parser.parse(path).id == mid(3)


def test_a_missing_file_raises_like_open(h: ParserHarness, tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        h.parser.parse(tmp_path / "absent.md")


def test_a_file_that_does_not_parse_raises_and_is_not_remembered(h: ParserHarness, tmp_path: Path) -> None:
    path = write(tmp_path, "---\nfrom: [unclosed\n---\nbody\n")
    raises_a_parse_error(lambda: h.parser.parse(path))
    path.write_text(FILE, encoding="utf-8")
    assert h.parser.parse(path).budget == 3
