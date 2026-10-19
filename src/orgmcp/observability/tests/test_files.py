"""``MailboxFiles`` and ``SchedulerPidFile``: the files the views look at by name, on disk and in memory (they must answer alike)."""

from __future__ import annotations

import os
from collections.abc import Callable
from pathlib import Path

import pytest

from orgmcp.agents.testing import MemoryAgents
from orgmcp.kernel import OrgPaths
from orgmcp.observability._files import FsMailboxFiles, FsSchedulerPidFile
from orgmcp.observability._ports import MailboxFiles, SchedulerPidFile
from orgmcp.observability.testing import MemoryMailboxFiles, MemorySchedulerPidFile


Put = Callable[[str, str], None]


def disk(tmp_path: Path) -> tuple[MailboxFiles, SchedulerPidFile, Put]:
    def put(rel: str, text: str) -> None:
        (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / rel).write_text(text)
        os.utime(tmp_path / rel, (1000.0, 1000.0))

    layout = OrgPaths(tmp_path)
    return FsMailboxFiles(layout), FsSchedulerPidFile(layout), put


def memory(tmp_path: Path) -> tuple[MailboxFiles, SchedulerPidFile, Put]:
    tree = MemoryAgents()
    return MemoryMailboxFiles(tree, 1000.0), MemorySchedulerPidFile(tree), tree.put


@pytest.fixture(params=[pytest.param(disk, id="disk"), pytest.param(memory, id="memory")])
def world(request: pytest.FixtureRequest, tmp_path: Path) -> tuple[MailboxFiles, SchedulerPidFile, Put, Path]:
    files, pid, put = request.param(tmp_path)
    root = tmp_path if request.param is disk else MemoryAgents().root
    return files, pid, put, root


def test_the_names_of_a_box_are_the_message_files_in_order(world: tuple[MailboxFiles, SchedulerPidFile, Put, Path]) -> None:
    files, _, put, _ = world
    for name in ("b.md", "a.md", ".hidden.md", "notes.txt", "c.md"):
        put(f"ceo/inbox/{name}", "x")
    put("inbox/r.md", "x")
    assert isinstance(files, MailboxFiles)
    assert files.names("ceo", "inbox") == ["a.md", "b.md", "c.md"] and files.names("root", "inbox") == ["r.md"]


def test_a_box_that_is_not_there_has_no_names(world: tuple[MailboxFiles, SchedulerPidFile, Put, Path]) -> None:
    files, _, put, _ = world
    put("ceo/inbox/a.md", "x")
    assert files.names("ceo", "inflight") == [] and files.names("nobody", "inbox") == []


def test_the_path_of_a_file_is_below_the_box_of_the_agent(world: tuple[MailboxFiles, SchedulerPidFile, Put, Path]) -> None:
    files, _, _, root = world
    assert files.path("ceo/eng", "inflight", "a.md") == root / "ceo" / "eng" / "inflight" / "a.md"
    assert files.path("root", "sent", "a.md") == root / "sent" / "a.md"


def test_the_time_of_a_file_is_when_it_was_written_and_a_file_that_is_not_there_has_none(world: tuple[MailboxFiles, SchedulerPidFile, Put, Path]) -> None:
    files, _, put, _ = world
    put("ceo/inbox/a.md", "x")
    assert files.mtime("ceo", "inbox", "a.md") == 1000.0 and files.mtime("ceo", "inbox", "b.md") is None


def test_there_is_a_pid_file_when_the_runtime_has_one(world: tuple[MailboxFiles, SchedulerPidFile, Put, Path]) -> None:
    _, pid, put, _ = world
    assert isinstance(pid, SchedulerPidFile) and pid.exists() is False
    put(".runtime/scheduler.pid", "123")
    assert pid.exists() is True
