# mypy: ignore-errors
# A test moved from tests/ by refactor step E1: not type-checked strictly (production code is). Delete the first line when this file is typed.

import pytest
from testkit.reach.hirearchy.core import ROOT, OrgError, split_frontmatter
from testkit.services_world import BRIEF, ENG, contract_meta, define, playbook_meta, request, svc, work


# --------------------------------------------------------------------------------------------- define
def test_define_writes_the_contract_without_a_playbook(org):
    text = define(org, notes="Mind the sources.")
    meta, body = contract_meta(org)
    assert meta["name"] == "weekly-brief" and meta["version"] == 1 and meta["budget"] == 10
    assert meta["locked"] is False and meta["defined_by"] == ROOT and meta["description"] == BRIEF["description"]
    assert meta["acceptance"] == BRIEF["acceptance"]
    assert meta["inputs"][1] == {"name": "week", "description": "ISO week; default the current one", "required": False}
    assert meta["deliverable"] == BRIEF["deliverable"] and body.strip() == "Mind the sources."
    assert not (org.dir("ceo") / "services" / "weekly-brief" / "PLAYBOOK.md").exists()
    assert "ceo/services/weekly-brief/SERVICE.md" in text and "no playbook yet" in text
    assert org.service_names("ceo") == ["weekly-brief"]
    assert not org.messages("ceo", "inbox")  # a first definition tells nobody


def test_define_with_a_playbook_writes_version_one(org):
    define(org, playbook="---\nignored: yes\n---\n## Steps\n1. Search.\n2. Write.")
    meta, body = playbook_meta(org)
    assert meta["version"] == 1 and meta["by"] == ROOT and meta["reason"] == "initial playbook"
    assert meta["service"] == "weekly-brief" and "ignored" not in meta
    assert body.strip().startswith("## Steps")
    assert org.runtime.service_catalog.read_playbook("ceo", "weekly-brief").version == 1


def test_only_the_parent_of_the_owner_defines_its_services(org):
    with pytest.raises(OrgError, match="only root, the parent of ceo"):
        define(org, actor="ceo", owner="ceo")  # an owner cannot define its own contract
    with pytest.raises(OrgError, match="only ceo, the parent of ceo/eng"):
        define(org, owner=ENG)  # root is not eng's parent
    org.hire("ceo", "qa", "Tester", "Test things.")
    with pytest.raises(OrgError, match="only ceo"):
        define(org, owner=ENG, actor="ceo/qa")  # a sibling cannot either
    define(org, owner=ENG, actor="ceo", name="eng-brief")  # a manager defines for its report (short names work too)
    assert org.service_names(ENG) == ["eng-brief"]
    define(org, owner="qa", actor="ceo", name="qa-brief")  # a short name works for a manager's own report
    assert org.service_names("ceo/qa") == ["qa-brief"]
    with pytest.raises(OrgError, match="no such agent"):
        define(org, owner="ghost")
    with pytest.raises(OrgError, match="no such agent"):
        define(org, owner=ROOT)


@pytest.mark.parametrize("over, match", [
    ({"name": "Bad Name"}, "service name"),
    ({"name": "name\n"}, "service name"),
    ({"description": " "}, "description"),
    ({"description": "two\nlines"}, "description"),
    ({"description": "x" * 301}, "description"),
    ({"acceptance": []}, "acceptance needs at least one"),
    ({"acceptance": ["  ", "-  "]}, "acceptance needs at least one"),
    ({"acceptance": [3]}, "only strings"),
    ({"inputs": [{"name": "Topic"}]}, "input name"),
    ({"inputs": [{"name": "a"}, {"name": "a"}]}, "used twice"),
    ({"inputs": [{"name": "a", "colour": "red"}]}, "unknown key"),
    ({"inputs": [{"name": "a", "required": "yes"}]}, "required must be"),
    ({"budget": 0}, "budget"),
    ({"budget": "10"}, "budget"),
    ({"budget": True}, "budget"),
    ({"deliverable": {"format": "md"}}, "needs a description"),
    ({"deliverable": "a file"}, "deliverable must be"),
    ({"deliverable": {"description": "x", "path": "relative/dir"}}, "absolute"),
    ({"deliverable": {"description": "x", "max_words": 0}}, "max_words"),
    ({"deliverable": {"description": "x", "colour": 1}}, "unknown key"),
    ({"locked": "yes"}, "locked"),
    ({"playbook": "  "}, "playbook is empty"),
])
def test_define_validation(org, over, match):
    with pytest.raises(OrgError, match=match):
        define(org, **over)
    assert org.service_names("ceo") == []  # nothing was written


def test_acceptance_may_be_a_newline_separated_string_and_inputs_may_be_empty(org):
    define(org, acceptance="- first criterion\n* second criterion\n\nthird", inputs=[])
    meta, _ = contract_meta(org)
    assert meta["acceptance"] == ["first criterion", "second criterion", "third"] and meta["inputs"] == []


def test_service_names_are_unique_among_the_owners_siblings(org):
    org.hire(ROOT, "ops", "Ops", "Run ops.", can_hire=True)
    define(org)
    with pytest.raises(OrgError, match="already exists at ceo"):
        define(org, owner="ops")
    define(org, owner="ops", name="other-brief")
    define(org, description="Redefined by the same owner's client.")  # same owner: a redefinition, not a clash
    # different levels do not clash: ceo/eng is not a sibling of ceo
    define(org, owner=ENG, actor="ceo")
    assert org.service_names(ENG) == ["weekly-brief"]


def test_redefinition_archives_bumps_the_version_and_tells_the_owner_quietly(svc):
    org = svc
    first, _ = contract_meta(org)
    text = define(org, acceptance=["At most 500 words", "Every factual claim has a source URL"], budget=12, locked=True)
    meta, _ = contract_meta(org)
    assert meta["version"] == 2 and meta["budget"] == 12 and meta["locked"] is True
    assert meta["created"] == first["created"]  # the service is the same one
    old = org.dir("ceo") / "services" / "weekly-brief" / "history" / "SERVICE.v1.md"
    assert split_frontmatter(old.read_text())[0]["version"] == 1
    assert "history/SERVICE.v1.md" in text and "v1 -> v2" in text
    (note,) = org.messages("ceo", "inbox")
    assert note.sender == "runtime" and note.wake is False and org.unread("ceo") == 0
    assert note.title == "contract of service weekly-brief changed to v2"
    assert "- acceptance removed: C1: At most 600 words" in note.body and "+ acceptance added: C3: At most 500 words" in note.body
    assert "budget per request: 10 -> 12 runs" in note.body and "locked: false -> true" in note.body
    assert "Every factual claim" not in note.body.split("Acceptance criteria now")[0]  # unchanged criteria are not diffed ...
    assert "Acceptance criteria now:\nC3: At most 500 words (not confirmed)\nC2: Every factual claim has a source URL\n" in note.body  # ... but listed with their ids


def test_redefinition_refuses_a_playbook_and_keeps_the_existing_one(org):
    define(org, playbook="Steps: search, write.")
    with pytest.raises(OrgError, match="belongs to ceo, which revises it"):
        define(org, playbook="Another playbook.")
    assert playbook_meta(org)[1].strip() == "Steps: search, write."
    assert contract_meta(org)[0]["version"] == 1


def test_retire_service_moves_it_away_and_it_cannot_be_requested(svc):
    org = svc
    out = org.retire_service(ROOT, "ceo", "weekly-brief", "no longer needed")
    assert ".retired/weekly-brief-" in out
    assert org.service_names("ceo") == []
    kept = list((org.dir("ceo") / "services" / ".retired").iterdir())
    assert len(kept) == 1 and (kept[0] / "SERVICE.md").is_file()
    (note,) = org.messages("ceo", "inbox")
    assert note.wake is False and "no longer needed" in note.body
    with pytest.raises(OrgError, match="no service `weekly-brief`"):
        request(org)
    with pytest.raises(OrgError, match="offers no service"):
        org.retire_service(ROOT, "ceo", "weekly-brief", "again")
    define(org)  # the name is free again, as a fresh v1
    assert contract_meta(org)[0]["version"] == 1


def test_only_the_parent_retires_a_service(svc):
    with pytest.raises(OrgError, match="direct reports"):
        svc.retire_service("ceo", "ceo", "weekly-brief", "mine")
    with pytest.raises(OrgError, match="reason"):
        svc.retire_service(ROOT, "ceo", "weekly-brief", " ")


# ------------------------------------------------------------------------------------ write guard
def test_the_runtime_owns_the_services_directory(svc):
    org = svc
    for path in ("ceo/services/weekly-brief/PLAYBOOK.md", "ceo/services/x.md", "ceo/Services/x.md", "ceo/services"):
        with pytest.raises(OrgError, match=r"services/ is managed by the runtime.*define_service.*revise_playbook"):
            org.write("ceo", path, "x")
    with pytest.raises(OrgError, match="reserved word"):
        org.hire("ceo", "services", "Odd", "x")
    assert not org.exists("ceo/services") and org.children("ceo") == [ENG]
    assert org.read("ceo/services/weekly-brief/SERVICE.md", actor=ENG).startswith("[ceo/services/weekly-brief/SERVICE.md")
    assert "SERVICE.md" in org.read("ceo/services/weekly-brief", actor="ceo")


def test_services_do_not_confuse_retire_or_run_counting(svc):
    org = svc
    org.revise_playbook("ceo", "weekly-brief", "Steps.", "r", [])
    org.delegate(ROOT, "ceo", "Plain", "g", "c", budget=2)
    work(org, "ceo")
    assert org.agents() == ["ceo", ENG] and org.runs_used("ceo") == 1
    r = org.retire_team(ROOT, "ceo", "done")
    assert r.addr == "ceo"
    retired = list((org.root / ".retired").glob("ceo-*"))
    assert (retired[0] / "services" / "weekly-brief" / "SERVICE.md").is_file()  # the service moved with its owner
