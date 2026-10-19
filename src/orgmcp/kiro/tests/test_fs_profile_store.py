"""``FsProfileStore``: the profiles in ``<agents directory>/<name>.json``, through the atomic writer it is given."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from orgmcp.kernel import AtomicWriter
from orgmcp.kernel.testing import FailingAtomicWriter, MemoryAtomicWriter, fs_atomic_writer
from orgmcp.kiro import ProfileStore
from orgmcp.kiro._profiles import FsProfileStore


def test_it_is_a_profile_store() -> None:
    assert isinstance(FsProfileStore(lambda: Path("/agents"), MemoryAtomicWriter()), ProfileStore)


def test_the_directory_is_asked_on_every_use(tmp_path: Path) -> None:
    current = {"directory": tmp_path / "one"}
    store = FsProfileStore(lambda: current["directory"], fs_atomic_writer(tmp_path).writer)
    store.write("orgmcp-a-123456", {"name": "first"})
    current["directory"] = tmp_path / "two"
    assert store.read("orgmcp-a-123456") is None
    store.write("orgmcp-a-123456", {"name": "second"})
    assert (tmp_path / "one" / "orgmcp-a-123456.json").is_file() and (tmp_path / "two" / "orgmcp-a-123456.json").is_file()
    assert json.loads((tmp_path / "one" / "orgmcp-a-123456.json").read_text(encoding="utf-8")) == {"name": "first"}


def test_the_directory_is_made_by_the_first_write(tmp_path: Path) -> None:
    directory = tmp_path / "a" / "b" / "agents"
    FsProfileStore(lambda: directory, fs_atomic_writer(tmp_path).writer).write("orgmcp-a-123456", {"name": "x"})
    assert [p.name for p in directory.iterdir()] == ["orgmcp-a-123456.json"]


def test_a_missing_directory_has_no_profiles(tmp_path: Path) -> None:
    assert FsProfileStore(lambda: tmp_path / "nowhere", fs_atomic_writer(tmp_path).writer).read("orgmcp-a-123456") is None


def test_the_file_is_written_through_the_atomic_writer_with_the_exact_text(tmp_path: Path) -> None:
    writer = MemoryAtomicWriter()
    FsProfileStore(lambda: tmp_path / "agents", writer).write("orgmcp-a-123456", {"name": "ü", "tools": ["a"]})
    assert writer.files == {tmp_path / "agents" / "orgmcp-a-123456.json": json.dumps({"name": "ü", "tools": ["a"]}, indent=2) + "\n"}


def test_a_write_that_fails_leaves_the_profile_as_it_was(tmp_path: Path) -> None:
    directory = tmp_path / "agents"
    FsProfileStore(lambda: directory, fs_atomic_writer(tmp_path).writer).write("orgmcp-a-123456", {"name": "old"})
    failing: AtomicWriter = FailingAtomicWriter(fs_atomic_writer(tmp_path).writer)
    with pytest.raises(OSError):
        FsProfileStore(lambda: directory, failing).write("orgmcp-a-123456", {"name": "new"})
    assert json.loads((directory / "orgmcp-a-123456.json").read_text(encoding="utf-8")) == {"name": "old"}
    assert [p.name for p in directory.iterdir()] == ["orgmcp-a-123456.json"]  # and nothing else


def test_a_file_that_is_not_utf8_is_unreadable_not_fatal(tmp_path: Path) -> None:
    (tmp_path / "orgmcp-a-123456.json").write_bytes(b"\xff\xfe{")
    assert FsProfileStore(lambda: tmp_path, fs_atomic_writer(tmp_path).writer).read("orgmcp-a-123456") is None


def test_a_directory_in_the_place_of_a_profile_is_unreadable_not_fatal(tmp_path: Path) -> None:
    (tmp_path / "orgmcp-a-123456.json").mkdir()
    assert FsProfileStore(lambda: tmp_path, fs_atomic_writer(tmp_path).writer).read("orgmcp-a-123456") is None
