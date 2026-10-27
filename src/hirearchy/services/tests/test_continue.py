# mypy: ignore-errors
# The tests that need the real record of a service (reflection's) and a team that retires and is hired again use the full organization of testkit
# (untyped): not type-checked strictly.
"""A root definition of a retired service's owner and name continues the retired service when a request of it has a result of any status
(design 5.10, DR-41): the same contract (the next version, the old ``created``), the same playbook and every earlier request as a case again, so
retiring the owner or the service never resets the record; the defining call cannot change the criteria or pass a playbook (P2-CONTINUES), and
every later change meets the gate with the whole record."""

import re
import time
from pathlib import Path

import pytest
from testkit.services_world import ENG, contract_meta, define, deliver, playbook_meta, request, svc  # noqa: F401  (svc is a fixture)

from hirearchy.kernel import ROOT, AtomicWriter, OrgError, split_frontmatter
from hirearchy.services.testing import fs_world

from ._support import answer, grant, populated
from ._support import define as define_in
from .test_define_answers import NOTE, RULE, YES

SERVICE = "weekly-brief"
STEPS = "## Steps\n1. Search.\n2. Write."
COPY = r"(\.retired/ceo-\d{8}T\d{6}/services/weekly-brief|ceo/services/\.retired/weekly-brief-\d{8}T\d{12})"


def retire_team_and_hire(org, owner="ceo"):
    """The user restructures: the owner and its team are retired, the same address is hired again."""
    org.retire_team(ROOT, owner, "restructure")
    org.hire(ROOT, owner, "Chief executive", "Run the company.", can_hire=True, max_children=2)


def refusal(org, **kw) -> str:
    with pytest.raises(OrgError) as info:
        define(org, **kw)
    return str(info.value)


def copies(org) -> list[Path]:
    """The retired copies of the service, wherever they are kept."""
    found = list((org.root / ".retired").glob("*/services/weekly-brief/SERVICE.md"))
    found += list(org.root.glob("*/services/.retired/weekly-brief-*/SERVICE.md"))
    found += list((org.root / ".retired").glob("*/services/.retired/weekly-brief-*/SERVICE.md"))
    return sorted(found)


def tree_of(org) -> Path:
    """The files below the organization that belong to the services, as text (what a refusal must leave as it was)."""
    return {str(p.relative_to(org.root)): p.read_bytes() for p in org.root.glob("**/services/**/*.md")}


def delivered_and_rejected(org, status="done", topic="ai"):
    task = request(org, topic)
    deliver(org, "ceo", task, status=status)
    return task, org.feedback(ROOT, task.id, "reject", NOTE, source="human")


# ------------------------------------------------------------------------------ the continuation


def test_redefining_with_other_criteria_after_retire_team_and_hire_is_refused_continues(svc):
    org = svc
    org.revise_playbook("ceo", SERVICE, "first", "first draft", [], text=STEPS)
    task, _ = delivered_and_rejected(org)
    retire_team_and_hire(org)
    before = tree_of(org)
    text = refusal(org, acceptance=["A different criterion"])
    path = re.search(r"kept at (\S+) \(", text).group(1)
    assert re.fullmatch(COPY, path)
    assert text == (
        f"refused: `weekly-brief` of ceo continues the retired service kept at {path} (1 request(s) with a result), so defining it again keeps "
        "its contract v1, its playbook v1 and its record. Leave out the change of the criteria: give no acceptance, add_acceptance or "
        "remove_acceptance, or acceptance exactly as in v1 (CLI: --acceptance, --add-acceptance, --remove-acceptance) and define it again; then "
        "change the criteria as an amendment, the user's answer to a rejection (answers=, about=, words=) or a change they asked for on their own "
        "(words= alone) (CLI: --answers, --about, --words). Nothing was written."
    )
    assert org.service_names("ceo") == [] and tree_of(org) == before
    both = refusal(org, acceptance=["A different criterion"], playbook=STEPS)
    assert "Leave out playbook (CLI: --playbook) and the change of the criteria: give no acceptance" in both
    assert "Leave out playbook (CLI: --playbook) and define it again" in refusal(org, playbook=STEPS)
    assert org.service_names("ceo") == [] and tree_of(org) == before


def test_redefining_with_its_criteria_continues_contract_playbook_and_cases(svc):
    org = svc
    org.revise_playbook("ceo", SERVICE, "first", "first draft", [], text=STEPS)
    task, no = delivered_and_rejected(org)
    first, _ = contract_meta(org)
    played = (org.dir("ceo") / "services" / SERVICE / "PLAYBOOK.md").read_text()
    retire_team_and_hire(org)
    (kept,) = copies(org)
    retired = {p.name: p.read_bytes() for p in kept.parent.rglob("*.md")}
    text = define(org)
    m = re.fullmatch(
        r"defined service `weekly-brief` for ceo again: it continues the retired one kept at (\S+) \(contract v1 -> v2, playbook v1, "
        r"1 request\(s\) with a result and their record\)\. (.*)", text, re.S,
    )
    assert m and re.fullmatch(COPY, m.group(1))
    assert m.group(2) == (
        f"Still open: rejection R1 (message {no.id}) has no answer. Record them before the criteria change (feedback first)."
    )
    meta, _ = contract_meta(org)
    assert meta["version"] == 2 and meta["created"] == first["created"] and meta["defined_by"] == ROOT and meta["defined"] > first["defined"]
    assert (org.dir("ceo") / "services" / SERVICE / "PLAYBOOK.md").read_text() == played  # the playbook continues at its version
    assert (org.dir("ceo") / "services" / SERVICE / "history" / "SERVICE.v1.md").read_bytes() == retired["SERVICE.md"]
    assert {p.name: p.read_bytes() for p in kept.parent.rglob("*.md")} == retired  # the retired copy is never changed
    (case,) = org.runtime.case_history.cases("ceo", SERVICE)
    assert [t.id for t in case.tasks] == [task.id] and [v.verdict for v in case.verdicts] == ["reject"]
    (note,) = [m for m in org.messages("ceo", "inbox") if m.title == "service weekly-brief continued as contract v2"]
    assert note.sender == "runtime" and note.wake is False and note.body == (
        f"root defined the service `weekly-brief` again: it continues the retired one kept at {m.group(1)}. Contract v2 has the criteria of v1; "
        "playbook v1; every earlier request is a case of it again."
    )


def test_the_continuation_changes_other_fields_and_lists_them(svc):
    org = svc
    delivered_and_rejected(org)
    retire_team_and_hire(org)
    text = define(org, budget=12, locked=True)
    assert "\nChanged:\n" in text and "budget per request: 10 -> 12 runs" in text and "locked: false -> true" in text
    (note,) = [m for m in org.messages("ceo", "inbox") if m.title == "service weekly-brief continued as contract v2"]
    assert "budget per request: 10 -> 12 runs" in note.body
    meta, _ = contract_meta(org)
    assert meta["version"] == 2 and meta["budget"] == 12 and "answers" not in meta and "initiated" not in meta


def test_after_a_continuation_an_amendment_meets_the_gate_with_the_whole_record(svc):
    org = svc
    task, no = delivered_and_rejected(org)
    retire_team_and_hire(org)
    define(org)
    with pytest.raises(OrgError) as info:
        org.define_service(ROOT, "ceo", SERVICE, add_acceptance=[RULE], words=YES)
    assert info.value.args[0].startswith(f"refused: rejection R1 (message {no.id}) on task {task.id} has no answer yet")
    assert contract_meta(org)[0]["version"] == 2
    org.define_service(ROOT, "ceo", SERVICE, add_acceptance=[RULE], answers=no.id, about="C1", words=YES)
    meta, _ = contract_meta(org)
    assert meta["version"] == 3 and meta["answers"] == no.id and meta["about"] == "C1"
    (link,) = [m for m in org.sent(ROOT) if m.reply_to == no.id and m.criterion]
    assert link.criterion == "C3" and org.runtime.service_evidence.confirmed("ceo", SERVICE) == frozenset({"C3"})


def test_the_same_after_retire_service_with_its_verdicts(svc):
    org = svc
    task, no = delivered_and_rejected(org)
    org.feedback(ROOT, task.id, "reject", "A one-off.", source="human", criterion=["none"], confirms=no.id)  # its answer
    org.retire_service(ROOT, "ceo", SERVICE, "redo")
    (kept,) = copies(org)
    assert re.search(r"ceo/services/\.retired/weekly-brief-\d{8}T\d{12}/SERVICE\.md$", str(kept))
    text = define(org)
    assert "continues the retired one kept at ceo/services/.retired/weekly-brief-" in text and "(contract v1 -> v2, no playbook yet, 1 request(s)" in text
    assert text.endswith("Every delivery has its verdict and every rejection its answer.")
    assert [c.id for c in org.runtime.case_history.cases("ceo", SERVICE)] == [task.id]
    org.define_service(ROOT, "ceo", SERVICE, add_acceptance=[RULE], words=YES)  # nothing is waiting: the user asked for it on their own
    assert contract_meta(org)[0]["initiated"] == "user" and contract_meta(org)[0]["version"] == 3


def test_a_retired_copy_without_a_recorded_request_is_a_first_definition(svc):
    """A service nobody got a result from has no record to keep (a rolled-back blueprint, a service retired before its first delivery)."""
    org = svc
    request(org)  # open: no result
    org.retire_service(ROOT, "ceo", SERVICE, "never delivered")
    text = define(org, acceptance=["Something else entirely"])
    assert text.startswith("defined service `weekly-brief` (contract v1) for ceo")
    meta, _ = contract_meta(org)
    assert meta["version"] == 1 and meta["acceptance"] == ["Something else entirely"]
    assert org.runtime.case_history.cases("ceo", SERVICE) == []


def test_weekly_is_not_continued_from_weekly_memo(svc):
    org = svc
    define(org, name="weekly-memo")
    task = org.request(ROOT, "weekly-memo", {"topic": "ai"})
    deliver(org, "ceo", task)
    org.feedback(ROOT, task.id, "accept", "fine", source="human")
    org.retire_service(ROOT, "ceo", "weekly-memo", "redo")
    text = define(org, name="weekly", acceptance=["Own criterion"])
    assert text.startswith("defined service `weekly` (contract v1) for ceo")


def test_the_same_name_for_another_top_level_agent_is_a_new_service(svc):
    org = svc
    delivered_and_rejected(org)
    org.retire_team(ROOT, "ceo", "restructure")
    org.hire(ROOT, "ops", "Operations", "Run ops.", can_hire=True, max_children=1)
    text = define(org, owner="ops", acceptance=["Own criterion"])  # the visible way around (design 5.8): a new service, a record that starts empty
    assert text.startswith("defined service `weekly-brief` (contract v1) for ops")
    assert org.runtime.case_history.cases("ops", SERVICE) == []


def test_an_unreadable_copy_fails_closed(svc):
    org = svc
    delivered_and_rejected(org)
    retire_team_and_hire(org)
    (kept,) = copies(org)
    kept.write_bytes(b"\xff\xfe not text")
    before = tree_of(org)
    text = refusal(org)
    assert text.startswith("refused: the record of `weekly-brief` cannot be read (") and text.endswith(
        "), so the contract was not changed. Try again; if it persists, tell the user."
    )
    assert org.service_names("ceo") == [] and tree_of(org) == before


def test_a_continuation_retired_and_continued_again_keeps_the_lineage(svc):
    org = svc
    task, no = delivered_and_rejected(org)
    first, _ = contract_meta(org)
    retire_team_and_hire(org)
    define(org)
    time.sleep(1.1)  # a tree is named after the second it was retired in
    retire_team_and_hire(org)
    text = define(org)
    assert "(contract v2 -> v3, no playbook yet, 1 request(s) with a result and their record)" in text
    meta, _ = contract_meta(org)
    assert meta["version"] == 3 and meta["created"] == first["created"]
    history = org.dir("ceo") / "services" / SERVICE / "history"
    assert sorted(p.name for p in history.iterdir()) == ["SERVICE.v1.md", "SERVICE.v2.md"]
    assert [c.id for c in org.runtime.case_history.cases("ceo", SERVICE)] == [task.id]
    with pytest.raises(OrgError, match=f"rejection R1 \\(message {no.id}\\)"):
        org.define_service(ROOT, "ceo", SERVICE, add_acceptance=[RULE], words=YES)


def test_a_definition_with_a_playbook_of_a_continued_name_is_refused_continues(svc):
    """What ``apply_org`` does for a service of a blueprint: it always passes a ``playbook`` (tests/e2e/test_no_bypass_0a2.py applies one)."""
    org = svc
    delivered_and_rejected(org)
    retire_team_and_hire(org)
    with pytest.raises(OrgError) as info:
        define(org, playbook=STEPS)
    assert "Leave out playbook (CLI: --playbook) and define it again" in info.value.args[0] and org.service_names("ceo") == []


# ------------------------------------------------------------------------------ DR-41: a result of any status keeps the record


def test_a_rejected_blocked_result_keeps_the_record_across_retire_team_hire_and_define(svc):
    org = svc
    task, no = delivered_and_rejected(org, status="blocked")
    retire_team_and_hire(org)
    assert "(1 request(s) with a result)" in refusal(org, acceptance=["Other criteria"])
    text = define(org)
    assert "continues the retired one kept at" in text and f"Still open: rejection R1 (message {no.id}) has no answer" in text
    (case,) = org.runtime.case_history.cases("ceo", SERVICE)
    assert [t.id for t in case.tasks] == [task.id]
    with pytest.raises(OrgError) as info:
        org.define_service(ROOT, "ceo", SERVICE, add_acceptance=[RULE], words=YES)
    assert info.value.args[0].startswith(f"refused: rejection R1 (message {no.id}) on task {task.id} has no answer yet")
    org.define_service(ROOT, "ceo", SERVICE, add_acceptance=[RULE], answers=no.id, about="C1", words=YES)
    assert contract_meta(org)[0]["version"] == 3


def test_retire_team_closes_open_requests_as_failed_so_they_are_recorded(svc):
    org = svc
    task = request(org)  # the team never answers it
    retire_team_and_hire(org)
    (closed,) = [m for m in org.received(ROOT) if m.type == "result" and m.reply_to == task.id]
    assert closed.status == "failed"
    text = define(org)
    assert "continues the retired one kept at" in text and "(contract v1 -> v2, no playbook yet, 1 request(s) with a result" in text
    assert [c.id for c in org.runtime.case_history.cases("ceo", SERVICE)] == [task.id]


def test_a_request_without_a_result_at_retire_service_is_not_recorded(svc):
    """The declared late-result facet: a request still open when the service is retired is no record, and its result, arriving after a fresh
    re-definition, falls outside every case of the new service (E5 counts it)."""
    org = svc
    task = request(org)
    org.retire_service(ROOT, "ceo", SERVICE, "redo")
    time.sleep(0.002)
    assert define(org).startswith("defined service `weekly-brief` (contract v1) for ceo")
    deliver(org, "ceo", task)  # the old team member answers late
    assert [m.reply_to for m in org.received(ROOT) if m.type == "result"] == [task.id]
    assert org.runtime.case_history.cases("ceo", SERVICE) == []
    org.retire_service(ROOT, "ceo", SERVICE, "again")
    assert define(org).startswith("defined service `weekly-brief` (contract v1) for ceo")  # the late result belongs to no service that exists


def test_a_continuation_with_answers_about_or_words_is_not_an_amendment(svc):
    org = svc
    _, no = delivered_and_rejected(org)
    retire_team_and_hire(org)
    not_an_amendment = (
        "refused: answers, about and words record the user's answer to a change of the acceptance criteria; this call changes none. Pass them only "
        "with acceptance, add_acceptance or remove_acceptance on an existing service (CLI: --acceptance, --add-acceptance, --remove-acceptance). "
        "Nothing was written."
    )
    before = tree_of(org)
    for given in ({"words": YES}, {"answers": no.id}, {"about": "C1"}, {"answers": no.id, "about": "C1", "words": YES}):
        assert refusal(org, **given) == not_an_amendment
    assert "continues the retired service" in refusal(org, acceptance=["Other"], words=YES)  # the criteria are refused first
    assert org.service_names("ceo") == [] and tree_of(org) == before


def test_a_continued_service_without_a_playbook_has_none_and_its_v1_is_pb_first_late(svc):
    """D6: the record of the retired copy holds a verdict, so a free first version is no longer allowed; the playbook is built one item at a time."""
    org = svc
    delivered_and_rejected(org)
    retire_team_and_hire(org)
    assert "no playbook yet" in define(org)
    assert not (org.dir("ceo") / "services" / SERVICE / "PLAYBOOK.md").exists()
    with pytest.raises(OrgError, match=r"already has evidence \(a verdict on "):
        org.revise_playbook("ceo", SERVICE, "first", "first draft", [], text=STEPS)
    assert not (org.dir("ceo") / "services" / SERVICE / "PLAYBOOK.md").exists()


# ------------------------------------------------------------------------------ writes that fail, the owner told, agents


class FailingWriter(AtomicWriter):
    """The writer that, once ``armed``, fails the ``nth`` write of a file called ``name`` (once) and writes through ``inner`` otherwise."""

    def __init__(self, inner: AtomicWriter, name: str, nth: int) -> None:
        self._inner = inner
        self._name = name
        self._nth = nth
        self._seen = 0
        self.armed = False

    def write(self, path: Path, text: str) -> None:
        if self.armed and path.name == self._name:
            self._seen += 1
            if self._seen == self._nth:
                raise OSError("disk full")
        self._inner.write(path, text)


def retired_service(tmp_path: Path, nth: int):
    """A world whose retired ``weekly-brief`` has a recorded request, and whose store fails the ``nth`` write of a ``SERVICE.md`` from now on."""
    made = []

    def wrap(inner: AtomicWriter) -> AtomicWriter:
        made.append(FailingWriter(inner, "SERVICE.md", nth))
        return made[0]

    w = populated(fs_world(tmp_path, writer=wrap))
    define_in(w)
    answer(w, w.commands.request("root", SERVICE, {"topic": "ai"}))
    w.commands.retire_service("root", "ceo", SERVICE, "redo")
    made[0].armed = True
    return w


def test_a_restore_that_fails_part_way_leaves_no_service_md(tmp_path):
    w = retired_service(tmp_path, nth=1)  # the restore writes SERVICE.md last: this is its last write
    with pytest.raises(OSError, match="disk full"):
        define_in(w)
    assert w.catalog.service_names("ceo") == [] and w.catalog.read_contract("ceo", SERVICE) is None  # no SERVICE.md: no service exists
    assert "continues the retired one" in define_in(w)  # a retry restores again, the same bytes
    assert w.catalog.read_contract("ceo", SERVICE).version == 2


def test_a_write_contract_failure_after_restore_leaves_the_copy_restored(tmp_path):
    w = retired_service(tmp_path, nth=2)  # the restore wrote SERVICE.md (1st); the next version's write is the 2nd
    (kept,) = [p for p in tmp_path.glob("ceo/services/.retired/weekly-brief-*/SERVICE.md")]
    with pytest.raises(OSError, match="disk full"):
        define_in(w)
    restored = w.catalog.read_contract("ceo", SERVICE)
    assert restored.version == 1 and (tmp_path / "ceo/services" / SERVICE / "SERVICE.md").read_bytes() == kept.read_bytes()  # the copy, exactly
    with pytest.raises(OrgError, match="^no change: the amendment leaves the contract of `weekly-brief` exactly as it is"):
        define_in(w)  # a retry is an ordinary amendment of it
    assert "redefined service `weekly-brief` of ceo: contract v1 -> v2" in define_in(w, budget=11)


def test_the_owner_is_told_the_service_continued(tmp_path):
    w = retired_service(tmp_path, nth=99)
    text = define_in(w)
    (note,) = [m for m in w.d.inbox("ceo") if m.title == "service weekly-brief continued as contract v2"]
    assert (note.sender, note.type, note.wake) == ("runtime", "note", False)
    assert note.body.startswith("root defined the service `weekly-brief` again: it continues the retired one kept at ceo/services/.retired/weekly-brief-")
    assert note.body.endswith("Contract v2 has the criteria of v1; playbook none yet; every earlier request is a case of it again.")
    assert "Every delivery has its verdict and every rejection its answer." in text
    assert w.events.events[-1].kind == "service.define" and w.events.events[-1].fields["amendment"] is True


def test_an_agent_clients_definition_never_continues(tmp_path):
    """Only root's definitions continue a retired copy: an agent client defines its report's service as a first definition (P2 binds root's)."""
    w = populated(fs_world(tmp_path))
    grant(w, "ceo", 20)
    define_in(w, owner=ENG, name="inner", actor="ceo")
    answer(w, w.commands.request("ceo", "inner", {"topic": "ai"}))
    w.commands.retire_service("ceo", ENG, "inner", "redo")
    text = define_in(w, owner=ENG, name="inner", actor="ceo", acceptance=["Fresh criterion"])
    assert text.startswith("defined service `inner` (contract v1) for ceo/eng")
    assert split_frontmatter((tmp_path / "ceo/eng/services/inner/SERVICE.md").read_text())[0]["version"] == 1
