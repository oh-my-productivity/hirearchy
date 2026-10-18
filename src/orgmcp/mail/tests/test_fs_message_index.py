"""``FsMessageIndex`` only: it walks the directories and asks the meta reader (whose cache is a process resource) for each file.

What every index gives is in ``test_contract_message_index``."""

from __future__ import annotations

from pathlib import Path

import pytest

from orgmcp.agents.testing import MemoryAgents
from orgmcp.kernel import OrgPaths
from orgmcp.mail import MessageIndex
from orgmcp.mail._index import FsMessageIndex, StampCachedMetaReader

from ._support import message_text, mid


BAD_ENCODING = b"\xff\xfe not text"


class CountingReads(StampCachedMetaReader):
    def __init__(self) -> None:
        super().__init__()
        self.misses = 0

    def _read_text(self, path: Path) -> str:
        self.misses += 1
        return super()._read_text(path)


def index(root: Path, agents: list[str], meta: StampCachedMetaReader | None = None) -> FsMessageIndex:
    directory = MemoryAgents()
    for addr in agents:
        directory.put(f"{addr}/AGENT.md", "---\nrole: R\n---\nx\n")
    return FsMessageIndex(OrgPaths(root), directory, meta or StampCachedMetaReader())


def put(root: Path, addr: str, box: str, n: int, text: str | None = None) -> Path:
    path = (root if addr == "root" else root / addr) / box / f"{mid(n)}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text if text is not None else message_text(mid(n), to=addr), encoding="utf-8")
    return path


def test_it_is_a_message_index(tmp_path: Path) -> None:
    assert isinstance(index(tmp_path, []), MessageIndex)


def test_building_one_touches_nothing(tmp_path: Path) -> None:
    index(tmp_path / "absent", ["ceo"])
    assert not (tmp_path / "absent").exists()


def test_a_second_scan_reads_no_file(tmp_path: Path) -> None:
    """ARCHITECTURE.md 10.1 risk 1: the meta cache keeps its hits (a count, not a time)."""
    meta = CountingReads()
    scanner = index(tmp_path, ["ceo"], meta)
    for n in range(30):
        put(tmp_path, "ceo", "inbox", n)
    assert len(scanner.scan()) == 30 and meta.misses == 30
    for _ in range(3):
        assert len(scanner.scan()) == 30
    assert meta.misses == 30


def test_a_changed_file_is_read_again_and_only_that_one(tmp_path: Path) -> None:
    meta = CountingReads()
    scanner = index(tmp_path, ["ceo"], meta)
    paths = [put(tmp_path, "ceo", "inbox", n) for n in range(10)]
    scanner.scan()
    paths[3].write_text("changed, and another size\n", encoding="utf-8")
    assert [f.error for f in scanner.scan()].count("no frontmatter") == 1 and meta.misses == 11


def test_two_indexes_share_the_cache_they_are_given(tmp_path: Path) -> None:
    """The cache is a process resource: every runtime of the process reads through the same one."""
    meta = CountingReads()
    for n in range(5):
        put(tmp_path, "ceo", "inbox", n)
    index(tmp_path, ["ceo"], meta).scan()
    index(tmp_path, ["ceo"], meta).scan()
    assert meta.misses == 5


def test_a_file_that_cannot_be_decoded_is_listed_as_unreadable(tmp_path: Path) -> None:
    path = put(tmp_path, "ceo", "inbox", 1)
    path.write_bytes(BAD_ENCODING)
    [f] = index(tmp_path, ["ceo"]).scan()
    assert f.meta is None and f.error == "unreadable (UnicodeDecodeError)" and f.mtime == 0.0 and f.id == mid(1)


def test_a_box_that_is_a_file_is_skipped(tmp_path: Path) -> None:
    (tmp_path / "ceo").mkdir()
    (tmp_path / "ceo" / "inbox").write_text("not a directory", encoding="utf-8")
    put(tmp_path, "ceo", "read", 1)
    assert [(f.box, f.id) for f in index(tmp_path, ["ceo"]).scan()] == [("read", mid(1))]


def test_the_agents_are_the_ones_the_directory_lists_in_its_order(tmp_path: Path) -> None:
    for addr in ("cto", "ceo", "ceo/eng"):
        put(tmp_path, addr, "inbox", 1, text=message_text(mid(1), to=addr))
    put(tmp_path, "root", "inbox", 2)
    assert [f.owner for f in index(tmp_path, ["ceo", "ceo/eng", "cto"]).scan()] == ["root", "ceo", "ceo/eng", "cto"]
    assert [f.owner for f in index(tmp_path, ["cto"]).scan()] == ["root", "cto"]  # the others are not (or no longer) agents
