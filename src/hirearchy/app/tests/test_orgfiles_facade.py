"""The orgfiles slice of the ``Org`` facade: reading and writing behave as they always did and now go through the ports of the runtime."""

from __future__ import annotations

import dataclasses
import inspect
from pathlib import Path

import pytest

from hirearchy import core
from hirearchy.app import Org
from hirearchy.kernel import OrgError
from hirearchy.orgfiles import OrgFileReader, OrgFileWriter


@pytest.fixture
def org(tmp_path: Path) -> Org:
    made = Org.init(tmp_path / "org", "mission")
    made.hire("root", "ceo", "CEO", "Leads.", can_hire=True)
    made.hire("ceo", "eng", "Engineer", "Builds.")
    return made


class RecordingReader(OrgFileReader):
    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[object, ...]]] = []

    def resolve_read(self, path: str, actor: str | None = None) -> Path:
        self.calls.append(("resolve_read", (path, actor)))
        return Path("/resolved")

    def read(self, path: str, actor: str | None = None) -> str:
        self.calls.append(("read", (path, actor)))
        return "shown"


class RecordingWriter(OrgFileWriter):
    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[object, ...]]] = []

    def resolve_write(self, actor: str, path: str) -> Path:
        self.calls.append(("resolve_write", (actor, path)))
        return Path("/w1")

    def write(self, actor: str, path: str, content: str, append: bool = False) -> Path:
        self.calls.append(("write", (actor, path, content, append)))
        return Path("/w2")

    def write_noted(self, actor: str, path: str, content: str, append: bool = False) -> tuple[Path, str]:
        self.calls.append(("write_noted", (actor, path, content, append)))
        return Path("/w3"), "a note"


def test_the_methods_come_from_the_ports_of_the_runtime(org: Org) -> None:
    reader, writer = RecordingReader(), RecordingWriter()
    org.runtime = dataclasses.replace(org.runtime, org_file_reader=reader, org_file_writer=writer)
    assert org.resolve_read("p", "a") == Path("/resolved") and org.resolve_read("q") == Path("/resolved")
    assert org.read("p", "a") == "shown" and org.read("q") == "shown" and org.read("r", actor="b") == "shown"
    assert org.resolve_write("a", "p") == Path("/w1")
    assert org.write("a", "p", "c") == Path("/w2") and org.write("a", "p", "c", True) == Path("/w2") and org.write("a", "p", "c", append=True)
    assert org.write_noted("a", "p", "c") == (Path("/w3"), "a note") and org.write_noted("a", "p", "c", append=True)[1] == "a note"
    assert reader.calls == [
        ("resolve_read", ("p", "a")), ("resolve_read", ("q", None)), ("read", ("p", "a")), ("read", ("q", None)), ("read", ("r", "b")),
    ]
    assert writer.calls == [
        ("resolve_write", ("a", "p")), ("write", ("a", "p", "c", False)), ("write", ("a", "p", "c", True)), ("write", ("a", "p", "c", True)),
        ("write_noted", ("a", "p", "c", False)), ("write_noted", ("a", "p", "c", True)),
    ]


def test_the_signatures_are_the_old_ones() -> None:
    for name, expected in (
        ("resolve_read", "(self, path: 'str', actor: 'str | None' = None) -> 'Path'"),
        ("read", "(self, path: 'str', actor: 'str | None' = None) -> 'str'"),
        ("resolve_write", "(self, actor: 'str', path: 'str') -> 'Path'"),
        ("write", "(self, actor: 'str', path: 'str', content: 'str', append: 'bool' = False) -> 'Path'"),
        ("write_noted", "(self, actor: 'str', path: 'str', content: 'str', append: 'bool' = False) -> 'tuple[Path, str]'"),
    ):
        assert str(inspect.signature(getattr(Org, name))) == expected, name


def test_the_org_reads_and_writes_the_files_of_its_directory(org: Org) -> None:
    path = org.write("ceo", "ceo/work/notes.md", "one two")
    assert path == org.root / "ceo" / "work" / "notes.md" and org.read("ceo/work/notes.md", "ceo/eng").startswith("[ceo/work/notes.md: 2 words")
    assert org.read("ceo/work") == "notes.md" and org.resolve_read("ceo/work") == org.root / "ceo" / "work"
    assert org.resolve_write("ceo", "ceo/work/x.md") == org.root / "ceo" / "work" / "x.md"
    with pytest.raises(OrgError, match="^you may only write inside your own directory"):
        org.write("ceo", "root/x.md", "x")
    with pytest.raises(OrgError, match="^no such agent: ghost$"):
        org.read("ceo", "ghost")


def test_a_charter_rewrite_keeps_the_frontmatter_and_says_so(org: Org) -> None:
    before, _ = org.charter("ceo/eng")
    path, note = org.write_noted("ceo", "ceo/eng/AGENT.md", "---\nrole: Sharper\n---\n# Role\nNew body.\n")
    after, body = org.charter("ceo/eng")
    assert path == org.root / "ceo" / "eng" / "AGENT.md" and after["role"] == "Sharper" and "New body." in body
    assert {k: v for k, v in after.items() if k != "role"} == {k: v for k, v in before.items() if k != "role"}
    assert note.startswith("charter frontmatter of `ceo/eng`: kept from the old frontmatter (not in your text): ")
    assert "changed (old -> new): role: Engineer -> Sharper." in note
    assert org.write_noted("ceo", "ceo/work/n.md", "x")[1] == ""


def test_the_old_module_level_helpers_are_still_importable_from_core(tmp_path: Path) -> None:
    fold, case_twin, short = getattr(core, "_fold"), getattr(core, "_case_twin"), getattr(core, "_short")
    folded, exact = getattr(core, "_FOLDED_RUNTIME_NAMES"), getattr(core, "_EXACT_FILES")
    assert fold("INBOX. ") == "inbox" and fold("ＭＥＭＯＲＹ.ｍｄ") == "memory.md"
    assert folded >= {"inbox", "sent", "runs", "services", ".paused"} and "work" not in folded
    assert exact == {"agent.md": "AGENT.md", "memory.md": "MEMORY.md", "org.md": "ORG.md"}
    (tmp_path / "Plan.md").write_text("x", encoding="utf-8")
    assert case_twin(tmp_path, "plan.md") == "Plan.md" and case_twin(tmp_path, "Plan.md") is None
    assert case_twin(tmp_path, "other.md") is None and case_twin(tmp_path / "missing", "x") is None
    assert case_twin(tmp_path / "Plan.md", "x") is None  # not a directory
    assert short("x" * 100) == "x" * 79 + "…" and short(["read"]) == "[read]"
    assert getattr(core, "charter_change_note")("a/b", {"role": "R", "tools": ["read"]}, {"role": "S"}, {}) == (
        "charter frontmatter of `a/b`: kept from the old frontmatter (not in your text): tools. changed (old -> new): role: R -> S. "
        "A key you leave out is kept; to remove one, set it explicitly (e.g. `tools: []`)."
    )
