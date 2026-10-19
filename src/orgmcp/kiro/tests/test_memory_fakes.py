"""The in-memory fakes keep what a consumer relies on beyond the contract suites."""

from __future__ import annotations

import json

from orgmcp.kiro import McpServerLocator, ProfileStore
from orgmcp.kiro.testing import CountingProfileStore, MemoryProfileStore, StaticMcpServerLocator


def test_the_fakes_are_the_ports() -> None:
    assert isinstance(MemoryProfileStore(), ProfileStore) and isinstance(StaticMcpServerLocator(), McpServerLocator)
    assert isinstance(CountingProfileStore(MemoryProfileStore()), ProfileStore)


def test_the_memory_store_keeps_the_text_a_file_would_have() -> None:
    store = MemoryProfileStore()
    store.write("p", {"b": 1, "a": [1]})
    assert store.files["p"] == json.dumps({"b": 1, "a": [1]}, indent=2) + "\n"


def test_the_counting_store_counts_writes_and_passes_reads_through() -> None:
    inner = MemoryProfileStore()
    counting = CountingProfileStore(inner)
    counting.write("p", {"a": 1})
    counting.write("p", {"a": 2})
    assert counting.writes == ["p", "p"] and counting.read("p") == {"a": 2} and inner.read("p") == {"a": 2}


def test_the_static_locator_answers_what_it_was_given() -> None:
    assert StaticMcpServerLocator({"command": "x", "args": ["y", "mcp"]}).command() == {"command": "x", "args": ["y", "mcp"]}
    assert StaticMcpServerLocator().command() == {"command": "/venv/bin/orgmcp", "args": ["mcp"]}


def test_the_static_locator_does_not_share_its_lists_with_its_callers() -> None:
    given = {"command": "x", "args": ["mcp"]}
    locator = StaticMcpServerLocator(given)
    given["args"].append("changed")  # type: ignore[attr-defined]
    assert locator.command()["args"] == ["mcp"]
