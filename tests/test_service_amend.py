"""define_service on an existing service is an amendment: omitted fields keep their value; add/remove criteria."""

import pytest

from orgmcp import services
from orgmcp.core import ROOT, OrgError, split_frontmatter

from testkit.services_world import BRIEF, call, cli, contract_meta, define, fails, playbook_meta  # noqa: F401


def amend(org, **kw):
    return org.define_service(ROOT, "ceo", "weekly-brief", **kw)


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
    assert playbook_meta(svc)[1].strip() == "Steps: search, write." and playbook_meta(svc)[0]["version"] == 1


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
    with pytest.raises(OrgError, match=r'(?s)already a criterion: "At most 600 words".*1\. At most 600 words\n2\. Every factual'):
        amend(svc, add_acceptance=["At most 600 words"])
    with pytest.raises(OrgError, match=r'(?s)not found: "At most 700 words".*Current criteria.*1\. At most 600 words'):
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
        with pytest.raises(OrgError, match=r"(?s)no change.*1\. At most 600 words"):
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
        assert "- acceptance removed: At most 600 words" in text and "+ acceptance added: Never longer than one page" in text
        assert "budget per request: 10 -> 12 runs" in text and "locked: true -> false" in text
        assert f'description: "{BRIEF["description"]}" -> "A shorter brief."' in text
        assert ('deliverable: "one markdown file" (format: markdown; max_words: 600) -> '
                '"one file" (format: markdown; max_words: 300)') in text
        assert "Every factual claim" not in text.split("Acceptance criteria now")[0]  # unchanged criteria are not diffed
    assert reply.endswith("Acceptance criteria now (2):\n1. Every factual claim has a source URL\n2. Never longer than one page")
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
    assert "- Never longer than one page" in task.body


def test_services_text_lists_the_criteria_in_full(svc):
    amend(svc, add_acceptance=["Never longer than one page"])
    out = services.services_text(svc, ROOT)
    assert ("  each request: 10 runs; acceptance criteria (ceo/services/weekly-brief/SERVICE.md):\n"
            "    1. At most 600 words\n    2. Every factual claim has a source URL\n    3. Never longer than one page\n"
            "  record:") in out
    assert "3 acceptance criteria" not in out
    assert "    3. Never longer than one page" in services.services_text(svc, "ceo")  # the owner sees them too


def test_a_manager_amends_the_contract_of_its_report(org):
    org.hire(ROOT, "ceo2", "Boss", "Lead.", can_hire=True)
    org.hire("ceo2", "qa", "Tester", "Test things.")
    define(org, owner="ceo2/qa", actor="ceo2", name="qa-brief")
    org.define_service("ceo2", "qa", "qa-brief", add_acceptance=["Cite the test run"])
    assert contract_meta(org, "ceo2/qa", "qa-brief")[0]["acceptance"][-1] == "Cite the test run"
    with pytest.raises(OrgError, match="only ceo2"):
        org.define_service(ROOT, "ceo2/qa", "qa-brief", add_acceptance=["Not mine to add"])


def test_cli_amendment(svc, capsys, tmp_path):
    cli(svc, "define-service", "ceo", "weekly-brief", "--add-acceptance", "Never longer than one page")
    out = capsys.readouterr().out
    assert "v1 -> v2" in out and "3. Never longer than one page" in out
    meta = contract_meta(svc)[0]
    assert meta["acceptance"][-1] == "Never longer than one page" and meta["budget"] == 10 and meta["deliverable"] == BRIEF["deliverable"]

    more = tmp_path / "more.txt"
    more.write_text("First extra\n- Second extra\n")
    cli(svc, "define-service", "ceo", "weekly-brief", "--remove-acceptance", "At most 600 words",
        "--remove-acceptance", "Never longer than one page", "--add-acceptance", f"@{more}")
    assert contract_meta(svc)[0]["acceptance"] == ["Every factual claim has a source URL", "First extra", "Second extra"]

    cli(svc, "define-service", "ceo", "weekly-brief", "--budget", "7", "--no-locked", "--max-words", "250", "--input", "topic*:the topic")
    meta = contract_meta(svc)[0]
    assert meta["budget"] == 7 and meta["locked"] is False and meta["inputs"] == [{"name": "topic", "description": "the topic", "required": True}]
    assert meta["deliverable"] == {**BRIEF["deliverable"], "max_words": 250}  # single deliverable parts merge over the old one
    capsys.readouterr()

    for args, message in (
        (("weekly-brief", "--acceptance", "Whole new", "--add-acceptance", "x y"), "replaces all criteria"),
        (("weekly-brief", "--budget", "7"), "no change"),
        (("brand-new", "--budget", "3"), "needs description"),
    ):
        with pytest.raises(SystemExit):
            cli(svc, "define-service", "ceo", *args)
        assert message in capsys.readouterr().err
