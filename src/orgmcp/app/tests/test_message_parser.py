"""``CachingMessageParser`` (the parse cache that was ``core._PARSED``) and the legacy ``Message.load`` that is served by it.

The cache tests are the ones of ``test_scheduler_robustness`` (QA-13) restated against the class; those themselves keep running
against ``core.Message.load`` and ``core._PARSED`` until step A-mail converts them.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from orgmcp import core
from orgmcp.app import _compat, wiring
from orgmcp.app._resources import CachingMessageParser
from orgmcp.kernel import JsonObject, Message, split_frontmatter

RED = pytest.mark.xfail(strict=True, reason="red: M2")  # until the facade attaches Message.load and core aliases the cache

FILE = "---\nid: 20260101T000000000000-root-aaaa\nfrom: root\nto: ceo\ntype: task\ntitle: 'Title: with colon'\nbudget: 3\n---\nline1\nline2\n"


class CountingSplit:
    def __init__(self) -> None:
        self.calls = 0

    def __call__(self, text: str) -> tuple[JsonObject, str]:
        self.calls += 1
        return split_frontmatter(text)


def write(directory: Path, name: str = "20260101T000000000000-root-aaaa.md", text: str = FILE) -> Path:
    path = directory / name
    path.write_text(text, encoding="utf-8")
    return path


def test_a_parsed_file_equals_the_pure_parse_of_its_text(tmp_path: Path) -> None:
    path = write(tmp_path)
    parsed = CachingMessageParser().parse(path)
    assert parsed == Message.parse(FILE, path) and parsed.path == path and parsed.budget == 3 and parsed.title == "Title: with colon"


def test_crlf_files_parse_like_read_text(tmp_path: Path) -> None:
    path = tmp_path / "20260101T000000000000-root-bbbb.md"
    path.write_bytes(b"---\r\nfrom: root\r\nto: ceo\r\ntype: note\r\n---\r\nline1\r\nline2\r\n")
    parsed = CachingMessageParser().parse(path)
    assert parsed.body == "line1\nline2" and parsed.sender == "root"


def test_an_unchanged_file_is_parsed_once_and_every_call_gets_a_fresh_message(tmp_path: Path) -> None:
    path, split = write(tmp_path), CountingSplit()
    parser = CachingMessageParser(split=split)
    first, second = parser.parse(path), parser.parse(path)
    assert split.calls == 1 and first == second and first is not second
    first.body = "mutated"  # messages are mutable: the cache holds the parts, not the object
    assert parser.parse(path).body == "line1\nline2"


def test_a_changed_file_is_parsed_again(tmp_path: Path) -> None:
    path, split = write(tmp_path), CountingSplit()
    parser = CachingMessageParser(split=split)
    parser.parse(path)
    path.write_text(FILE.replace("line1", "LINE1!"), encoding="utf-8")  # same path, new size
    assert parser.parse(path).body.startswith("LINE1!") and split.calls == 2


def test_the_same_size_with_a_new_mtime_is_parsed_again(tmp_path: Path) -> None:
    path, split = write(tmp_path), CountingSplit()
    parser = CachingMessageParser(split=split)
    parser.parse(path)
    stat = path.stat()
    os.utime(path, ns=(stat.st_atime_ns, stat.st_mtime_ns + 1_000_000_000))
    parser.parse(path)
    assert split.calls == 2


def test_the_cache_is_bounded_and_keeps_the_most_recently_used(tmp_path: Path) -> None:
    parser = CachingMessageParser(max_entries=5)
    paths = [write(tmp_path, f"20260101T00000000000{i}-root-aaaa.md") for i in range(8)]
    for path in paths[:5]:
        parser.parse(path)
    parser.parse(paths[0])  # the oldest is used again: it is now the newest
    for path in paths[5:]:
        parser.parse(path)
    assert len(parser.cache) == 5
    assert str(paths[0]) in parser.cache and str(paths[1]) not in parser.cache and str(paths[7]) in parser.cache


def test_parse_as_builds_the_class_it_is_asked_for(tmp_path: Path) -> None:
    class Special(Message):
        pass

    path = write(tmp_path)
    assert type(CachingMessageParser().parse_as(Special, path)) is Special
    assert type(CachingMessageParser().parse(path)) is Message


def test_clear_empties_the_cache_in_place(tmp_path: Path) -> None:
    parser = CachingMessageParser()
    cache = parser.cache
    parser.parse(write(tmp_path))
    parser.clear()
    assert parser.cache is cache and not cache


def test_a_missing_file_raises_like_open(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        CachingMessageParser().parse(tmp_path / "absent.md")


# ---------------------------------------------------------------------------------------------- the legacy patch points


def test_the_process_parser_reads_the_limit_and_the_splitter_from_core_at_call_time(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    parser = wiring.process_resources().message_parser
    assert isinstance(parser, _compat.PatchPointMessageParser)
    split = CountingSplit()
    monkeypatch.setattr(core, "split_frontmatter", split)
    monkeypatch.setattr(core, "_PARSED_MAX", 2)
    parser.clear()
    for i in range(4):
        parser.parse(write(tmp_path, f"20260101T00000000000{i}-root-aaaa.md"))
    assert split.calls == 4 and len(parser.cache) == 2 and parser.max_entries == 2


@RED
def test_core_parsed_is_the_cache_of_the_process_parser() -> None:
    assert core._PARSED is wiring.process_resources().message_parser.cache


@RED
def test_message_load_is_served_by_the_process_parser(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path, split = write(tmp_path), CountingSplit()
    monkeypatch.setattr(core, "split_frontmatter", split)
    wiring.process_resources().reset()
    first, second = Message.load(path), Message.load(path)  # type: ignore[attr-defined]
    assert split.calls == 1 and first == second and first is not second and type(first) is Message
    assert str(path) in wiring.process_resources().message_parser.cache



@RED
def test_message_load_is_attached_by_the_composition_root_not_by_core() -> None:
    load = vars(Message)["load"]
    assert isinstance(load, classmethod) and load.__func__.__module__ == "orgmcp.app._compat"
    assert not hasattr(core, "_load_message")


@RED
def test_a_fresh_interpreter_that_imports_only_the_kernel_message_can_load(tmp_path: Path) -> None:
    path = write(tmp_path)
    code = (
        "import sys\n"
        "from orgmcp.kernel import Message\n"
        f"m = Message.load(__import__('pathlib').Path({str(path)!r}))\n"
        "assert m.sender == 'root' and m.budget == 3\n"
        "assert Message.load.__func__.__module__ == 'orgmcp.app._compat'\n"
        "assert 'orgmcp.app' in sys.modules\n"
    )
    done = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=False, timeout=60)
    assert done.returncode == 0, done.stderr
