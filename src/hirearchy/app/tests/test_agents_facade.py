"""The agents slice of the ``Org`` facade: ``exists`` ... ``memory``, the skeleton that ``hire`` makes, the move that ``retire_team``
makes and the charter rewrite of ``write`` behave as they always did, and now go through the ports of the runtime."""

from __future__ import annotations

import inspect
from datetime import datetime, timezone
from pathlib import Path

import pytest

from hirearchy.app import Org, wiring
from hirearchy.kernel import AtomicWriter, Clock, OrgError
from hirearchy.kernel._system import FsAtomicWriter
from hirearchy.kernel.testing import FailingAtomicWriter
from testkit.clocks import ClockReading

SKELETON = ["AGENT.md", "MEMORY.md", "inbox", "inflight", "read", "runs", "sent", "work"]


@pytest.fixture
def org(tmp_path: Path) -> Org:
    made = Org.init(tmp_path / "org", "mission")
    made.hire("root", "ceo", "Boss", "Runs it.", can_hire=True, max_children=3)
    made.hire("ceo", "eng", "Engineer", "Builds.", can_hire=True, approved=True)
    made.hire("ceo", "ops", "Operator", "Operates.")
    made.hire("ceo/eng", "qa", "Tester", "Tests.")
    made.hire("root", "cto", "Chief", "Advises.")
    return made


def test_the_tree_is_what_hire_made(org: Org) -> None:
    assert org.agents() == ["ceo", "ceo/eng", "ceo/eng/qa", "ceo/ops", "cto"]
    assert org.children("root") == ["ceo", "cto"] and org.children("ceo") == ["ceo/eng", "ceo/ops"]
    assert org.subtree("ceo") == ["ceo", "ceo/ops", "ceo/eng", "ceo/eng/qa"]
    assert org.exists("ceo/eng/qa") and org.exists(" /ceo/ ") and org.exists("root") and not org.exists("nobody")
    assert org.require(" /ceo/eng/ ") == "ceo/eng"
    with pytest.raises(OrgError, match="^no such agent: nobody$"):
        org.require("nobody")


def test_a_hired_agent_has_the_skeleton_an_empty_memory_and_a_charter(org: Org) -> None:
    assert sorted(p.name for p in org.dir("ceo/ops").iterdir()) == SKELETON
    assert (org.dir("ceo/ops") / "MEMORY.md").read_text(encoding="utf-8") == ""
    meta, body = org.charter("ceo/ops")
    assert meta["role"] == "Operator" and meta["hired_by"] == "ceo" and body.startswith("# Role: Operator")
    assert org.memory("ceo/ops") == "" and org.memory("nobody") == ""
    assert org.charter("root") == ({"role": "human (root of the organization)"}, "")


def test_the_memory_is_read_as_the_agent_wrote_it(org: Org) -> None:
    org.write("ceo", "ceo/MEMORY.md", "  # notes é\n\n")
    assert org.memory("ceo") == "  # notes é\n\n"


def test_the_charter_file_is_written_last(org: Org) -> None:
    flaky = FailingAtomicWriter(FsAtomicWriter(), lambda path: path.name == "AGENT.md", OSError("disk full"))
    org.runtime = wiring.open_runtime(org.root, {AtomicWriter: flaky})
    with pytest.raises(OSError):
        org.hire("ceo", "new", "New", "Newer.")
    org.runtime = wiring.open_runtime(org.root)
    assert not org.exists("ceo/new") and "ceo/new" not in org.agents()
    assert sorted(p.name for p in org.dir("ceo/new").iterdir()) == [s for s in SKELETON if s != "AGENT.md"]


def test_hire_still_refuses_an_existing_agent_and_leaves_it_alone(org: Org) -> None:
    before = (org.dir("ceo/ops") / "AGENT.md").read_bytes()
    with pytest.raises(OrgError, match="ceo/ops already exists"):
        org.hire("ceo", "ops", "Other", "Other.")
    assert (org.dir("ceo/ops") / "AGENT.md").read_bytes() == before


def test_a_retired_team_moves_to_a_stamped_name_below_retired(org: Org) -> None:
    org.runtime = wiring.open_runtime(org.root, {Clock: ClockReading(lambda: datetime(2026, 10, 18, 10, 15, 0, tzinfo=timezone.utc))})
    assert org.retire("ceo", "eng", "done") == "ceo/eng"
    retired = org.root / ".retired" / "ceo.eng-20261018T101500"
    assert sorted(p.name for p in retired.iterdir()) == sorted([*SKELETON, "RETIRED.md", "qa"])  # commit 14: a retire writes its record
    assert not org.dir("ceo/eng").exists() and org.agents() == ["ceo", "ceo/ops", "cto"]
    assert org.retire("root", "cto", "closed") == "cto"
    assert (org.root / ".retired" / "cto-20261018T101500" / "AGENT.md").is_file()


def test_the_retired_archive_of_the_runtime_sees_what_retire_moved(org: Org) -> None:
    org.retire("ceo", "eng", "done")
    org.retire("root", "cto", "closed")
    trees = org.runtime.retired_archive.trees()
    assert [(t.name.split("-")[0], t.top_level) for t in trees] == [("ceo.eng", False), ("cto", True)]


def test_a_charter_rewrite_goes_through_the_registry_and_the_atomic_writer_of_the_runtime(org: Org) -> None:
    written: list[Path] = []

    class Spy(FsAtomicWriter):
        def write(self, path: Path, text: str) -> None:
            written.append(path)
            super().write(path, text)

    org.runtime = wiring.open_runtime(org.root, {AtomicWriter: Spy()})
    org.write("ceo", "ceo/ops/AGENT.md", "---\nrole: Operator 2\n---\nNew words.\n")
    assert written == [org.dir("ceo/ops") / "AGENT.md"]
    meta, body = org.charter("ceo/ops")
    assert meta["role"] == "Operator 2" and meta["hired_by"] == "ceo" and body == "New words."  # the old keys are kept


def test_a_charter_rewrite_note_names_what_was_kept(org: Org) -> None:
    path, note = org.write_noted("ceo", "ceo/ops/AGENT.md", "---\nrole: Operator 2\n---\nx\n")
    assert path == org.dir("ceo/ops") / "AGENT.md"
    assert note.startswith("charter frontmatter of `ceo/ops`: kept from the old frontmatter (not in your text): ")


def test_an_appended_charter_is_written_as_one_charter(org: Org) -> None:
    before = (org.dir("ceo") / "AGENT.md").read_text(encoding="utf-8")
    org.write("root", "ceo/AGENT.md", "\nAn extra line.\n", append=True)  # root's rewrite does not merge the frontmatter
    assert (org.dir("ceo") / "AGENT.md").read_text(encoding="utf-8") == before + "\nAn extra line.\n"


def test_other_files_are_still_written_by_the_org_files(org: Org) -> None:
    org.write("ceo", "ceo/work/note.md", "hello")
    assert (org.dir("ceo") / "work" / "note.md").read_text(encoding="utf-8") == "hello"


def test_the_slice_keeps_its_signatures() -> None:
    names = ["exists", "require", "children", "agents", "subtree", "charter", "memory"]
    assert [list(inspect.signature(getattr(Org, n)).parameters) for n in names] == [
        ["self", "addr"], ["self", "addr"], ["self", "addr"], ["self"], ["self", "addr"], ["self", "addr"], ["self", "addr"]
    ]
