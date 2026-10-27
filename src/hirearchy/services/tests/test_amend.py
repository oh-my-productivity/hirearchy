# mypy: ignore-errors
# A test moved from tests/ by refactor step E1: not type-checked strictly (production code is). Delete the first line when this file is typed.

import pytest
from testkit.reach.hirearchy.core import ROOT, OrgError, split_frontmatter
from testkit.services_world import BRIEF, contract_meta, define, legacy_playbook, playbook_meta


def amend(org, **kw):
    """Root amends the contract. A change of the criteria carries the user's words (Rule W: ``words`` alone is a change the user asked for)."""
    if {"acceptance", "add_acceptance", "remove_acceptance"} & set(kw) and "words" not in kw and "answers" not in kw:
        kw = {**kw, "words": "Change them, please."}
    return org.define_service(ROOT, "ceo", "weekly-brief", **kw)


def amend_named(org, name, **kw):
    return org.define_service(ROOT, "ceo", name, **{"words": "Change them, please.", **kw})


@pytest.fixture
def svc(org):
    define(org, notes="Mind the sources.", locked=True, playbook="Steps: search, write.")
    return org


def test_an_amendment_keeps_every_omitted_field(svc):
    before, body = contract_meta(svc)
    amend(svc, budget=12)
    meta, new_body = contract_meta(svc)
    assert meta["version"] == 2 and meta["budget"] == 12
    for key in ("description", "inputs", "acceptance", "deliverable", "locked", "created", "name"):
        assert meta[key] == before[key], key
    assert new_body.strip() == body.strip() == "Mind the sources."
    assert playbook_meta(svc)[1].strip() == "- [P1] Steps: search, write." and playbook_meta(svc)[0]["version"] == 1


def test_single_fields_can_be_amended_and_explicit_values_replace(svc):
    amend(svc, description="A shorter brief.", locked=False, notes="New notes.", inputs=[])
    meta, body = contract_meta(svc)
    assert meta["description"] == "A shorter brief." and meta["locked"] is False and meta["inputs"] == []
    assert body.strip() == "New notes." and meta["acceptance"] == BRIEF["acceptance"] and meta["budget"] == 10
    amend(svc, deliverable={"description": "two files"})
    assert contract_meta(svc)[0]["deliverable"] == {"description": "two files"}  # a full replacement of that field


def test_add_acceptance_appends_and_a_string_works(svc):
    amend(svc, add_acceptance=["Never longer than one page", "- Names the week"])
    assert contract_meta(svc)[0]["acceptance"] == BRIEF["acceptance"] + ["Never longer than one page", "Names the week"]


def test_remove_acceptance_drops_exact_text(svc):
    amend(svc, remove_acceptance=["At most 600 words"])
    assert contract_meta(svc)[0]["acceptance"] == ["Every factual claim has a source URL"]


def test_add_and_remove_together(svc):
    amend(svc, add_acceptance=["At most 400 words"], remove_acceptance=["At most 600 words"])
    assert contract_meta(svc)[0]["acceptance"] == ["Every factual claim has a source URL", "At most 400 words"]


def test_acceptance_replaces_all_but_not_together_with_add_or_remove(svc):
    amend(svc, acceptance=["Only this"])
    assert contract_meta(svc)[0]["acceptance"] == ["Only this"]
    for extra in ({"add_acceptance": ["x y"]}, {"remove_acceptance": ["Only this"]}):
        with pytest.raises(OrgError, match="replaces all criteria.*add_acceptance / remove_acceptance"):
            amend(svc, acceptance=["Other"], **extra)
    assert contract_meta(svc)[0]["version"] == 2


def test_duplicate_unknown_and_emptying_criteria_are_refused_with_the_current_list(svc):
    with pytest.raises(OrgError, match=r'(?s)already a criterion: "At most 600 words".*C1: At most 600 words\nC2: Every factual'):
        amend(svc, add_acceptance=["At most 600 words"])
    with pytest.raises(OrgError, match=r'(?s)not found: "At most 700 words".*Current criteria.*C1: At most 600 words'):
        amend(svc, remove_acceptance=["At most 700 words"])
    with pytest.raises(OrgError, match="same criterion twice"):
        amend(svc, add_acceptance=["New one", "New one"])
    with pytest.raises(OrgError, match="without acceptance criteria"):
        amend(svc, remove_acceptance=BRIEF["acceptance"])
    with pytest.raises(OrgError, match="at least one"):
        amend(svc, acceptance=[])
    assert contract_meta(svc)[0]["version"] == 1  # nothing was written
    amend(svc, remove_acceptance=BRIEF["acceptance"], add_acceptance=["A fresh criterion"])  # replaced in one go is fine
    assert contract_meta(svc)[0]["acceptance"] == ["A fresh criterion"]


@pytest.mark.parametrize("over, match", [
    ({"description": " "}, "description"),
    ({"budget": 0}, "budget"),
    ({"locked": "yes"}, "locked"),
    ({"deliverable": {"format": "md"}}, "needs a description"),
    ({"inputs": [{"name": "A"}]}, "input name"),
    ({"playbook": "Mine now."}, "belongs to ceo"),
])
def test_amendment_values_are_validated(svc, over, match):
    with pytest.raises(OrgError, match=match):
        amend(svc, **over)
    assert contract_meta(svc)[0]["version"] == 1


def test_an_amendment_that_changes_nothing_is_refused(svc):
    for same in ({}, {"budget": 10}, {"description": BRIEF["description"]}, {"acceptance": BRIEF["acceptance"]},
                 {"add_acceptance": []}, {"locked": True}, {"notes": "Mind the sources."}):
        with pytest.raises(OrgError, match=r"(?s)no change.*C1: At most 600 words"):
            amend(svc, **same)
    assert contract_meta(svc)[0]["version"] == 1
    assert not svc.messages("ceo", "inbox")
    assert not (svc.dir("ceo") / "services" / "weekly-brief" / "history").exists()


def test_first_definitions_still_need_the_four_fields_and_refuse_add_remove(org):
    for left_out in ("description", "acceptance", "deliverable", "budget"):
        over = {k: v for k, v in BRIEF.items() if k != left_out}
        with pytest.raises(OrgError, match=f"first definition of `weekly-brief` needs {left_out}"):
            org.define_service(ROOT, "ceo", "weekly-brief", **over)
    with pytest.raises(OrgError, match="needs description, acceptance, deliverable, budget"):
        org.define_service(ROOT, "ceo", "weekly-brief")
    with pytest.raises(OrgError, match="does not exist yet.*full `acceptance`"):
        org.define_service(ROOT, "ceo", "weekly-brief", **{**BRIEF, "acceptance": None}, add_acceptance=["x y"])
    assert org.service_names("ceo") == []
    define(org, inputs=None, locked=None, notes=None)  # inputs / locked / notes default as before
    meta, body = contract_meta(org)
    assert meta["inputs"] == [] and meta["locked"] is False and body.strip() == ""


def test_the_note_and_the_reply_show_exactly_what_changed(svc):
    reply = amend(svc, add_acceptance=["Never longer than one page"], remove_acceptance=["At most 600 words"],
                  budget=12, description="A shorter brief.", locked=False,
                  deliverable={"description": "one file", "format": "markdown", "max_words": 300})
    (note,) = svc.messages("ceo", "inbox")
    assert note.sender == "runtime" and note.wake is False and note.title == "contract of service weekly-brief changed to v2"
    for text in (note.body, reply):
        assert "- acceptance removed: C1: At most 600 words" in text and "+ acceptance added: C3: Never longer than one page" in text
        assert "budget per request: 10 -> 12 runs" in text and "locked: true -> false" in text
        assert f'description: "{BRIEF["description"]}" -> "A shorter brief."' in text
        assert ('deliverable: "one markdown file" (format: markdown; max_words: 600) -> '
                '"one file" (format: markdown; max_words: 300)') in text
        assert "Every factual claim" not in text.split("Acceptance criteria now")[0]  # unchanged criteria are not diffed
    assert "- acceptance removed: C1: At most 600 words" in note.body and "+ acceptance added: C3: Never longer than one page" in note.body
    assert reply.split("\nRecorded as")[0].endswith("Acceptance criteria now (2):\nC2: Every factual claim has a source URL\nC3: Never longer than one page")
    assert "ceo/services/weekly-brief/SERVICE.md" in note.body
    amend(svc, notes="Fresh notes.")
    assert 'notes: "Mind the sources." -> "Fresh notes."' in svc.messages("ceo", "inbox")[-1].body


def test_an_amendment_bumps_the_version_and_archives_the_old_contract(svc):
    amend(svc, add_acceptance=["One more check"])
    amend(svc, add_acceptance=["And another check"])
    history = svc.dir("ceo") / "services" / "weekly-brief" / "history"
    v1, v2 = (split_frontmatter((history / f"SERVICE.v{n}.md").read_text())[0] for n in (1, 2))
    assert v1["version"] == 1 and v1["acceptance"] == BRIEF["acceptance"]
    assert v2["version"] == 2 and v2["acceptance"] == BRIEF["acceptance"] + ["One more check"]
    meta = contract_meta(svc)[0]
    assert meta["version"] == 3 and meta["acceptance"][-1] == "And another check"


def test_a_requested_task_carries_the_amended_criteria(svc):
    amend(svc, add_acceptance=["Never longer than one page"])
    task = svc.request(ROOT, "weekly-brief", {"topic": "ai"})
    assert "- C3: Never longer than one page" in task.body and "- C1: At most 600 words" in task.body


def test_services_text_lists_the_criteria_in_full(svc):
    amend(svc, add_acceptance=["Never longer than one page"])
    out = svc.runtime.service_reports.services_text(ROOT)
    assert ("  each request: 10 runs; acceptance criteria (ceo/services/weekly-brief/SERVICE.md):\n"
            "    C1: At most 600 words\n    C2: Every factual claim has a source URL\n"
            "    C3: Never longer than one page (amendment, user-initiated: never admits a playbook revision)\n  record:") in out
    assert "3 acceptance criteria" not in out
    assert "    C3: Never longer than one page" in svc.runtime.service_reports.services_text("ceo")  # the owner sees them too


def test_a_manager_amends_the_contract_of_its_report(org):
    org.hire(ROOT, "ceo2", "Boss", "Lead.", can_hire=True)
    org.hire("ceo2", "qa", "Tester", "Test things.")
    define(org, owner="ceo2/qa", actor="ceo2", name="qa-brief")
    org.define_service("ceo2", "qa", "qa-brief", add_acceptance=["Cite the test run"])
    assert contract_meta(org, "ceo2/qa", "qa-brief")[0]["acceptance"][-1] == "Cite the test run"
    with pytest.raises(OrgError, match="only ceo2"):
        org.define_service(ROOT, "ceo2/qa", "qa-brief", add_acceptance=["Not mine to add"])


def test_the_amendment_reply_lists_the_new_versions_criteria_with_ids(svc):
    reply = amend(svc, add_acceptance=["Dates are written in full"])
    assert "Acceptance criteria now (3):\nC1: At most 600 words\nC2: Every factual claim has a source URL\nC3: Dates are written in full" in reply
    assert "+ acceptance added: C3: Dates are written in full" in reply
    reply = amend(svc, remove_acceptance=["At most 600 words"])
    assert reply.split("\nRecorded as")[0].endswith("Acceptance criteria now (2):\nC2: Every factual claim has a source URL\nC3: Dates are written in full")  # ids never move
    assert "- acceptance removed: C1: At most 600 words" in reply


def test_amendment_errors_list_current_criteria_with_ids(svc):
    amend(svc, add_acceptance=["Dates are written in full"], remove_acceptance=["At most 600 words"])
    with pytest.raises(OrgError) as e:
        amend(svc, remove_acceptance=["At most 600 words"])  # gone: its id C1 is not offered any more
    assert str(e.value).endswith("Current criteria of `weekly-brief`:\nC2: Every factual claim has a source URL\nC3: Dates are written in full")
    with pytest.raises(OrgError) as e:
        amend(svc, add_acceptance=["Dates are written in full"])
    assert "C3: Dates are written in full" in str(e.value)
    with pytest.raises(OrgError) as e:
        amend(svc, budget=10)
    assert str(e.value).endswith("Current criteria:\nC2: Every factual claim has a source URL\nC3: Dates are written in full")


def test_the_owners_amendment_note_lists_every_current_criterion_with_its_id(svc):
    amend(svc, add_acceptance=["Dates are written in full"])
    amend(svc, add_acceptance=["Cite the test run"], remove_acceptance=["At most 600 words"])
    first, second = svc.messages("ceo", "inbox")
    assert second.body == (
        "root changed the contract of service `weekly-brief` (v2 -> v3). Read it, and follow the new criteria from the next request on:\n"
        "- acceptance removed: C1: At most 600 words\n+ acceptance added: C4: Cite the test run\n"
        'The client asked for this change on their own ("Change them, please."): C4 is user-initiated.\n'
        "Acceptance criteria now:\nC2: Every factual claim has a source URL\nC3: Dates are written in full (user-initiated)\n"
        "C4: Cite the test run (user-initiated)\nContract: ceo/services/weekly-brief/SERVICE.md"
    )  # locked in the fixture: no rule (c) line
    assert "Acceptance criteria now:\nC1: At most 600 words\nC2: Every factual claim has a source URL\nC3: Dates are written in full (user-initiated)\n" in first.body


def test_a_text_added_removed_and_added_again_keeps_its_id_through_define_service(svc):
    amend(svc, add_acceptance=["Dates are written in full"])  # C3
    amend(svc, remove_acceptance=["Dates are written in full"])
    reply = amend(svc, add_acceptance=["Dates are written in full", "Cite the test run"])
    assert "+ acceptance added: C3: Dates are written in full" in reply and "+ acceptance added: C4: Cite the test run" in reply
    assert reply.split("\nRecorded as")[0].endswith("C3: Dates are written in full\nC4: Cite the test run")
    assert [c.id for c in svc.runtime.service_catalog.criteria("ceo", "weekly-brief") if c.current] == ["C1", "C2", "C3", "C4"]


def test_removing_a_quoted_criterion_tells_the_owner_by_item_id(svc):
    define(svc, playbook="Steps: search, write.\n- C1: At most 600 words\n- Keep every claim sourced, at most 600 words.", name="quoted")
    amend_named(svc, "quoted", remove_acceptance=["At most 600 words"], add_acceptance=["At most 400 words"])
    note = svc.messages("ceo", "inbox")[-1].body
    assert (
        "Removed: C1. Playbook v1 still cites it in 2 item(s): P2, P3. Where it differs from the contract, follow the contract; the playbook changes "
        "only by an item change the evidence admits (step 3)."
    ) in note
    assert "[P2]" not in note.split("Removed: C1.")[1].split("\n")[0] and "At most 600 words" not in note.split("Removed: C1.")[1].split("\n")[0]
    assert note.index("Acceptance criteria now:") < note.index("Removed: C1.")
    amend_named(svc, "quoted", remove_acceptance=["Every factual claim has a source URL"])  # quoted by nothing
    assert "Removed:" not in svc.messages("ceo", "inbox")[-1].body



def test_the_removed_line_names_the_items_that_cite_it_by_id(svc):
    define(svc, name="cited", playbook="## Steps\n1. Open the sources.\n2. Check every claim (C2).\n3. Say it in at most 600 words.")
    amend_named(svc, "cited", remove_acceptance=["At most 600 words"], add_acceptance=["At most 400 words"])
    note = svc.messages("ceo", "inbox")[-1].body
    assert "Removed: C1. Playbook v1 still cites it in 1 item(s): P3. Where it differs" in note  # its words quoted; P2 cites C2, not C1
    amend_named(svc, "cited", remove_acceptance=["Every factual claim has a source URL"])
    assert "Removed: C2. Playbook v1 still cites it in 1 item(s): P2." in svc.messages("ceo", "inbox")[-1].body  # its id in the item's words


def test_a_legacy_playbook_keeps_its_quoted_lines_with_the_new_tail(svc):
    define(svc, name="legacy")
    legacy_playbook(svc, "Steps: search, write.\n- C1: At most 600 words\n- Keep every claim sourced, at most 600 words.", name="legacy")
    amend_named(svc, "legacy", remove_acceptance=["At most 600 words"], add_acceptance=["At most 400 words"])
    note = svc.messages("ceo", "inbox")[-1].body
    assert (
        'Removed: C1. Playbook v1 still quotes it in 2 line(s): "- C1: At most 600 words", "- Keep every claim sourced, at most 600 words.". '
        "Where it differs from the contract, follow the contract; the playbook changes only by an item change the evidence admits (step 3)."
    ) in note
