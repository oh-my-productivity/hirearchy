"""``ArchiveFiles``: the operating system's file tree and the in-memory one answer the same questions the same way."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import pytest

from hirearchy.agents._retired import ArchiveFiles, OsArchiveFiles
from hirearchy.agents.testing import MemoryAgents, MemoryArchiveFiles


@dataclass(frozen=True)
class World:
    files: ArchiveFiles
    root: Path
    put: Callable[[str, str], None]
    put_dir: Callable[[str], None]


def on_disk(tmp_path: Path) -> World:
    def put(path: str, text: str) -> None:
        (tmp_path / path).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / path).write_text(text, encoding="utf-8")

    return World(OsArchiveFiles(), tmp_path, put, lambda path: (tmp_path / path).mkdir(parents=True, exist_ok=True))


def in_memory(tmp_path: Path) -> World:
    fake = MemoryAgents()
    return World(MemoryArchiveFiles(fake), fake.root, fake.put, fake.put_dir)


@pytest.fixture(params=[on_disk, in_memory], ids=lambda factory: factory.__name__)
def w(request: pytest.FixtureRequest, tmp_path: Path) -> World:
    world: World = request.param(tmp_path)
    assert isinstance(world.files, ArchiveFiles)
    world.put("t/a.md", "one")
    world.put("t/runs/1.log", "x")
    world.put("t/runs/2.log", "y")
    world.put("t/eng/AGENT.md", "z")
    world.put_dir("t/eng/inbox")
    return world


def walk(w: World, top: str) -> dict[str, tuple[list[str], list[str]]]:
    return {Path(here).relative_to(w.root).as_posix(): (sorted(d), sorted(f)) for here, d, f in w.files.walk(w.root / top)}


def test_walk_lists_every_directory_with_its_subdirectories_and_files(w: World) -> None:
    assert walk(w, "t") == {
        "t": (["eng", "runs"], ["a.md"]),
        "t/eng": (["inbox"], ["AGENT.md"]),
        "t/eng/inbox": ([], []),
        "t/runs": ([], ["1.log", "2.log"]),
    }


def test_walk_does_not_enter_a_directory_the_caller_removed_from_the_list(w: World) -> None:
    seen = []
    for here, dirs, _ in w.files.walk(w.root / "t"):
        seen.append(Path(here).relative_to(w.root).as_posix())
        dirs[:] = [d for d in dirs if d != "eng"]
    assert sorted(seen) == ["t", "t/runs"]


def test_walk_of_a_file_or_of_nothing_is_empty(w: World) -> None:
    assert walk(w, "t/a.md") == {} and walk(w, "nowhere") == {}


def test_listdir_names_files_and_directories(w: World) -> None:
    assert sorted(w.files.listdir(w.root / "t")) == ["a.md", "eng", "runs"]
    assert w.files.listdir(w.root / "t/eng/inbox") == []


@pytest.mark.parametrize("path", ["nowhere", "t/a.md"])
def test_listdir_of_what_is_not_a_directory_is_an_os_error(w: World, path: str) -> None:
    with pytest.raises(OSError):
        w.files.listdir(w.root / path)


def test_is_dir(w: World) -> None:
    assert [w.files.is_dir(w.root / p) for p in ("t", "t/runs", "t/a.md", "nowhere")] == [True, True, False, False]


def test_read_text(w: World) -> None:
    assert w.files.read_text(w.root / "t/a.md") == "one"


@pytest.mark.parametrize("path", ["nowhere", "t", "t/runs"])
def test_read_text_of_what_is_not_a_file_is_an_os_error(w: World, path: str) -> None:
    with pytest.raises(OSError):
        w.files.read_text(w.root / path)
