"""``MemoryAgents``: the in-memory registry and the file tree it keeps (the fake that consumers' unit tests may use)."""

from __future__ import annotations

from pathlib import Path

import pytest

from orgmcp.agents import AgentDirectory, AgentRegistry, CharterReader, RetiredArchive
from orgmcp.agents.testing import MemoryAgents, MemoryArchiveFiles


def test_it_is_all_four_ports() -> None:
    fake = MemoryAgents()
    assert isinstance(fake, AgentDirectory) and isinstance(fake, CharterReader)
    assert isinstance(fake, AgentRegistry) and isinstance(fake, RetiredArchive)


def test_a_new_one_is_an_organization_without_agents() -> None:
    fake = MemoryAgents()
    assert fake.agents() == [] and fake.exists("root") and fake.trees() == [] and fake.run_count() == 0


def test_put_makes_the_directories_above_the_file() -> None:
    fake = MemoryAgents()
    fake.put("a/b/c.txt", "x")
    assert fake.listing("") == ["a"] and fake.listing("a") == ["b"] and fake.listing("a/b") == ["c.txt"]
    assert fake.read("a/b/c.txt") == "x" and fake.read("a/b") is None and fake.listing("a/b/c.txt") is None and fake.listing("zz") is None


def test_put_dir_makes_an_empty_directory() -> None:
    fake = MemoryAgents()
    fake.put_dir("a/b")
    assert fake.listing("a") == ["b"] and fake.listing("a/b") == [] and fake.read("a/b") is None


def test_an_entry_is_a_file_or_a_directory_not_both() -> None:
    fake = MemoryAgents()
    fake.put("a/b", "file")
    fake.put_dir("a/b/c")
    assert fake.read("a/b") is None and fake.listing("a/b") == ["c"]


def test_the_trees_have_paths_below_the_root_of_the_fake() -> None:
    fake = MemoryAgents()
    fake.put_dir(".retired/ceo-S")
    assert fake.trees()[0].path == fake.root / ".retired" / "ceo-S"


def test_the_archive_files_see_the_same_tree() -> None:
    fake = MemoryAgents()
    fake.put("t/runs/a.log", "x")
    files = MemoryArchiveFiles(fake)
    assert files.is_dir(fake.root / "t") and files.listdir(fake.root / "t") == ["runs"]
    assert files.read_text(fake.root / "t" / "runs" / "a.log") == "x"
    assert [(Path(p).relative_to(fake.root).as_posix(), d, f) for p, d, f in files.walk(fake.root / "t")] == [
        ("t", ["runs"], []),
        ("t/runs", [], ["a.log"]),
    ]


def test_the_archive_files_raise_what_the_disk_raises() -> None:
    fake = MemoryAgents()
    files = MemoryArchiveFiles(fake)
    with pytest.raises(FileNotFoundError):
        files.listdir(fake.root / "nowhere")
    with pytest.raises(FileNotFoundError):
        files.read_text(fake.root / "nowhere")
    assert list(files.walk(fake.root / "nowhere")) == [] and files.is_dir(fake.root / "nowhere") is False
