"""``StampCachedMetaReader``: the front matter of a message file, read once per ``(path, mtime_ns, size)`` (what ``observe._META_CACHE`` was)."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from orgmcp.mail._index import MetaReader, StampCachedMetaReader

from ._support import BAD_BUDGET, message_text, mid


pytestmark = pytest.mark.xfail(strict=True, reason="red: A-mail")


def write(directory: Path, n: int = 1, text: str | None = None) -> Path:
    path = directory / f"{mid(n)}.md"
    path.write_text(text if text is not None else message_text(mid(n)), encoding="utf-8")
    return path


class CountingReads(StampCachedMetaReader):
    """Counts the files whose text was actually read (a cache hit does not read)."""

    def __init__(self, max_entries: int = 50_000) -> None:
        super().__init__(max_entries)
        self.misses = 0

    def _read_text(self, path: Path) -> str:
        self.misses += 1
        return super()._read_text(path)


def test_it_is_a_meta_reader() -> None:
    assert isinstance(StampCachedMetaReader(), MetaReader)


def test_the_cache_holds_fifty_thousand_entries_by_default() -> None:
    assert StampCachedMetaReader().max_entries == 50_000


def test_it_reads_the_front_matter_the_finding_and_the_mtime(tmp_path: Path) -> None:
    path = write(tmp_path)
    meta, error, mtime = StampCachedMetaReader().read(path)
    assert meta is not None and meta["id"] == mid(1) and error is None and mtime == path.stat().st_mtime


def test_a_file_is_read_once_however_often_it_is_asked_for(tmp_path: Path) -> None:
    reader, path = CountingReads(), write(tmp_path)
    results = [reader.read(path) for _ in range(5)]
    assert reader.misses == 1 and len(set(map(repr, results))) == 1


def test_a_changed_file_is_read_again(tmp_path: Path) -> None:
    reader, path = CountingReads(), write(tmp_path)
    reader.read(path)
    write(tmp_path, text="no front matter, another size\n")
    assert reader.read(path)[1] == "no frontmatter" and reader.misses == 2


def test_the_same_size_with_a_new_mtime_is_read_again(tmp_path: Path) -> None:
    reader, path = CountingReads(), write(tmp_path)
    reader.read(path)
    stat = path.stat()
    os.utime(path, ns=(stat.st_atime_ns, stat.st_mtime_ns + 1_000_000_000))
    reader.read(path)
    assert reader.misses == 2


def test_a_finding_is_remembered_too(tmp_path: Path) -> None:
    reader, path = CountingReads(), write(tmp_path, text=BAD_BUDGET)
    assert reader.read(path)[1] == "budget is not a number: 'lots'" and reader.read(path)[1] == "budget is not a number: 'lots'"
    assert reader.misses == 1


def test_a_hit_still_reports_the_current_mtime(tmp_path: Path) -> None:
    reader, path = StampCachedMetaReader(), write(tmp_path)
    assert reader.read(path)[2] == reader.read(path)[2] == path.stat().st_mtime


def test_a_file_that_is_not_there_is_unreadable(tmp_path: Path) -> None:
    assert StampCachedMetaReader().read(tmp_path / "absent.md") == (None, "unreadable (FileNotFoundError)", 0.0)


def test_a_file_that_is_not_text_is_unreadable_and_not_remembered(tmp_path: Path) -> None:
    reader, path = StampCachedMetaReader(), tmp_path / f"{mid(1)}.md"
    path.write_bytes(b"\xff\xfe\x00 no")
    assert reader.read(path) == (None, "unreadable (UnicodeDecodeError)", 0.0) and reader.cache == {}


def test_a_directory_is_unreadable(tmp_path: Path) -> None:
    (tmp_path / "d.md").mkdir()
    meta, error, mtime = StampCachedMetaReader().read(tmp_path / "d.md")
    assert meta is None and error is not None and error.startswith("unreadable (") and mtime == 0.0


def test_the_cache_is_emptied_when_it_grows_past_its_limit(tmp_path: Path) -> None:
    """The former behaviour, kept: past the limit the whole cache goes (the next scan fills it again)."""
    reader = StampCachedMetaReader(max_entries=3)
    for n in range(4):
        reader.read(write(tmp_path, n))
    assert len(reader.cache) == 4  # the check is made before the insert, as it always was
    reader.read(write(tmp_path, 4))
    assert len(reader.cache) == 1


def test_clear_empties_the_cache_in_place(tmp_path: Path) -> None:
    reader = StampCachedMetaReader()
    cache = reader.cache
    reader.read(write(tmp_path))
    reader.clear()
    assert reader.cache is cache and not cache


def test_crlf_files_read_like_read_text(tmp_path: Path) -> None:
    path = tmp_path / f"{mid(1)}.md"
    path.write_bytes(b"---\r\nfrom: root\r\nto: ceo\r\ntype: note\r\n---\r\nbody\r\n")
    assert StampCachedMetaReader().read(path)[:2] == ({"from": "root", "to": "ceo", "type": "note"}, None)
