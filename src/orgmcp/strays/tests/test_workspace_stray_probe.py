"""``WorkspaceStrayProbe``: what it asks of its three collaborators, apart from the contract (``test_contract_stray_probe``)."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

import pytest

from orgmcp.access import AccessScopes
from orgmcp.agents import CharterReader
from orgmcp.kernel import JsonObject
from orgmcp.strays import StrayProbe
from orgmcp.strays._ports import MtimeReader
from orgmcp.strays._probe import WorkspaceStrayProbe


class Scopes(AccessScopes):
    """Gives each agent the workspace it is told, and remembers whom it was asked about."""

    def __init__(self, workspaces: dict[str, Path | None]) -> None:
        self.workspaces = workspaces
        self.asked: list[str] = []

    def workspace_of(self, addr: str) -> Path | None:
        self.asked.append(addr)
        return self.workspaces.get(addr)

    def inputs_of(self, addr: str) -> list[Path]:
        raise AssertionError("the probe has no business with the inputs")

    def readable_roots(self, addr: str) -> list[Path]:
        raise AssertionError("the probe has no business with the readable roots")

    def unconfined_read(self, meta: Mapping[str, object]) -> bool:
        raise AssertionError("the probe has no business with the read rules")


class Charters(CharterReader):
    def __init__(self, charters: dict[str, JsonObject]) -> None:
        self.charters = charters

    def charter(self, addr: str) -> tuple[JsonObject, str]:
        if addr not in self.charters:
            raise FileNotFoundError(addr)
        return self.charters[addr], "body"

    def memory(self, addr: str) -> str:
        raise AssertionError("the probe does not read memories")


class Mtimes(MtimeReader):
    """Knows some paths, and remembers which it was asked about."""

    def __init__(self, times: dict[Path, float]) -> None:
        self.times = times
        self.asked: list[Path] = []

    def mtime(self, path: Path) -> float | None:
        self.asked.append(path)
        return self.times.get(path)


WS = Path("/the/ws")


def probe_of(tools: object, workspace: Path | None, times: dict[Path, float]) -> tuple[WorkspaceStrayProbe, Scopes, Mtimes]:
    scopes, mtimes = Scopes({"lead/an": workspace}), Mtimes(times)
    charter: JsonObject = {"role": "R", "tools": tools}
    return WorkspaceStrayProbe(scopes, Charters({"lead/an": charter}), mtimes), scopes, mtimes


def test_it_is_a_stray_probe() -> None:
    probe, _, _ = probe_of(["write"], WS, {})
    assert isinstance(probe, StrayProbe)


def test_it_asks_for_the_tree_of_the_address_and_then_its_memory_file() -> None:
    tree = WS / "lead" / "an"
    probe, scopes, mtimes = probe_of(["read", "write"], WS, {tree: 3.0, tree / "MEMORY.md": 4.0})
    assert probe.probe("lead/an") == {str(tree): 3.0, str(tree / "MEMORY.md"): 4.0}
    assert scopes.asked == ["lead/an"] and mtimes.asked == [tree, tree / "MEMORY.md"]


def test_a_path_that_cannot_be_statted_is_left_out() -> None:
    tree = WS / "lead" / "an"
    probe, _, _ = probe_of(["write"], WS, {tree / "MEMORY.md": 4.0})
    assert probe.probe("lead/an") == {str(tree / "MEMORY.md"): 4.0}


@pytest.mark.parametrize("tools", [None, [], ["read"], ["Write"]])
def test_without_the_built_in_write_no_file_is_looked_at(tools: object) -> None:
    probe, _, mtimes = probe_of(tools, WS, {WS / "lead" / "an": 3.0})
    assert probe.probe("lead/an") == {} and mtimes.asked == []


def test_without_a_workspace_no_file_is_looked_at() -> None:
    probe, _, mtimes = probe_of(["write"], None, {})
    assert probe.probe("lead/an") == {} and mtimes.asked == []


def test_an_agent_the_charters_do_not_know_is_an_error() -> None:
    probe, _, _ = probe_of(["write"], WS, {})
    with pytest.raises(FileNotFoundError):
        probe.probe("ghost")


def test_a_file_whose_name_only_ends_in_memory_md_counts_as_a_memory_file() -> None:
    probe, _, _ = probe_of(["write"], WS, {})
    old, new = str(WS / "OLD_MEMORY.md"), str(WS / "NEW_MEMORY.md")
    assert probe.found_since({old: 1.0}, {old: 2.0, new: 2.0}) == [old, new]
    assert probe.found_since({old: 1.0}, {old: 1.0}) == []
