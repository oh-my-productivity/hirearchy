"""``CachingMessageParser``: the parse cache that was ``core._PARSED`` (50 000 entries, least recently used first, keyed by path and
stamped by ``(mtime_ns, size)``). The behaviour every parser has is in ``test_contract_message_parser``; this is what only this one does."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from hirearchy.kernel import JsonObject, Message, split_frontmatter
from hirearchy.mail import MessageParser
from hirearchy.mail._parser import CachingMessageParser

from ._support import message_text, mid


class CountingSplit:
    def __init__(self) -> None:
        self.calls = 0

    def __call__(self, text: str) -> tuple[JsonObject, str]:
        self.calls += 1
        return split_frontmatter(text)


def write(directory: Path, n: int) -> Path:
    path = directory / f"{mid(n)}.md"
    path.write_text(message_text(mid(n)), encoding="utf-8")
    return path


def test_it_is_a_message_parser() -> None:
    assert isinstance(CachingMessageParser(), MessageParser)


def test_the_cache_holds_fifty_thousand_entries_by_default() -> None:
    assert CachingMessageParser().max_entries == 50_000


def test_the_cache_is_bounded_and_keeps_the_most_recently_used(tmp_path: Path) -> None:
    parser = CachingMessageParser(max_entries=5)
    paths = [write(tmp_path, i) for i in range(8)]
    for path in paths[:5]:
        parser.parse(path)
    parser.parse(paths[0])  # the oldest is used again: it is now the newest
    for path in paths[5:]:
        parser.parse(path)
    assert len(parser.cache) == 5
    assert str(paths[0]) in parser.cache and str(paths[1]) not in parser.cache and str(paths[7]) in parser.cache


def test_an_evicted_file_is_parsed_again(tmp_path: Path) -> None:
    split = CountingSplit()
    parser = CachingMessageParser(max_entries=2, split=split)
    paths = [write(tmp_path, i) for i in range(3)]
    for path in paths:
        parser.parse(path)
    parser.parse(paths[0])  # evicted by the third
    assert split.calls == 4


def test_the_cache_is_keyed_by_the_path(tmp_path: Path) -> None:
    split = CountingSplit()
    parser = CachingMessageParser(split=split)
    first, second = write(tmp_path, 1), tmp_path / "copy.md"
    second.write_bytes(first.read_bytes())
    parser.parse(first)
    parser.parse(second)
    assert split.calls == 2 and sorted(parser.cache) == sorted([str(first), str(second)])


def test_what_the_cache_keeps_is_the_stamp_and_the_parts(tmp_path: Path) -> None:
    path = write(tmp_path, 1)
    parser = CachingMessageParser()
    parser.parse(path)
    stamp, meta, body = parser.cache[str(path)]
    stat = path.stat()
    assert stamp == (stat.st_mtime_ns, stat.st_size) and meta["id"] == mid(1) and body == "body\n"


def test_parse_as_builds_the_class_it_is_asked_for(tmp_path: Path) -> None:
    class Special(Message):
        pass

    path = write(tmp_path, 1)
    assert type(CachingMessageParser().parse_as(Special, path)) is Special
    assert type(CachingMessageParser().parse(path)) is Message


def test_clear_empties_the_cache_in_place(tmp_path: Path) -> None:
    parser = CachingMessageParser()
    cache = parser.cache
    parser.parse(write(tmp_path, 1))
    parser.clear()
    assert parser.cache is cache and not cache


def test_a_cleared_cache_parses_again(tmp_path: Path) -> None:
    split = CountingSplit()
    parser = CachingMessageParser(split=split)
    path = write(tmp_path, 1)
    parser.parse(path)
    parser.clear()
    parser.parse(path)
    assert split.calls == 2


def test_a_file_with_the_same_mtime_and_size_is_taken_to_be_the_same_file(tmp_path: Path) -> None:
    """The stamp is all the cache looks at (messages are immutable files): that is what makes a hit cheap."""
    parser = CachingMessageParser()
    path = write(tmp_path, 1)
    stat = path.stat()
    assert parser.parse(path).body == "body"
    path.write_text(message_text(mid(1), body="BODY"), encoding="utf-8")  # same size
    os.utime(path, ns=(stat.st_atime_ns, stat.st_mtime_ns))
    assert parser.parse(path).body == "body"
