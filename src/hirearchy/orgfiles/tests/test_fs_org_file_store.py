"""``FsOrgFileStore``: what holds only for the files of a real filesystem.

Symbolic links (``resolve`` and ``kind`` follow them), bytes that are not UTF-8, universal newlines on reading, permissions, a relative path
that is the organization's rather than the working directory's, and the atomic writer the store is given."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from hirearchy.kernel import AtomicWriter, OrgPaths
from hirearchy.kernel.testing import FailingAtomicWriter, MemoryAtomicWriter
from hirearchy.orgfiles import OrgFileStore
from hirearchy.orgfiles._store import FsOrgFileStore
from hirearchy.orgfiles.testing import StoreHarness, fs_org_file_store


@pytest.fixture
def h(tmp_path: Path) -> StoreHarness:
    return fs_org_file_store(tmp_path)


def store_with(h: StoreHarness, writer: AtomicWriter) -> OrgFileStore:
    return FsOrgFileStore(OrgPaths(h.root), writer)


def test_a_relative_path_is_the_organizations_not_the_working_directorys(h: StoreHarness, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(h.outside)
    assert h.store.resolve(Path("ceo/x.md")) == h.root / "ceo" / "x.md"


def test_resolve_follows_symbolic_links(h: StoreHarness) -> None:
    h.put(h.outside / "real" / "f.md", "x")
    os.symlink(h.outside / "real", h.root / "link")
    assert h.store.resolve(h.root / "link" / "f.md") == h.outside / "real" / "f.md"
    assert h.store.resolve(h.root / "link") == h.outside / "real"


def test_a_link_to_a_path_that_is_not_there_resolves_to_where_it_points(h: StoreHarness) -> None:
    os.symlink(h.outside / "later", h.root / "dangling")
    assert h.store.resolve(h.root / "dangling") == h.outside / "later"


def test_kind_follows_symbolic_links(h: StoreHarness) -> None:
    h.put(h.outside / "real" / "f.md", "x")
    os.symlink(h.outside / "real", h.root / "dirlink")
    os.symlink(h.outside / "real" / "f.md", h.root / "filelink")
    os.symlink(h.outside / "gone", h.root / "broken")
    assert (h.store.kind(h.root / "dirlink"), h.store.kind(h.root / "filelink"), h.store.kind(h.root / "broken")) == ("dir", "file", "missing")


def test_a_link_is_an_entry_under_its_own_name(h: StoreHarness) -> None:
    os.symlink(h.outside, h.root / "Link")
    assert h.store.entries(h.root) == ["Link"]


def test_text_that_is_not_utf_8_is_an_error_unless_the_handler_replaces_it(h: StoreHarness) -> None:
    (h.root / "bin.md").write_bytes(b"ok \xff\xfe end")
    with pytest.raises(UnicodeDecodeError):
        h.store.read_text(h.root / "bin.md")
    assert h.store.read_text(h.root / "bin.md", "replace") == "ok \ufffd\ufffd end"


def test_reading_translates_line_endings_as_text_files_do(h: StoreHarness) -> None:
    (h.root / "crlf.md").write_bytes(b"a\r\nb\rc\n")
    assert h.store.read_text(h.root / "crlf.md") == "a\nb\nc\n"


def test_writing_does_not_translate_line_endings(h: StoreHarness) -> None:
    h.store.write_text(h.root / "w.md", "a\r\nb\n")
    assert (h.root / "w.md").read_bytes() == b"a\r\nb\n"


def test_modified_is_the_modification_time_of_the_file(h: StoreHarness) -> None:
    h.put(h.root / "f.md", "x")
    os.utime(h.root / "f.md", (1_000_000_000, 1_000_000_000))
    assert h.store.modified(h.root / "f.md").timestamp() == 1_000_000_000


@pytest.mark.skipif(os.geteuid() == 0, reason="root reads every directory")
def test_a_directory_that_cannot_be_listed_is_an_error_not_an_empty_directory(h: StoreHarness) -> None:
    h.put(h.root / "closed" / "f.md", "x")
    (h.root / "closed").chmod(0)
    try:
        with pytest.raises(PermissionError):
            h.store.entries(h.root / "closed")
    finally:
        (h.root / "closed").chmod(0o755)


def test_the_text_is_written_through_the_atomic_writer_it_is_given(h: StoreHarness) -> None:
    writer = MemoryAtomicWriter()
    store_with(h, writer).write_text(h.root / "ceo" / "w.md", "text")
    assert writer.files == {h.root / "ceo" / "w.md": "text"}
    assert not (h.root / "ceo").exists()


def test_a_failing_write_leaves_the_old_file_and_raises_the_error_of_the_writer(h: StoreHarness) -> None:
    h.put(h.root / "f.md", "old")
    store = store_with(h, FailingAtomicWriter(MemoryAtomicWriter()))
    with pytest.raises(OSError, match="No space left"):
        store.write_text(h.root / "f.md", "new")
    assert h.read(h.root / "f.md") == "old"


def test_the_real_store_leaves_no_temporary_file_when_the_write_goes_through(h: StoreHarness) -> None:
    h.store.write_text(h.root / "d" / "f.md", "x")
    assert sorted(os.listdir(h.root / "d")) == ["f.md"]
