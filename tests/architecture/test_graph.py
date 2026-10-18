"""graph.py and ownership.py are the machine-readable forms of ARCHITECTURE.md; these tests keep them equal to the document.

If one of them fails, the document (2.2, 2.3, 4.1, 4.3) and the data disagree: decide which is right, then change that one on
purpose (ARCHITECTURE.md is edited only by the manager).
"""

from __future__ import annotations

import pytest

from . import document, graph, ownership

pytestmark = [pytest.mark.architecture, pytest.mark.xfail(strict=True, reason="red: M0")]


def test_there_are_42_packages():
    assert len(graph.ALL_PACKAGES) == 42
    assert graph.ALL_PACKAGES[0] == "kernel" and graph.ALL_PACKAGES[-1] == "app"
    assert len(graph.FEATURES) == 36 and graph.ENTRY_POINTS == ("scheduler", "mcp_server", "cli", "dashboard")


def test_graph_matches_the_package_map(architecture_text):
    rows = document.package_rows(architecture_text)
    assert [r.name for r in rows] == list(graph.ALL_PACKAGES)
    for row in rows:
        if row.name == graph.APP:
            continue
        package = graph.PACKAGES[row.name]
        assert (package.kind, package.deps) == (row.kind, row.deps), row.name


def test_graph_edges_are_the_205_edges_of_4_3(architecture_text):
    in_document = document.edge_rows(architecture_text)
    assert graph.edges() == in_document
    assert len(in_document) == 205


def test_levels_are_the_levels_of_4_1(architecture_text):
    expected = document.level_rows(architecture_text)
    assert {f"L{n}": names for n, names in graph.feature_levels().items()} == {k: v for k, v in expected.items() if k.startswith("L")}
    assert set(expected["E"]) == set(graph.ENTRY_POINTS)


def test_the_graph_is_acyclic_and_every_package_reaches_the_kernel():
    assert len(graph.PACKAGES) == 41  # kernel + 36 features + 4 entry points (app is the 42nd and is not in the graph)
    for name, package in graph.PACKAGES.items():
        assert name == graph.KERNEL or graph.KERNEL in package.deps, name
        for dep in package.deps:
            assert dep == graph.KERNEL or graph.level(dep) < graph.level(name), (name, dep)  # also terminates only if acyclic


def test_ownership_matches_the_table_of_2_3(architecture_text):
    rows = document.ownership_rows(architecture_text)
    ours = {(o.path, o.owner) for o in ownership.OWNERS}
    for path, owner in rows:
        if path.startswith("workspace directories"):
            assert owner == "blueprint"  # no literal fragment: the paths come from the blueprint
            continue
        assert (path, owner) in ours, f"2.3 row {path!r} (owner {owner}) is missing in ownership.OWNERS"
    assert len(ownership.OWNERS) == len(rows) - 1
    assert all(o.owner in graph.PACKAGES for o in ownership.OWNERS)


def test_the_ledger_registry_matches_2_3(architecture_text):
    assert document.ledger_registry(architecture_text) == ownership.LEDGERS
