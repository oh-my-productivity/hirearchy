"""``CachingMessageParser`` (the parse cache that was ``core._PARSED``) and the process parser that serves it.

The cache tests are the ones of ``test_scheduler_robustness`` (QA-13) restated against the class (A-mail converted those to inject a
parser through ``open_runtime``; ``core._PARSED`` stays, the cache of the process parser; the classmethod ``Message.load`` is gone: E2-compat).
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from orgmcp import core
from orgmcp.app import wiring
from orgmcp.kernel import JsonObject, Message, split_frontmatter
from orgmcp.mail._parser import CachingMessageParser


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


# ---------------------------------------------------------------------------------------------- the process parser


def test_the_process_parser_is_a_plain_caching_parser_with_the_limit_core_names(tmp_path: Path) -> None:
    """Nothing reads ``core._PARSED_MAX`` or ``core.split_frontmatter`` at call time any more (A-mail): the parser is what it is built as."""
    parser = wiring.process_resources().message_parser
    assert type(parser) is CachingMessageParser and parser.max_entries == core._PARSED_MAX == 50_000


def test_core_parsed_is_the_cache_of_the_process_parser() -> None:
    assert core._PARSED is wiring.process_resources().message_parser.cache


def test_the_process_parser_serves_a_file_from_its_cache(tmp_path: Path) -> None:
    path = write(tmp_path)
    wiring.process_resources().reset()
    first = wiring.process_resources().message_parser.parse(path)
    entry = wiring.process_resources().message_parser.cache[str(path)]
    second = wiring.process_resources().message_parser.parse(path)
    assert wiring.process_resources().message_parser.cache[str(path)] is entry  # served from the cache: not parsed again
    assert first == second and first is not second and type(first) is Message


def test_the_kernel_message_is_pure_data_and_core_has_no_loader() -> None:
    assert not hasattr(Message, "load") and not hasattr(core, "_load_message")


def test_a_fresh_interpreter_that_imports_only_the_kernel_message_has_no_loader_and_the_process_parser_loads(tmp_path: Path) -> None:
    path = write(tmp_path)
    code = (
        "import sys\n"
        "from orgmcp.kernel import Message\n"
        "from orgmcp.app import wiring\n"
        f"m = wiring.process_resources().message_parser.parse(__import__('pathlib').Path({str(path)!r}))\n"
        "assert m.sender == 'root' and m.budget == 3\n"
        "assert not hasattr(Message, 'load')\n"
        "assert 'orgmcp.app' in sys.modules\n"
    )
    done = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=False, timeout=60)
    assert done.returncode == 0, done.stderr
