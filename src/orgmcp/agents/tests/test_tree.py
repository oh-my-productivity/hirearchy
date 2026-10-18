"""The helpers the directory implementations share: name rules, charter text, the two walks of the tree."""

from __future__ import annotations

import pytest

from orgmcp.agents._tree import parse_charter, valid_address, walk_agents, walk_subtree


@pytest.mark.parametrize("addr", ["ceo", "ceo/eng", "a", "a1-b2", "a" * 32, "ceo/eng/qa", "x/" * 3 + "y"])
def test_valid_addresses(addr: str) -> None:
    assert valid_address(addr) is True


@pytest.mark.parametrize(
    "addr",
    ["", "Ceo", "1a", "-a", "a_b", "a b", "a/", "/a", "a//b", "a" * 33, "a/b\n", "a\n/b", "ops\n", "work", "a/inbox", "runtime",
     "agent", "memory", "org", ".paused", ".retired", "a/.git", ".gitignore", "é", "a/é"],
)
def test_invalid_addresses(addr: str) -> None:
    assert valid_address(addr) is False


def test_root_is_not_an_address_of_an_agent_here() -> None:
    assert valid_address("root") is False  # the callers decide about root before they ask


def test_parse_charter_strips_the_body() -> None:
    assert parse_charter("---\nrole: R\n---\n\n  body  \n\n") == ({"role": "R"}, "body")


def test_parse_charter_without_frontmatter() -> None:
    assert parse_charter("  just text \n") == ({}, "just text")


def test_parse_charter_lets_a_broken_frontmatter_raise() -> None:
    with pytest.raises(Exception) as raised:
        parse_charter("---\nrole: [x\n---\nb\n")
    assert type(raised.value).__name__ in {"ParserError", "ScannerError"}


TREE = {"root": ["a", "b"], "a": ["a/x", "a/y"], "a/x": ["a/x/1"], "b": []}


def kids(addr: str) -> list[str]:
    return TREE.get(addr, [])


def test_walk_agents_is_a_depth_first_preorder_without_root() -> None:
    assert walk_agents(kids) == ["a", "a/x", "a/x/1", "a/y", "b"]


def test_walk_agents_of_nothing() -> None:
    assert walk_agents(lambda addr: []) == []


def test_walk_agents_asks_for_each_agent_once() -> None:
    asked: list[str] = []

    def spy(addr: str) -> list[str]:
        asked.append(addr)
        return kids(addr)

    walk_agents(spy)
    assert asked == ["root", "a", "a/x", "a/x/1", "a/y", "b"]


def test_walk_subtree_takes_the_last_child_first() -> None:
    assert walk_subtree("root", kids) == ["root", "b", "a", "a/y", "a/x", "a/x/1"]
    assert walk_subtree("a", kids) == ["a", "a/y", "a/x", "a/x/1"]


def test_walk_subtree_of_a_leaf_and_of_an_unknown_address() -> None:
    assert walk_subtree("b", kids) == ["b"]
    assert walk_subtree("nobody", kids) == ["nobody"]


def test_walk_subtree_normalizes_the_address() -> None:
    assert walk_subtree(" /a/ ", kids)[0] == "a"
