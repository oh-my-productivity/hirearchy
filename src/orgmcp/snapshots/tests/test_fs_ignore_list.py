"""``FsIgnoreList``: it writes ``.gitignore`` through the injected writer and nothing else."""

from __future__ import annotations

from pathlib import Path

import pytest

from orgmcp.kernel import OrgPaths
from orgmcp.kernel.testing import FailingAtomicWriter, MemoryAtomicWriter, fs_atomic_writer
from orgmcp.snapshots._ignore import FsIgnoreList

ROOT = Path("/org")


def test_it_writes_the_gitignore_of_the_organization_through_the_writer(tmp_path: Path) -> None:
    writer = MemoryAtomicWriter()
    FsIgnoreList(OrgPaths(tmp_path), writer).write_initial(["a", "b"])
    assert writer.files == {tmp_path / ".gitignore": "a\nb\n"}
    assert not (tmp_path / ".gitignore").exists()  # the in-memory writer wrote it, not the list


def test_a_list_with_nothing_missing_writes_nothing(tmp_path: Path) -> None:
    (tmp_path / ".gitignore").write_text("a\nb\n", encoding="utf-8")
    writer = MemoryAtomicWriter()
    FsIgnoreList(OrgPaths(tmp_path), writer).ensure(["b", "a"])
    assert writer.files == {}


def test_a_full_disk_is_swallowed_by_ensure_and_reported_by_write_initial(tmp_path: Path) -> None:
    writer = FailingAtomicWriter(fs_atomic_writer(tmp_path).writer)
    ignore = FsIgnoreList(OrgPaths(tmp_path), writer)
    ignore.ensure(["a"])
    ignore.ensure_runtime_files()
    assert len(writer.attempts) == 2 and not (tmp_path / ".gitignore").exists()
    with pytest.raises(OSError):
        ignore.write_initial(["a"])


def test_no_temporary_file_is_left_behind(tmp_path: Path) -> None:
    ignore = FsIgnoreList(OrgPaths(tmp_path), fs_atomic_writer(tmp_path).writer)
    ignore.write_initial(["a"])
    ignore.ensure(["b"])
    assert sorted(p.name for p in tmp_path.iterdir()) == [".gitignore"]


def test_the_organization_directory_is_not_created_for_a_gitignore(tmp_path: Path) -> None:
    ignore = FsIgnoreList(OrgPaths(tmp_path / "nowhere"), fs_atomic_writer(tmp_path).writer)
    ignore.ensure_runtime_files()
    assert not (tmp_path / "nowhere").exists()
