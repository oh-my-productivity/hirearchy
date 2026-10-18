"""``wire_settings`` and ``wire_locator``: the runtime has the settings ports, built from the kernel's ports."""

from __future__ import annotations

from pathlib import Path

import pytest

import orgmcp.core as core
from orgmcp.app import wiring
from orgmcp.kernel import AtomicWriter, Environment
from orgmcp.kernel.testing import DictEnvironment
from orgmcp.locator import OrgLocator
from orgmcp.settings import EventSwitch, OrgDocumentStore, OrgSettings
from orgmcp.settings.testing import MemoryOrgSettings


def test_the_runtime_has_the_settings_ports(tmp_path: Path) -> None:
    runtime = wiring.open_runtime(tmp_path)
    assert isinstance(runtime.settings, OrgSettings) and isinstance(runtime.documents, OrgDocumentStore)
    assert isinstance(runtime.event_switch, EventSwitch) and isinstance(runtime.locator, OrgLocator)


def test_the_settings_are_the_files_of_the_runtime_root(tmp_path: Path) -> None:
    (tmp_path / "ORG.md").write_text("---\nmax_depth: 6\n---\nthe rules\n", encoding="utf-8")
    runtime = wiring.open_runtime(tmp_path)
    assert runtime.settings.config()["max_depth"] == 6 and runtime.settings.rules() == "the rules"
    assert runtime.documents.exists() and runtime.documents.read_raw().endswith("the rules\n")
    assert runtime.event_switch.enabled() is True
    (tmp_path / "ORG.md").write_text("---\nevents: false\n---\nthe rules\n", encoding="utf-8")
    assert runtime.event_switch.enabled() is False


def test_the_document_is_written_through_the_atomic_writer_of_the_runtime(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    written: list[tuple[Path, str]] = []
    monkeypatch.setattr(core, "atomic_write", lambda path, text: written.append((path, text)))
    wiring.open_runtime(tmp_path).documents.write_raw("text\n")
    assert written == [(tmp_path / "ORG.md", "text\n")]


def test_an_override_replaces_the_settings_port(tmp_path: Path) -> None:
    fake = MemoryOrgSettings("---\nmax_depth: 8\n---\nbody\n")
    runtime = wiring.open_runtime(tmp_path, {OrgSettings: fake})
    assert runtime.settings is fake
    assert runtime.documents is not fake  # another port, still the file


def test_the_locator_works_on_the_environment_port(tmp_path: Path) -> None:
    (tmp_path / "ORG.md").write_text("x", encoding="utf-8")
    below = tmp_path / "ceo" / "work"
    below.mkdir(parents=True)
    runtime = wiring.open_runtime(tmp_path, {Environment: DictEnvironment(cwd=below)})
    assert runtime.locator.find_root() == tmp_path.resolve()


def test_building_the_settings_ports_does_not_create_org_md(tmp_path: Path) -> None:
    runtime = wiring.open_runtime(tmp_path)
    assert runtime.documents.exists() is False and runtime.event_switch.enabled() is False
    assert list(tmp_path.iterdir()) == []


def test_the_atomic_writer_port_is_still_there(tmp_path: Path) -> None:
    assert isinstance(wiring.open_runtime(tmp_path).atomic_writer, AtomicWriter)
