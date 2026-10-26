"""``MovingMessageParser``: the parser that moves a file just before it reads it (the seam of the race between a listing and a read)."""

from __future__ import annotations

from pathlib import Path

import pytest

from hirearchy.mail import MessageParser
from hirearchy.mail.testing import MovingMessageParser

from ._support import message_text, mid


def write(directory: Path, n: int) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{mid(n)}.md"
    path.write_text(message_text(mid(n)), encoding="utf-8")
    return path


def test_it_is_a_message_parser() -> None:
    assert isinstance(MovingMessageParser({}), MessageParser)


def test_it_moves_the_file_on_the_first_matching_parse_only(tmp_path: Path) -> None:
    source = write(tmp_path / "inbox", 1)
    target = tmp_path / "read" / source.name
    target.parent.mkdir()
    parser = MovingMessageParser({source: target})
    with pytest.raises(FileNotFoundError):
        parser.parse(source)
    assert not source.exists() and target.is_file() and parser.moved == [source]
    source.write_text(message_text(mid(1)), encoding="utf-8")  # put back, it is not moved again
    assert parser.parse(source).id == mid(1) and parser.moved == [source]


def test_the_error_is_the_real_one_of_the_open(tmp_path: Path) -> None:
    source = write(tmp_path / "inbox", 1)
    (tmp_path / "read").mkdir()
    parser = MovingMessageParser({source: tmp_path / "read" / source.name})
    with pytest.raises(FileNotFoundError) as caught:
        parser.parse(source)
    assert caught.value.filename == str(source)


def test_the_match_is_made_on_resolved_paths(tmp_path: Path) -> None:
    """``tmp_path`` spelled through a symlink (macOS: ``/var`` against ``/private/var``) is the same file."""
    real = tmp_path / "real"
    source = write(real / "inbox", 1)
    (tmp_path / "link").symlink_to(real, target_is_directory=True)
    (real / "read").mkdir()
    parser = MovingMessageParser({source: real / "read" / source.name})
    with pytest.raises(FileNotFoundError):
        parser.parse(tmp_path / "link" / "inbox" / source.name)
    assert parser.moved == [source]


def test_a_path_that_is_no_source_parses_as_the_caching_parser_does(tmp_path: Path) -> None:
    source, other = write(tmp_path / "inbox", 1), write(tmp_path / "inbox", 2)
    (tmp_path / "read").mkdir()
    parser = MovingMessageParser({source: tmp_path / "read" / source.name})
    assert parser.parse(other).id == mid(2) and parser.moved == [] and source.is_file()
    assert parser.parse(other).id == mid(2) and len(parser.cache) == 1
