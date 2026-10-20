"""``wire_orgfiles``: the runtime has the three ``orgfiles`` ports, built from the layout, the agents, the access ports, the settings and
the atomic writer of the runtime."""

from __future__ import annotations

from pathlib import Path

import pytest

from orgmcp.agents import AgentDirectory, AgentRegistry, CharterReader
from orgmcp.agents.testing import MemoryAgents
from orgmcp.app import wiring
from orgmcp.kernel import AtomicWriter, OrgError, join_frontmatter
from orgmcp.kernel.testing import FailingAtomicWriter, MemoryAtomicWriter
from orgmcp.orgfiles import OrgFileReader, OrgFileStore, OrgFileWriter
from orgmcp.orgfiles.testing import MemoryOrgFileStore


@pytest.fixture
def root(tmp_path: Path) -> Path:
    (tmp_path / "ORG.md").write_text("---\nmemory_max_words: 3\n---\nrules\n", encoding="utf-8")
    for addr in ("ceo", "ceo/eng"):
        (tmp_path / addr).mkdir(parents=True, exist_ok=True)
        (tmp_path / addr / "AGENT.md").write_text(join_frontmatter({"role": addr}, "body"), encoding="utf-8")
    return tmp_path


def test_the_runtime_has_the_orgfiles_ports(tmp_path: Path) -> None:
    runtime = wiring.open_runtime(tmp_path)
    assert isinstance(runtime.org_file_store, OrgFileStore)
    assert isinstance(runtime.org_file_reader, OrgFileReader) and isinstance(runtime.org_file_writer, OrgFileWriter)


def test_building_the_ports_touches_nothing(tmp_path: Path) -> None:
    runtime = wiring.open_runtime(tmp_path)
    assert runtime.org_file_reader and runtime.org_file_writer
    assert list(tmp_path.iterdir()) == []


def test_the_writer_and_the_reader_work_on_the_files_of_the_runtime_root(root: Path) -> None:
    runtime = wiring.open_runtime(root)
    assert runtime.org_file_writer.write("ceo", "ceo/work/n.md", "a b") == root / "ceo" / "work" / "n.md"
    assert (root / "ceo" / "work" / "n.md").read_text(encoding="utf-8") == "a b"
    assert runtime.org_file_reader.read("ceo/work/n.md").startswith("[ceo/work/n.md: 2 words, 0 lines, modified ")
    assert runtime.org_file_reader.read("ceo/work") == "n.md"


def test_the_cap_is_the_one_of_the_org_md_of_the_root(root: Path) -> None:
    runtime = wiring.open_runtime(root)
    runtime.org_file_writer.write("ceo", "ceo/MEMORY.md", "one two three")
    with pytest.raises(OrgError, match="would be 4 words; the limit is 3"):
        runtime.org_file_writer.write("ceo", "ceo/MEMORY.md", "one two three four")


def test_the_guard_asks_the_agents_of_the_runtime(root: Path) -> None:
    runtime = wiring.open_runtime(root)
    with pytest.raises(OrgError, match="^AGENT.md can only be written for an existing direct report"):
        runtime.org_file_writer.write("ceo", "ceo/ops/AGENT.md", "---\nrole: x\n---\n")
    runtime.org_file_writer.write("ceo", "ceo/eng/AGENT.md", "---\nrole: Eng 2\n---\nnew\n")
    assert "role: Eng 2" in (root / "ceo" / "eng" / "AGENT.md").read_text(encoding="utf-8")


def test_the_reader_asks_the_access_ports_of_the_runtime(root: Path, tmp_path_factory: pytest.TempPathFactory) -> None:
    elsewhere = tmp_path_factory.mktemp("ws")
    (elsewhere / "p.md").write_text("x", encoding="utf-8")
    (root / "ceo" / "AGENT.md").write_text(join_frontmatter({"role": "ceo", "workspace": str(elsewhere)}, "body"), encoding="utf-8")
    runtime = wiring.open_runtime(root)
    assert runtime.org_file_reader.read(str(elsewhere / "p.md"), "ceo").endswith("\nx")
    with pytest.raises(OrgError, match="^you can only read inside the organization$"):
        runtime.org_file_reader.read(str(elsewhere / "p.md"))


def test_the_store_writes_through_the_atomic_writer_of_the_runtime(root: Path) -> None:
    sink = MemoryAtomicWriter()
    runtime = wiring.open_runtime(root, {AtomicWriter: sink})
    runtime.org_file_writer.write("ceo", "ceo/work/n.md", "text")
    assert sink.files == {root / "ceo" / "work" / "n.md": "text"} and not (root / "ceo" / "work").exists()
    failing = wiring.open_runtime(root, {AtomicWriter: FailingAtomicWriter(MemoryAtomicWriter())})
    with pytest.raises(OSError, match="No space left"):
        failing.org_file_writer.write("ceo", "ceo/work/m.md", "x")


def test_an_override_of_the_store_and_the_agents_runs_the_writer_in_memory(root: Path) -> None:
    agents = MemoryAgents()
    agents.root = root
    agents.create("ceo", {"role": "CEO"}, "body")
    store = MemoryOrgFileStore(agents)
    runtime = wiring.open_runtime(
        root, {AgentDirectory: agents, CharterReader: agents, AgentRegistry: agents, OrgFileStore: store}
    )
    assert runtime.org_file_store is store
    runtime.org_file_writer.write("ceo", "ceo/work/n.md", "in memory")
    assert store.read(root / "ceo" / "work" / "n.md") == "in memory" and runtime.org_file_reader.read("ceo/work") == "n.md"
    assert not (root / "ceo" / "work").exists()


def test_a_charter_rewrite_goes_through_the_registry_of_the_runtime(root: Path) -> None:
    class Recording(MemoryAgents):
        def __init__(self) -> None:
            super().__init__()
            self.rewrites: list[tuple[str, str]] = []

        def rewrite_charter(self, addr: str, text: str) -> None:
            self.rewrites.append((addr, text))

    registry = Recording()
    runtime = wiring.open_runtime(root, {AgentRegistry: registry})
    runtime.org_file_writer.write("ceo", "ceo/eng/AGENT.md", "---\nrole: Eng 2\n---\nnew\n")
    assert registry.rewrites == [("ceo/eng", "---\nrole: Eng 2\n---\nnew\n")]
    assert "role: Eng 2" not in (root / "ceo" / "eng" / "AGENT.md").read_text(encoding="utf-8")
