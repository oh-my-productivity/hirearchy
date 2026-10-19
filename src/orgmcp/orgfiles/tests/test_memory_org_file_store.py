"""``MemoryOrgFileStore``: what is only the fake's, and what keeps it trustworthy for the tests of its consumers.

It shares its tree with the in-memory agents (so they see the same files) and keeps what is outside the organization apart; it has no
symbolic links, no case-insensitivity and no permissions."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from orgmcp.agents.testing import MemoryAgents
from orgmcp.orgfiles.testing import MemoryOrgFileStore

pytestmark = pytest.mark.xfail(strict=True, reason="red: B-orgfiles")


def test_it_touches_no_file(tmp_path: Path) -> None:
    store = MemoryOrgFileStore()
    store.write_text(store.root / "a" / "b.md", "x")
    store.put(Path("/somewhere/else.md"), "y")
    assert list(tmp_path.iterdir()) == []


def test_the_agents_and_the_store_see_the_same_files() -> None:
    agents = MemoryAgents()
    store = MemoryOrgFileStore(agents)
    agents.put("ceo/AGENT.md", "---\nrole: R\n---\nbody\n")
    assert store.kind(agents.root / "ceo" / "AGENT.md") == "file" and store.kind(agents.root / "ceo") == "dir"
    assert store.read_text(agents.root / "ceo" / "AGENT.md") == "---\nrole: R\n---\nbody\n"
    store.write_text(agents.root / "ceo" / "work" / "n.md", "note")
    assert agents.read("ceo/work/n.md") == "note" and agents.listing("ceo/work") == ["n.md"]
    assert store.root == agents.root


def test_what_is_outside_the_organization_is_kept_apart() -> None:
    agents = MemoryAgents()
    store = MemoryOrgFileStore(agents)
    store.put(Path("/ws/w.md"), "w")
    assert store.read_text(Path("/ws/w.md")) == "w" and store.read(Path("/ws/w.md")) == "w"
    assert agents.files == {} and agents.dirs == {""}
    assert store.entries(Path("/ws")) == ["w.md"] and store.kind(Path("/ws")) == "dir"


def test_a_file_replaces_a_directory_of_the_same_name_and_the_other_way_round() -> None:
    store = MemoryOrgFileStore()
    store.put_dir(store.root / "x")
    store.put(store.root / "x", "now a file")
    assert store.kind(store.root / "x") == "file"
    store.put_dir(store.root / "x")
    assert store.kind(store.root / "x") == "dir"


def test_resolve_is_lexical_and_has_no_symbolic_links() -> None:
    store = MemoryOrgFileStore()
    assert store.resolve(Path("a/../b")) == store.root / "b"
    assert store.resolve(Path("/x/./y/../z")) == Path("/x/z")


def test_a_write_takes_the_time_of_the_clock_and_a_put_a_fixed_one() -> None:
    store = MemoryOrgFileStore()
    store.put(store.root / "p.md", "x")
    first = store.modified(store.root / "p.md")
    store.write_text(store.root / "w.md", "x")
    assert store.modified(store.root / "w.md") > first
    store.touch(store.root / "p.md", datetime(2030, 1, 1, tzinfo=timezone.utc))
    assert store.modified(store.root / "p.md") == datetime(2030, 1, 1, tzinfo=timezone.utc)


def test_read_is_none_for_what_is_not_a_file() -> None:
    store = MemoryOrgFileStore()
    store.put_dir(store.root / "d")
    assert store.read(store.root / "d") is None and store.read(store.root / "nope") is None


def test_a_directory_cannot_be_read_as_text_and_a_missing_path_is_not_found() -> None:
    store = MemoryOrgFileStore()
    store.put_dir(store.root / "d")
    with pytest.raises(IsADirectoryError):
        store.read_text(store.root / "d")
    with pytest.raises(FileNotFoundError):
        store.read_text(store.root / "nope")
