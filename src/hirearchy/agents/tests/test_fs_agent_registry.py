"""``FsAgentRegistry``: every write goes through the atomic writer, in an order that never shows half an agent."""

from __future__ import annotations

from pathlib import Path

import pytest

from hirearchy.agents import AgentRegistry
from hirearchy.agents._directory import FsAgentDirectory
from hirearchy.agents._registry import FsAgentRegistry
from hirearchy.kernel import AtomicWriter, OrgPaths
from hirearchy.kernel.testing import FailingAtomicWriter, MemoryAtomicWriter


class RecordingWriter(AtomicWriter):
    """Writes through to the disk and remembers what it was asked."""

    def __init__(self) -> None:
        self.calls: list[tuple[Path, str]] = []

    def write(self, path: Path, text: str) -> None:
        self.calls.append((path, text))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")


def test_it_is_an_agent_registry(tmp_path: Path) -> None:
    assert isinstance(FsAgentRegistry(OrgPaths(tmp_path), MemoryAtomicWriter()), AgentRegistry)


def test_building_it_writes_nothing(tmp_path: Path) -> None:
    writer = RecordingWriter()
    FsAgentRegistry(OrgPaths(tmp_path / "nowhere"), writer)
    assert writer.calls == [] and not (tmp_path / "nowhere").exists()


def test_create_makes_the_empty_memory_before_the_charter_is_written_through_the_writer(tmp_path: Path) -> None:
    seen: list[bool] = []

    class Spy(RecordingWriter):
        def write(self, path: Path, text: str) -> None:
            seen.append((path.parent / "MEMORY.md").read_text(encoding="utf-8") == "")
            super().write(path, text)

    writer = Spy()
    FsAgentRegistry(OrgPaths(tmp_path), writer).create("ceo", {"role": "R"}, "text")
    assert writer.calls == [(tmp_path / "ceo" / "AGENT.md", "---\nrole: R\n---\ntext\n")] and seen == [True]


def test_the_skeleton_is_made_by_the_registry_not_by_the_writer(tmp_path: Path) -> None:
    writer = MemoryAtomicWriter()
    FsAgentRegistry(OrgPaths(tmp_path), writer).create("ceo", {"role": "R"}, "x")
    assert sorted(p.name for p in (tmp_path / "ceo").iterdir()) == ["MEMORY.md", "inbox", "inflight", "read", "runs", "sent", "work"]
    assert set(writer.files) == {tmp_path / "ceo" / "AGENT.md"}


def test_a_failed_charter_write_leaves_a_directory_that_is_no_agent(tmp_path: Path) -> None:
    paths = OrgPaths(tmp_path)
    writer = FailingAtomicWriter(RecordingWriter(), fails=lambda path: path.name == "AGENT.md")
    with pytest.raises(OSError):
        FsAgentRegistry(paths, writer).create("ceo", {"role": "R"}, "x")
    assert (tmp_path / "ceo" / "MEMORY.md").read_text(encoding="utf-8") == ""
    assert FsAgentDirectory(paths).exists("ceo") is False and FsAgentDirectory(paths).agents() == []


def test_a_memory_that_cannot_be_made_stops_before_the_charter(tmp_path: Path) -> None:
    (tmp_path / "ceo" / "MEMORY.md").mkdir(parents=True)  # a directory where the file should go
    writer = RecordingWriter()
    with pytest.raises(OSError):
        FsAgentRegistry(OrgPaths(tmp_path), writer).create("ceo", {"role": "R"}, "x")
    assert writer.calls == [] and not (tmp_path / "ceo" / "AGENT.md").exists()


def test_creating_over_an_agent_empties_its_memory(tmp_path: Path) -> None:
    """What ``hire`` always did when it got that far; the callers refuse to hire over an existing agent."""
    (tmp_path / "ceo").mkdir()
    (tmp_path / "ceo" / "MEMORY.md").write_text("notes", encoding="utf-8")
    FsAgentRegistry(OrgPaths(tmp_path), RecordingWriter()).create("ceo", {"role": "R"}, "x")
    assert (tmp_path / "ceo" / "MEMORY.md").read_text(encoding="utf-8") == ""


def test_the_directories_of_an_existing_agent_directory_are_kept(tmp_path: Path) -> None:
    (tmp_path / "ceo" / "inbox").mkdir(parents=True)
    (tmp_path / "ceo" / "inbox" / "m.md").write_text("mail", encoding="utf-8")
    FsAgentRegistry(OrgPaths(tmp_path), RecordingWriter()).create("ceo", {"role": "R"}, "x")
    assert (tmp_path / "ceo" / "inbox" / "m.md").read_text(encoding="utf-8") == "mail"


def test_rewrite_charter_is_one_atomic_write_of_the_text_as_given(tmp_path: Path) -> None:
    writer = RecordingWriter()
    FsAgentRegistry(OrgPaths(tmp_path), writer).rewrite_charter(" /ceo/eng/ ", "any\ntext")
    assert writer.calls == [(tmp_path / "ceo" / "eng" / "AGENT.md", "any\ntext")]


def test_a_failed_rewrite_leaves_the_old_charter(tmp_path: Path) -> None:
    (tmp_path / "ceo").mkdir()
    (tmp_path / "ceo" / "AGENT.md").write_text("old", encoding="utf-8")
    writer = FailingAtomicWriter(RecordingWriter())
    with pytest.raises(OSError):
        FsAgentRegistry(OrgPaths(tmp_path), writer).rewrite_charter("ceo", "new")
    assert (tmp_path / "ceo" / "AGENT.md").read_text(encoding="utf-8") == "old"


def test_archive_writes_through_no_writer(tmp_path: Path) -> None:
    (tmp_path / "ceo").mkdir()
    (tmp_path / "ceo" / "AGENT.md").write_text("x", encoding="utf-8")
    writer = RecordingWriter()
    assert FsAgentRegistry(OrgPaths(tmp_path), writer).archive("ceo", "S") == "ceo-S"
    assert writer.calls == [] and (tmp_path / ".retired" / "ceo-S" / "AGENT.md").read_text(encoding="utf-8") == "x"


def test_archive_keeps_the_modification_times_of_what_it_moves(tmp_path: Path) -> None:
    import os

    (tmp_path / "ceo").mkdir()
    charter = tmp_path / "ceo" / "AGENT.md"
    charter.write_text("x", encoding="utf-8")
    os.utime(charter, ns=(1_700_000_000_000_000_000, 1_700_000_000_000_000_000))
    FsAgentRegistry(OrgPaths(tmp_path), RecordingWriter()).archive("ceo", "S")
    assert (tmp_path / ".retired" / "ceo-S" / "AGENT.md").stat().st_mtime_ns == 1_700_000_000_000_000_000
