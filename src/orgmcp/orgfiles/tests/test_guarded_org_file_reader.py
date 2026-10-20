"""``GuardedOrgFileReader``: which collaborator it asks for what, with recording fakes.

What it shows and refuses is the contract (``test_contract_org_file_reader.py``); this pins the seams: the scopes are asked only for a path
outside the organization and never for root, the agent directory only when a reader is named, and the text is read leniently."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

import pytest

from orgmcp.access import AccessScopes
from orgmcp.agents.testing import MemoryAgents
from orgmcp.kernel import OrgError, OrgPaths
from orgmcp.orgfiles._reader import GuardedOrgFileReader
from orgmcp.orgfiles.testing import MemoryOrgFileStore


class RecordingScopes(AccessScopes):
    def __init__(self, roots: list[Path]) -> None:
        self.roots = roots
        self.asked: list[str] = []

    def workspace_of(self, addr: str) -> Path | None:
        raise AssertionError("the reader never asks for a workspace")

    def inputs_of(self, addr: str) -> list[Path]:
        raise AssertionError("the reader never asks for inputs")

    def readable_roots(self, addr: str) -> list[Path]:
        self.asked.append(addr)
        return self.roots

    def unconfined_read(self, meta: Mapping[str, object]) -> bool:
        raise AssertionError("the reader never asks whether a charter is legacy")


class RecordingStore(MemoryOrgFileStore):
    def __init__(self, agents: MemoryAgents) -> None:
        super().__init__(agents)
        self.errors: list[str] = []

    def read_text(self, path: Path, errors: str = "strict") -> str:
        self.errors.append(errors)
        return super().read_text(path, errors)


def reader(roots: list[Path] | None = None) -> tuple[GuardedOrgFileReader, RecordingScopes, RecordingStore]:
    agents = MemoryAgents()
    agents.create("lead", {"role": "Lead"}, "body")
    store = RecordingStore(agents)
    scopes = RecordingScopes(roots or [])
    return GuardedOrgFileReader(OrgPaths(store.root), store, agents, scopes), scopes, store


def test_a_path_inside_the_organization_asks_the_scopes_nothing() -> None:
    r, scopes, store = reader()
    store.put(store.root / "lead" / "work" / "n.md", "a b")
    assert r.read("lead/work/n.md", "lead").startswith("[lead/work/n.md: 2 words")
    assert r.read("lead/work", "lead") == "n.md" and scopes.asked == []


def test_a_path_outside_asks_for_the_readable_roots_of_the_canonical_actor_and_root_is_never_asked() -> None:
    r, scopes, store = reader([Path("/ws/lead")])
    store.put(Path("/ws/lead/p.md"), "x")
    assert r.resolve_read("/ws/lead/p.md", " /lead/ ") == Path("/ws/lead/p.md") and scopes.asked == ["lead"]
    for actor in (None, "", "root", " /root/"):
        with pytest.raises(OrgError, match="^you can only read inside the organization$"):
            r.resolve_read("/ws/lead/p.md", actor)
    assert scopes.asked == ["lead"]


def test_resolve_read_does_not_ask_whether_the_actor_exists_and_read_does() -> None:
    r, _, _ = reader()
    assert r.resolve_read("lead", "ghost") == r.resolve_read("lead")
    with pytest.raises(OrgError, match="^no such agent: ghost$"):
        r.read("lead", "ghost")
    assert r.read("", "") == "lead/"  # an empty actor is no actor: nobody is asked for


def test_the_text_is_read_leniently_and_the_directory_listing_reads_no_file() -> None:
    r, _, store = reader()
    store.put(store.root / "lead" / "work" / "n.md", "x")
    r.read("lead/work/n.md")
    r.read("lead/work")
    assert store.errors == ["replace"]
