"""``wire_strays``: the runtime has the two stray ports, built from the access, charters and ledgers of the runtime."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

import pytest

from orgmcp.access import AccessScopes, ToolNaming
from orgmcp.app import wiring
from orgmcp.kernel import LedgerStore
from orgmcp.kernel.testing import MemoryLedgerStore
from orgmcp.strays import StrayProbe, StrayRegistry
from orgmcp.strays._probe import WorkspaceStrayProbe
from orgmcp.strays._registry import LedgerStrayRegistry

class FixedProbe(StrayProbe):
    def probe(self, addr: str) -> dict[str, float]:
        return {"/fixed": 1.0}

    def found_since(self, before: Mapping[str, float], after: Mapping[str, float]) -> list[str]:
        return []


class Names(ToolNaming):
    def tool_names(self, addr: str) -> dict[str, str]:
        return {"read": "r!", "write": "w!"}


def hire(root: Path, tools: str, workspace: Path) -> None:
    (root / "dev").mkdir(parents=True)
    (root / "dev" / "AGENT.md").write_text(f"---\nrole: Dev\ntools: [{tools}]\nworkspace: {workspace}\n---\n# Role: Dev\n\nCode.\n", encoding="utf-8")


def test_the_runtime_has_the_stray_ports(tmp_path: Path) -> None:
    runtime = wiring.open_runtime(tmp_path)
    assert isinstance(runtime.stray_probe, WorkspaceStrayProbe) and isinstance(runtime.stray_probe, StrayProbe)
    assert isinstance(runtime.stray_registry, LedgerStrayRegistry) and isinstance(runtime.stray_registry, StrayRegistry)


def test_building_the_stray_ports_does_no_io(tmp_path: Path) -> None:
    runtime = wiring.open_runtime(tmp_path)
    assert runtime.stray_registry.take_notice("dev") == ""
    assert list(tmp_path.iterdir()) == []


def test_the_probe_reads_the_charters_and_the_workspace_of_the_runtime(tmp_path: Path) -> None:
    ws = (tmp_path / "ws").resolve()
    (ws / "dev").mkdir(parents=True)
    hire(tmp_path / "org", "write", ws)
    runtime = wiring.open_runtime(tmp_path / "org")
    assert list(runtime.stray_probe.probe("dev")) == [str(ws / "dev")]
    hire(tmp_path / "org2", "read", ws)
    assert wiring.open_runtime(tmp_path / "org2").stray_probe.probe("dev") == {}


def test_the_registry_writes_the_strays_ledger_of_the_organization(tmp_path: Path) -> None:
    org = tmp_path / "org"
    hire(org, "write", tmp_path / "ws")
    runtime = wiring.open_runtime(org)
    runtime.stray_registry.record("dev", ["/a"])
    assert (org / ".runtime" / "strays.json").read_text(encoding="utf-8") == '{\n  "dev": {\n    "paths": [\n      "/a"\n    ],\n    "told": false\n  }\n}\n'
    assert "`@orgmcp/org_write`" in runtime.stray_registry.take_notice("dev")


def test_an_override_replaces_the_port(tmp_path: Path) -> None:
    fake = FixedProbe()
    runtime = wiring.open_runtime(tmp_path, {StrayProbe: fake})
    assert runtime.stray_probe is fake and isinstance(runtime.stray_registry, LedgerStrayRegistry)


def test_the_registry_uses_the_ledger_and_the_naming_of_the_runtime(tmp_path: Path) -> None:
    ledgers = MemoryLedgerStore()
    runtime = wiring.open_runtime(tmp_path, {LedgerStore: ledgers, ToolNaming: Names()})
    runtime.stray_registry.record("dev", ["/a"])
    assert "dev" in ledgers.texts["strays"] and "`@orgmcp/w!`" in runtime.stray_registry.take_notice("dev")


def test_the_probe_uses_the_access_scopes_of_the_runtime(tmp_path: Path) -> None:
    class Elsewhere(AccessScopes):
        def workspace_of(self, addr: str) -> Path | None:
            return tmp_path / "elsewhere"

        def inputs_of(self, addr: str) -> list[Path]:
            return []

        def readable_roots(self, addr: str) -> list[Path]:
            return []

        def unconfined_read(self, meta: Mapping[str, object]) -> bool:
            return False

    hire(tmp_path / "org", "write", tmp_path / "ws")
    (tmp_path / "elsewhere" / "dev").mkdir(parents=True)
    runtime = wiring.open_runtime(tmp_path / "org", {AccessScopes: Elsewhere()})
    assert list(runtime.stray_probe.probe("dev")) == [str(tmp_path / "elsewhere" / "dev")]


def test_every_runtime_has_its_own_stray_ports(tmp_path: Path) -> None:
    first, second = wiring.open_runtime(tmp_path), wiring.open_runtime(tmp_path)
    assert first.stray_probe is not second.stray_probe and first.stray_registry is not second.stray_registry
