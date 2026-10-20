"""``wire_agents``: the runtime has the four ports of ``agents`` built from the kernel's ports."""

from __future__ import annotations

from pathlib import Path

from orgmcp.agents import AgentDirectory, AgentRegistry, CharterReader, RetiredArchive
from orgmcp.agents._charters import FsCharterReader
from orgmcp.agents._directory import FsAgentDirectory
from orgmcp.agents._registry import FsAgentRegistry
from orgmcp.agents._retired import FsRetiredArchive
from orgmcp.agents.testing import MemoryAgents
from orgmcp.app import wiring
from orgmcp.kernel import AtomicWriter, OrgLayout, OrgPaths
from orgmcp.kernel.testing import RecordingAtomicWriter


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


def test_the_charter_is_written_through_the_atomic_writer_of_the_runtime(tmp_path: Path) -> None:
    written: list[tuple[Path, str]] = []

    def record(path: Path, text: str) -> None:
        written.append((path, text))

    wiring.open_runtime(tmp_path, {AtomicWriter: RecordingAtomicWriter(record)}).agent_registry.rewrite_charter("ceo", "text")
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
