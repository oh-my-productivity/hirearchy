"""``wire_agents``: the runtime has the four ports of ``agents`` built from the kernel's ports, and the dashboard's lenient variant."""

from __future__ import annotations

from pathlib import Path

import pytest

import orgmcp.core as core
from orgmcp.agents import AgentDirectory, AgentRegistry, CharterReader, RetiredArchive
from orgmcp.agents._caching import CachingAgentDirectory, DirectoryProbe, LenientCharterReader
from orgmcp.agents._charters import FsCharterReader
from orgmcp.agents._directory import FsAgentDirectory
from orgmcp.agents._registry import FsAgentRegistry
from orgmcp.agents._retired import FsRetiredArchive
from orgmcp.agents.testing import MemoryAgents
from orgmcp.app import Org, wire_agents, wiring
from orgmcp.dashboard_data import LenientOrg
from orgmcp.kernel import OrgLayout, OrgPaths


class FixedProbe(DirectoryProbe):
    """Every directory was last modified at this time (-1: there is none)."""

    def __init__(self, mtime: int) -> None:
        self._mtime = mtime

    def mtime(self, addr: str, name: str) -> int:
        return self._mtime


def test_the_runtime_has_the_real_agent_ports(tmp_path: Path) -> None:
    runtime = wiring.open_runtime(tmp_path)
    assert isinstance(runtime.agents, FsAgentDirectory) and isinstance(runtime.charters, FsCharterReader)
    assert isinstance(runtime.agent_registry, FsAgentRegistry) and isinstance(runtime.retired_archive, FsRetiredArchive)
    assert isinstance(runtime.agents, AgentDirectory) and isinstance(runtime.charters, CharterReader)
    assert isinstance(runtime.agent_registry, AgentRegistry) and isinstance(runtime.retired_archive, RetiredArchive)


def test_the_ports_look_at_the_runtime_root(tmp_path: Path) -> None:
    (tmp_path / "ceo").mkdir()
    (tmp_path / "ceo" / "AGENT.md").write_text("---\nrole: Boss\n---\nbody\n", encoding="utf-8")
    (tmp_path / "ceo" / "MEMORY.md").write_text("notes", encoding="utf-8")
    runtime = wiring.open_runtime(tmp_path)
    assert runtime.agents.agents() == ["ceo"]
    assert runtime.charters.charter("ceo") == ({"role": "Boss"}, "body") and runtime.charters.memory("ceo") == "notes"
    assert runtime.agent_registry.archive("ceo", "S") == "ceo-S"
    assert [t.name for t in runtime.retired_archive.trees()] == ["ceo-S"] and runtime.agents.agents() == []


def test_the_charter_is_written_through_the_atomic_writer_of_the_runtime(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    written: list[tuple[Path, str]] = []

    def record(path: Path, text: str) -> None:
        written.append((path, text))

    monkeypatch.setattr(core, "atomic_write", record)
    wiring.open_runtime(tmp_path).agent_registry.rewrite_charter("ceo", "text")
    assert written == [(tmp_path / "ceo" / "AGENT.md", "text")]


def test_an_override_replaces_one_agent_port_and_the_others_stay_files(tmp_path: Path) -> None:
    fake = MemoryAgents()
    fake.put("ceo/AGENT.md", "---\nrole: R\n---\n")
    runtime = wiring.open_runtime(tmp_path, {AgentDirectory: fake})
    assert runtime.agents is fake and runtime.agents.agents() == ["ceo"]
    assert isinstance(runtime.charters, FsCharterReader) and isinstance(runtime.agent_registry, FsAgentRegistry)


def test_one_fake_can_be_all_four_ports(tmp_path: Path) -> None:
    fake = MemoryAgents()
    runtime = wiring.open_runtime(tmp_path, {AgentDirectory: fake, CharterReader: fake, AgentRegistry: fake, RetiredArchive: fake})
    runtime.agent_registry.create("ceo", {"role": "R"}, "text")
    assert runtime.agents.agents() == ["ceo"] and runtime.charters.charter("ceo") == ({"role": "R"}, "text")
    assert list(tmp_path.iterdir()) == []


def test_opening_a_runtime_touches_nothing_of_the_agents(tmp_path: Path) -> None:
    runtime = wiring.open_runtime(tmp_path / "nowhere")
    assert runtime.agents.exists("root") and not (tmp_path / "nowhere").exists()


def test_two_runtimes_do_not_share_agent_objects(tmp_path: Path) -> None:
    one, two = wiring.open_runtime(tmp_path), wiring.open_runtime(tmp_path)
    assert one.agents is not two.agents and one.agent_registry is not two.agent_registry


def test_the_layout_the_ports_are_built_on_is_the_runtimes(tmp_path: Path) -> None:
    runtime = wiring.open_runtime(tmp_path, {OrgLayout: OrgPaths(tmp_path / "elsewhere")})
    (tmp_path / "elsewhere" / "cto").mkdir(parents=True)
    (tmp_path / "elsewhere" / "cto" / "AGENT.md").write_text("---\nrole: R\n---\n", encoding="utf-8")
    assert runtime.agents.agents() == ["cto"]


# ------------------------------------------------------------------------------ the dashboard's variant


def test_lenient_puts_the_decorators_on_the_read_ports_only(tmp_path: Path) -> None:
    runtime = wiring.open_runtime(tmp_path)
    problems: dict[str, str] = {}
    lenient = wire_agents.lenient(runtime, FixedProbe(-1), problems)
    assert isinstance(lenient.agents, CachingAgentDirectory) and isinstance(lenient.charters, LenientCharterReader)
    assert lenient.agent_registry is runtime.agent_registry and lenient.retired_archive is runtime.retired_archive
    assert lenient.root == runtime.root and lenient.clock is runtime.clock
    assert lenient.agents.children("anyone") == []  # the probe says there is no such directory


def test_the_lenient_org_is_built_on_the_decorators_and_reports_charters_it_cannot_read(tmp_path: Path) -> None:
    org = Org.init(tmp_path / "org", "mission")
    org.hire("root", "ceo", "Boss", "text")
    lenient = LenientOrg(org.root)
    assert isinstance(lenient.runtime.agents, CachingAgentDirectory) and isinstance(lenient.runtime.charters, LenientCharterReader)
    assert lenient.charter("ceo")[0]["role"] == "Boss" and lenient.bad == {}
    (org.root / "ceo" / "AGENT.md").write_text("---\nrole: [oops\n---\n", encoding="utf-8")
    assert lenient.charter("ceo") == ({"role": "?"}, "") and lenient.bad == {"ceo/AGENT.md": "ParserError"}


def test_the_lenient_org_lists_children_from_its_per_tick_directory_times(tmp_path: Path) -> None:
    org = Org.init(tmp_path / "org", "mission")
    org.hire("root", "ceo", "Boss", "text")
    lenient = LenientOrg(org.root)
    asked: list[tuple[str, str]] = []
    real = lenient.mtime

    def spy(addr: str, name: str) -> int:
        asked.append((addr, name))
        return real(addr, name)

    lenient.mtime = spy  # type: ignore[method-assign]
    assert lenient.children("root") == ["ceo"] and lenient.agents() == ["ceo"] and lenient.subtree("ceo") == ["ceo"]
    assert ("root", "") in asked and ("ceo", "") in asked


def test_what_the_probe_says_is_quiet_is_listed_once(tmp_path: Path) -> None:
    (tmp_path / "ceo").mkdir()
    (tmp_path / "ceo" / "AGENT.md").write_text("---\nrole: R\n---\n", encoding="utf-8")
    lenient = wire_agents.lenient(wiring.open_runtime(tmp_path), FixedProbe(1), {})  # modified at the epoch: long quiet
    assert lenient.agents.children("root") == ["ceo"]
    (tmp_path / "cto").mkdir()
    (tmp_path / "cto" / "AGENT.md").write_text("---\nrole: R\n---\n", encoding="utf-8")
    assert lenient.agents.children("root") == ["ceo"]  # trusted: the probe still says nothing changed
