"""Contract of ``StrayProbe``: over workspaces on disk and over the in-memory table the same files are found."""

from __future__ import annotations

from pathlib import Path

import pytest

from orgmcp.strays import StrayProbe
from orgmcp.strays.testing import IMPLEMENTATIONS, StraysHarness

from ._support import make, writer


@pytest.fixture(params=IMPLEMENTATIONS[StrayProbe], ids=lambda factory: factory.__name__)
def h(request: pytest.FixtureRequest, tmp_path: Path) -> StraysHarness:
    made = make(request, tmp_path)
    assert isinstance(made.probe, StrayProbe)
    return made


# ------------------------------------------------------------------------------ probe


def test_an_agent_with_the_built_in_write_and_a_workspace_with_nothing_in_it_has_no_strays(h: StraysHarness) -> None:
    writer(h, "dev")
    assert h.probe.probe("dev") == {}


def test_the_tree_of_the_address_is_probed_with_its_mtime(h: StraysHarness) -> None:
    ws = writer(h, "dev")
    h.touch_dir(ws / "dev", 1000.0)
    assert h.probe.probe("dev") == {str(ws / "dev"): 1000.0}


def test_the_memory_file_of_the_address_is_probed_too(h: StraysHarness) -> None:
    ws = writer(h, "dev")
    h.touch(ws / "dev" / "MEMORY.md", 2000.0)
    h.touch_dir(ws / "dev", 1000.0)  # after the file: making a file changes the mtime of its directory
    assert h.probe.probe("dev") == {str(ws / "dev"): 1000.0, str(ws / "dev" / "MEMORY.md"): 2000.0}


def test_the_tree_comes_before_the_memory_file(h: StraysHarness) -> None:
    ws = writer(h, "dev")
    h.touch(ws / "dev" / "MEMORY.md", 2000.0)
    h.touch_dir(ws / "dev", 1000.0)
    assert list(h.probe.probe("dev")) == [str(ws / "dev"), str(ws / "dev" / "MEMORY.md")]


def test_a_nested_address_lands_in_a_nested_tree(h: StraysHarness) -> None:
    ws = writer(h, "lead/an")
    h.touch(ws / "lead" / "an" / "work" / "x.md", 1000.0)
    h.touch_dir(ws / "lead" / "an", 1500.0)
    assert h.probe.probe("lead/an") == {str(ws / "lead" / "an"): 1500.0}


def test_only_the_tree_and_the_memory_of_the_address_are_looked_at(h: StraysHarness) -> None:
    ws = writer(h, "dev")
    h.touch(ws / "report.md", 1000.0)  # a real deliverable of the workspace
    h.touch(ws / "MEMORY.md", 1000.0)  # not <workspace>/<address>/MEMORY.md
    h.touch(ws / "other" / "MEMORY.md", 1000.0)  # the tree of another address
    assert h.probe.probe("dev") == {}


@pytest.mark.parametrize("tools", [[], ["read"], ["read", "shell", "web"]])
def test_an_agent_without_the_built_in_write_has_nothing_to_probe(h: StraysHarness, tools: list[str]) -> None:
    ws = writer(h, "dev", tools)
    h.touch(ws / "dev" / "MEMORY.md", 1000.0)  # it cannot have written there itself
    assert h.probe.probe("dev") == {}


@pytest.mark.parametrize("meta", [{"role": "R"}, {"role": "R", "tools": None}, {"role": "R", "tools": []}])
def test_an_agent_with_no_tools_in_its_charter_has_nothing_to_probe(h: StraysHarness, meta: dict[str, object]) -> None:
    ws = h.workspace / "dev"
    h.put_agent("dev", {**meta, "workspace": str(ws)})
    h.touch(ws / "dev" / "MEMORY.md", 1000.0)
    assert h.probe.probe("dev") == {}


@pytest.mark.parametrize("workspace", [None, ""])
def test_an_agent_without_a_workspace_has_nothing_to_probe(h: StraysHarness, workspace: str | None) -> None:
    h.put_agent("dev", {"role": "R", "tools": ["write"], "workspace": workspace})
    assert h.probe.probe("dev") == {}


def test_root_has_nothing_to_probe(h: StraysHarness) -> None:
    assert h.probe.probe("root") == {}


def test_an_agent_that_does_not_exist_is_an_error(h: StraysHarness) -> None:
    with pytest.raises(FileNotFoundError):
        h.probe.probe("ghost")


def test_probing_changes_nothing(h: StraysHarness) -> None:
    ws = writer(h, "dev")
    h.touch(ws / "dev" / "MEMORY.md", 1000.0)
    first = h.probe.probe("dev")
    assert h.probe.probe("dev") == first
    assert h.ledger_text() is None


# ------------------------------------------------------------------------------ found_since


def paths(h: StraysHarness) -> tuple[str, str]:
    tree = h.workspace / "dev"
    return str(tree), str(tree / "MEMORY.md")


def test_nothing_new_is_nothing_found(h: StraysHarness) -> None:
    tree, memory = paths(h)
    assert h.probe.found_since({}, {}) == []
    assert h.probe.found_since({tree: 1.0, memory: 2.0}, {tree: 1.0, memory: 2.0}) == []


def test_a_new_tree_is_found(h: StraysHarness) -> None:
    tree, _ = paths(h)
    assert h.probe.found_since({}, {tree: 5.0}) == [tree]


def test_a_tree_that_was_there_before_the_run_is_not_ours_to_flag(h: StraysHarness) -> None:
    tree, _ = paths(h)
    assert h.probe.found_since({tree: 1.0}, {tree: 1.0}) == []
    assert h.probe.found_since({tree: 1.0}, {tree: 9.0}) == []  # a directory that changed is not a new directory


def test_a_new_memory_file_in_a_tree_that_was_there_is_found(h: StraysHarness) -> None:
    tree, memory = paths(h)
    assert h.probe.found_since({tree: 1.0}, {tree: 5.0, memory: 5.0}) == [memory]


def test_a_memory_file_written_during_the_run_is_found(h: StraysHarness) -> None:
    tree, memory = paths(h)
    assert h.probe.found_since({tree: 1.0, memory: 2.0}, {tree: 1.0, memory: 3.0}) == [memory]


@pytest.mark.parametrize("after", [2.0, 1.0])
def test_a_memory_file_that_was_not_written_during_the_run_is_not_found(h: StraysHarness, after: float) -> None:
    tree, memory = paths(h)
    assert h.probe.found_since({tree: 1.0, memory: 2.0}, {tree: 1.0, memory: after}) == []


def test_the_tree_says_it_all(h: StraysHarness) -> None:
    tree, memory = paths(h)
    assert h.probe.found_since({}, {tree: 5.0, memory: 5.0}) == [tree]


def test_the_memory_file_of_another_tree_stays(h: StraysHarness) -> None:
    tree, memory = paths(h)
    other = str(h.workspace / "other" / "MEMORY.md")
    assert h.probe.found_since({}, {tree: 5.0, other: 5.0}) == [tree, other]


def test_what_is_found_keeps_the_order_of_the_probe(h: StraysHarness) -> None:
    a, b = str(h.workspace / "a"), str(h.workspace / "b")
    assert h.probe.found_since({}, {b: 1.0, a: 1.0}) == [b, a]
    assert h.probe.found_since({}, {a: 1.0, b: 1.0}) == [a, b]
