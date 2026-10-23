# mypy: ignore-errors
# A test moved from tests/ by refactor step E1: not type-checked strictly (production code is). Delete the first line when this file is typed.

import pytest
from testkit.reach.hirearchy.core import ROOT, OrgError
from testkit.services_world import ENG, confirmed_amendment, define, playbook_meta, svc

from hirearchy.services.testing import AdmittingServiceEvidence, RefusingServiceEvidence, fs_world

from ._support import define as define_in
from ._support import populated


# ----------------------------------------------------------------------------------- revise_playbook
def test_revise_playbook_versions_archives_and_tells_the_client(svc):
    org = svc
    assert org.revise_playbook("ceo", "weekly-brief", "---\nversion: 99\n---\n## Steps\n1. Search.", "first draft", []) == 1
    meta, body = playbook_meta(org)
    assert meta["version"] == 1 and meta["by"] == "ceo" and meta["reason"] == "first draft" and meta["service"] == "weekly-brief"
    assert body.strip() == "## Steps\n1. Search."  # the caller's frontmatter was stripped, the runtime's is used
    c3 = confirmed_amendment(org, "Every claim names its source")  # the user's amendment and their yes: the evidence of v2
    assert org.revise_playbook("ceo", "weekly-brief", "## Steps\n1. Search.\n- C3: Every claim names its source", "Cases A and B lacked sources", [c3]) == 2
    hist = org.dir("ceo") / "services" / "weekly-brief" / "history" / "PLAYBOOK.v1.md"
    assert "1. Search." in hist.read_text() and "C3: Every claim" not in hist.read_text()
    assert playbook_meta(org)[0]["version"] == 2
    notes = [n for n in org.messages(ROOT, "inbox") if n.sender == "runtime"]  # the helper's delivery put its result in the inbox too
    assert [n.title for n in notes] == [
        "playbook of weekly-brief revised to v1", "playbook of weekly-brief revised to v2",
    ]
    assert all(n.wake is False for n in notes)
    assert "Cases A and B lacked sources" in notes[1].body and "ceo/services/weekly-brief/PLAYBOOK.md" in notes[1].body
    assert org.unread(ROOT) == 1  # the helper's result only: the quiet notes add none


def test_the_client_of_a_nested_owner_gets_the_note_without_being_woken(org):
    define(org, owner=ENG, actor="ceo", name="eng-brief")
    org.revise_playbook(ENG, "eng-brief", "Steps.", "first", [])
    (note,) = org.messages("ceo", "inbox")
    assert note.wake is False and org.unread("ceo") == 0 and "revised to v1" in note.title


def test_only_the_owner_revises_and_only_unlocked_services(svc):
    org = svc
    with pytest.raises(OrgError, match="do not own a service called `weekly-brief`.*none"):
        org.revise_playbook(ENG, "weekly-brief", "Steps.", "r", [])
    with pytest.raises(OrgError, match="do not own"):
        org.revise_playbook(ROOT, "weekly-brief", "Steps.", "r", [])
    with pytest.raises(OrgError, match="do not own a service called `nope`.*weekly-brief"):
        org.revise_playbook("ceo", "nope", "Steps.", "r", [])
    define(org, locked=True)
    with pytest.raises(OrgError, match="locked by root"):
        org.revise_playbook("ceo", "weekly-brief", "Steps.", "r", [])
    define(org, locked=False)
    assert org.revise_playbook("ceo", "weekly-brief", "Steps.", "r", []) == 1


def test_revise_playbook_checks_content_reason_and_no_op(svc):
    org = svc
    with pytest.raises(OrgError, match="playbook is empty"):
        org.revise_playbook("ceo", "weekly-brief", "---\nx: 1\n---\n", "r", [])
    with pytest.raises(OrgError, match="reason is 1-400"):
        org.revise_playbook("ceo", "weekly-brief", "Steps.", " ", [])
    with pytest.raises(OrgError, match="reason is 1-400"):
        org.revise_playbook("ceo", "weekly-brief", "Steps.", "r" * 401, [])
    with pytest.raises(OrgError, match="the limit is 1000"):
        org.revise_playbook("ceo", "weekly-brief", "word " * 1001, "r", [])
    org.revise_playbook("ceo", "weekly-brief", "word " * 1000, "at the cap", [])
    with pytest.raises(OrgError, match="no change: this is identical to playbook v1"):
        org.revise_playbook("ceo", "weekly-brief", "---\nanything: 1\n---\n" + "word " * 1000, "again", [])
    assert playbook_meta(org)[0]["version"] == 1


def test_the_word_cap_is_configurable(svc):
    org = svc
    text = (org.root / "ORG.md").read_text().replace("playbook_max_words: 1000", "playbook_max_words: 5")
    (org.root / "ORG.md").write_text(text)
    with pytest.raises(OrgError, match="the limit is 5"):
        org.revise_playbook("ceo", "weekly-brief", "one two three four five six", "r", [])


# ----------------------------------------------------------------------------------- the lines of a revision (P1)
class RecordingEvidence(AdmittingServiceEvidence):
    """The stand-in gate that remembers what it was asked."""

    def __init__(self) -> None:
        super().__init__()
        self.asked: list[tuple[str | None, tuple[str, ...]]] = []

    def admit(self, owner, service, evidence, reason, *, exempt=None, lines=()):
        self.asked.append((exempt, tuple(lines)))
        return super().admit(owner, service, evidence, reason, exempt=exempt, lines=lines)


def test_revise_playbook_passes_the_changed_lines_to_the_gate(tmp_path):
    gate = RecordingEvidence()
    w = populated(fs_world(tmp_path, gate))
    define_in(w)
    w.commands.revise_playbook("ceo", "weekly-brief", "A one\nB two\nC three", "first", [])
    w.commands.revise_playbook("ceo", "weekly-brief", "A one\nB changed\nC three\nD four", "second", ["R1"])
    w.commands.revise_playbook("ceo", "weekly-brief", "A one\nC three", "third", ["R1"])  # a removal only
    assert gate.asked == [("first", ()), (None, ("B changed", "D four")), (None, ())]


def test_a_refused_revision_writes_nothing(tmp_path):
    w = populated(fs_world(tmp_path, RefusingServiceEvidence("refused by the stand-in for the gate")))
    define_in(w, playbook="A one\nB two")
    before = w.text("ceo/services/weekly-brief/PLAYBOOK.md")
    with pytest.raises(OrgError, match="^refused by the stand-in"):
        w.commands.revise_playbook("ceo", "weekly-brief", "A one\nB three", "why", ["R1"])
    assert w.text("ceo/services/weekly-brief/PLAYBOOK.md") == before and w.d.inbox("root") == []


def test_roots_note_lists_the_admitted_lines_and_the_removed_count(tmp_path):
    w = populated(fs_world(tmp_path, AdmittingServiceEvidence()))
    define_in(w)
    w.commands.revise_playbook("ceo", "weekly-brief", "A one\nB two\nC three", "first", [])
    w.commands.revise_playbook("ceo", "weekly-brief", "A one\nB changed\nC three", "second", ["R1"])  # one line changed, one removed
    w.commands.revise_playbook("ceo", "weekly-brief", "A one\nB changed\nC three\nD four", "third", ["R2"])  # added only
    w.commands.revise_playbook("ceo", "weekly-brief", "A one\nD four", "fourth", ["R3"])  # removed only (and reordered)
    first, second, third, fourth = (m.body for m in w.d.inbox("root"))
    where = "File: ceo/services/weekly-brief/PLAYBOOK.md"
    stand_in = "admitted: admitted by the stand-in for the gate"
    head = "Lines added or changed (each with the id that admits it):"
    assert first == f"ceo revised the playbook of service `weekly-brief` to v1.\nReason: first\nEvidence: none; the first playbook (no evidence needed)\n{where}"
    assert second == f"ceo revised the playbook of service `weekly-brief` to v2.\nReason: second\nEvidence: R1; {stand_in}\n{head}\n- [R1] B changed\n1 line(s) removed.\n{where}"
    assert third == f"ceo revised the playbook of service `weekly-brief` to v3.\nReason: third\nEvidence: R2; {stand_in}\n{head}\n- [R2] D four\n{where}"
    assert fourth == f"ceo revised the playbook of service `weekly-brief` to v4.\nReason: fourth\nEvidence: R3; {stand_in}\n2 line(s) removed.\n{where}"
