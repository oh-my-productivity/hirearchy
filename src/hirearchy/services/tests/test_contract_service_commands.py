"""Contract of ``ServiceCommands``: defining, amending, retiring, revising, requesting and rating a service behave the same over disk and memory.

What the callers rely on: the confirmation and refusal texts (written for an LLM), the files that are written (a first definition, an amendment that
keeps the old contract, a playbook that keeps the old version), the quiet notes to the other side, and the task a request makes."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from hirearchy.kernel import Message, OrgError, split_frontmatter
from hirearchy.services import FEEDBACK_HEADER, ServiceCommands
from hirearchy.services.testing import IMPLEMENTATIONS, ServicesWorld

from ._support import BRIEF, STEPS, amend, answer, define, grant, implementations, make, request

CONTRACT = "ceo/services/weekly-brief/SERVICE.md"
PLAYBOOK = "ceo/services/weekly-brief/PLAYBOOK.md"


@pytest.fixture(params=implementations(IMPLEMENTATIONS[ServiceCommands]))
def w(request: pytest.FixtureRequest, tmp_path: Path) -> ServicesWorld:
    made = make(request, tmp_path)
    assert isinstance(made.commands, ServiceCommands)
    return made


def meta_of(w: ServicesWorld, rel: str) -> tuple[dict[str, object], str]:
    text = w.text(rel)
    assert text is not None, rel
    return split_frontmatter(text)


def refusal(w: ServicesWorld, **over: Any) -> str:
    with pytest.raises(OrgError) as e:
        define(w, **over)
    return str(e.value)


# ============================================================================================== define: a first definition


def test_a_first_definition_writes_the_contract_without_a_playbook(w: ServicesWorld) -> None:
    text = define(w, notes="Mind the sources.")
    meta, body = meta_of(w, CONTRACT)
    assert (meta["name"], meta["version"], meta["budget"], meta["locked"], meta["defined_by"]) == ("weekly-brief", 1, 10, False, "root")
    assert meta["acceptance"] == BRIEF["acceptance"] and meta["deliverable"] == BRIEF["deliverable"] and body.strip() == "Mind the sources."
    assert meta["created"] == meta["defined"]
    assert w.text(PLAYBOOK) is None
    assert text == (
        "defined service `weekly-brief` (contract v1) for ceo: ceo/services/weekly-brief/SERVICE.md. "
        "It has no playbook yet: ceo writes v1 with revise_playbook after its first request."
    )


def test_a_first_definition_tells_nobody(w: ServicesWorld) -> None:
    define(w)
    assert w.d.inbox("ceo") == []


def test_a_first_definition_with_a_playbook_writes_version_one_without_its_frontmatter(w: ServicesWorld) -> None:
    text = define(w, playbook=f"---\nignored: yes\n---\n{STEPS}")
    meta, body = meta_of(w, PLAYBOOK)
    assert (meta["service"], meta["version"], meta["by"], meta["reason"]) == ("weekly-brief", 1, "root", "initial playbook")
    assert "ignored" not in meta and body.strip() == STEPS
    assert text.endswith("for ceo: ceo/services/weekly-brief/SERVICE.md; playbook v1: ceo/services/weekly-brief/PLAYBOOK.md")


def test_the_definition_is_an_event(w: ServicesWorld) -> None:
    define(w, playbook=STEPS)
    kinds = [(e.kind, e.actor, e.fields) for e in w.events.events]
    assert kinds == [
        ("service.define", "root", {"owner": "ceo", "service": "weekly-brief", "version": 1, "by": "root", "amendment": False}),
        ("service.revise", "root", {"owner": "ceo", "service": "weekly-brief", "version": 1, "by": "root"}),
    ]


def test_the_short_name_of_a_direct_report_is_enough_for_a_manager(w: ServicesWorld) -> None:
    define(w, owner="eng", actor="ceo", name="eng-brief")
    assert w.catalog.service_names("ceo/eng") == ["eng-brief"]


def test_root_names_its_report_by_the_short_name_too(w: ServicesWorld) -> None:
    define(w, owner="ops", name="ops-brief")
    assert w.catalog.service_names("ops") == ["ops-brief"]


@pytest.mark.parametrize("over, text", [
    ({"name": "Bad Name"}, "a service name is lowercase letters, digits and dashes, starting with a letter (max 32), e.g. weekly-brief"),
    ({"name": "name\n"}, "a service name is lowercase letters, digits and dashes, starting with a letter (max 32), e.g. weekly-brief"),
    ({"description": " "}, "description is one line of at most 300 characters saying what the service delivers"),
    ({"description": "two\nlines"}, "description is one line of at most 300 characters saying what the service delivers"),
    ({"description": "x" * 301}, "description is one line of at most 300 characters saying what the service delivers"),
    ({"acceptance": []}, "acceptance needs at least one non-empty criterion: concrete, checkable conditions the delivery must meet"),
    ({"acceptance": ["  ", "-  "]}, "acceptance needs at least one non-empty criterion: concrete, checkable conditions the delivery must meet"),
    ({"acceptance": 7}, "acceptance must be a list of strings (or one newline-separated string)"),
    ({"acceptance": ["ok", 3]}, "acceptance must contain only strings (got 3)"),
    ({"budget": 0}, "budget is the number of runs handed down with each request: a whole number, at least 1"),
    ({"budget": True}, "budget is the number of runs handed down with each request: a whole number, at least 1"),
    ({"budget": "5"}, "budget is the number of runs handed down with each request: a whole number, at least 1"),
    ({"locked": "yes"}, "locked must be true or false"),
    ({"deliverable": {}}, "deliverable needs a description: what the owner hands back (e.g. one markdown file)"),
    ({"deliverable": "a file"}, "deliverable must be {description, format?, max_words?, path?}"),
    ({"deliverable": {"description": "d", "colour": "red"}}, "unknown key(s) in deliverable: colour. Use description, format, max_words, path"),
    ({"deliverable": {"description": "d", "max_words": 0}}, "deliverable.max_words must be a whole number of at least 1"),
    ({"deliverable": {"description": "d", "path": "relative/out.md"}}, "deliverable.path must be an absolute path (got 'relative/out.md')"),
    ({"inputs": "topic"}, "inputs must be a list of {name, description, required} (or may be empty)"),
    ({"inputs": [{"name": "Bad"}]}, "input name must be lowercase letters, digits and underscores, starting with a letter (max 32): 'Bad'"),
    ({"inputs": [{"name": "a"}, {"name": "a"}]}, "input name used twice: a"),
    ({"inputs": [{"name": "a", "required": "yes"}]}, "input a: required must be true or false"),
    ({"inputs": [{"name": "a", "size": 1}]}, "unknown key(s) in input 'a': size. Use name, description, required"),
    ({"inputs": [3]}, "each input must be {name, description, required} (got 3)"),
])
def test_what_a_first_definition_refuses_and_says(w: ServicesWorld, over: dict[str, object], text: str) -> None:
    assert refusal(w, **over) == text
    assert w.catalog.service_names("ceo") == []  # nothing was written


@pytest.mark.parametrize("missing", ["description", "acceptance", "deliverable", "budget"])
def test_a_first_definition_needs_the_four_fields_and_names_the_missing_ones(w: ServicesWorld, missing: str) -> None:
    given: dict[str, Any] = {k: v for k, v in BRIEF.items() if k != missing}
    with pytest.raises(OrgError) as e:
        w.commands.define_service("root", "ceo", "weekly-brief", **given)
    assert str(e.value) == f"a first definition of `weekly-brief` needs {missing} (it does not exist yet, so there is nothing to keep)"


def test_a_first_definition_without_anything_names_all_four(w: ServicesWorld) -> None:
    with pytest.raises(OrgError) as e:
        w.commands.define_service("root", "ceo", "weekly-brief")
    assert str(e.value).startswith("a first definition of `weekly-brief` needs description, acceptance, deliverable, budget (")


def test_amending_a_service_that_does_not_exist_is_refused(w: ServicesWorld) -> None:
    with pytest.raises(OrgError) as e:
        w.commands.define_service("root", "ceo", "weekly-brief", add_acceptance=["More"])
    assert str(e.value) == (
        "service `weekly-brief` does not exist yet: add_acceptance / remove_acceptance amend an existing contract. "
        "Give the full `acceptance` list for a first definition."
    )


def test_criteria_may_be_one_newline_separated_string_with_bullets(w: ServicesWorld) -> None:
    define(w, acceptance="- First\n* Second\n\n  Third  ")
    assert meta_of(w, CONTRACT)[0]["acceptance"] == ["First", "Second", "Third"]


def test_inputs_may_be_given_as_specs(w: ServicesWorld) -> None:
    define(w, inputs=["topic*:what it is about", "week"])
    assert meta_of(w, CONTRACT)[0]["inputs"] == [
        {"name": "topic", "description": "what it is about", "required": True},
        {"name": "week", "description": "", "required": False},
    ]


# ============================================================================================== define: who may


def test_only_the_parent_of_the_owner_defines_its_services(w: ServicesWorld) -> None:
    with pytest.raises(OrgError) as e:
        define(w, actor="ceo", owner="ceo")
    assert str(e.value) == (
        "only root, the parent of ceo, can define its services (you are ceo): the contract belongs to the client. "
        "Ask root, or define services for your own direct reports."
    )
    with pytest.raises(OrgError, match="only ceo, the parent of ceo/eng"):
        define(w, owner="ceo/eng")  # root is not eng's parent
    with pytest.raises(OrgError, match="only ceo, the parent of ceo/eng"):
        define(w, owner="ceo/eng", actor="ceo/qa")  # a sibling cannot either


def test_the_owner_has_to_exist_and_cannot_be_root(w: ServicesWorld) -> None:
    for owner in ("ghost", "root"):
        with pytest.raises(OrgError) as e:
            define(w, owner=owner)
        assert str(e.value) == f"no such agent: {owner}. A service is offered by one of your direct reports (root: a top-level agent)."


def test_the_actor_has_to_exist(w: ServicesWorld) -> None:
    with pytest.raises(OrgError, match="no such agent: ghost"):
        define(w, actor="ghost")


def test_a_name_is_unique_among_the_services_of_the_reports_of_one_client(w: ServicesWorld) -> None:
    define(w)
    with pytest.raises(OrgError) as e:
        define(w, owner="ops")
    assert str(e.value) == (
        "a service called `weekly-brief` already exists at ceo. Requests name the service only, so names "
        "must be unique among the agents that report to root: pick another name."
    )
    define(w, owner="ceo/eng", actor="ceo")  # under another client the same name is another service


# ============================================================================================== define: amending


def test_an_amendment_changes_only_what_it_names(w: ServicesWorld) -> None:
    define(w, notes="Mind the sources.")
    text = amend(w, budget=12)
    meta, body = meta_of(w, CONTRACT)
    assert (meta["version"], meta["budget"], meta["description"]) == (2, 12, BRIEF["description"])
    assert meta["acceptance"] == BRIEF["acceptance"] and meta["deliverable"] == BRIEF["deliverable"] and body.strip() == "Mind the sources."
    assert text == (
        "redefined service `weekly-brief` of ceo: contract v1 -> v2 (ceo/services/weekly-brief/SERVICE.md); the old one "
        "is kept at ceo/services/weekly-brief/history/SERVICE.v1.md. ceo was told (without waking it).\n"
        "Changed:\nbudget per request: 10 -> 12 runs\n"
        "Acceptance criteria now (2):\nC1: At most 600 words\nC2: Every factual claim has a source URL"
    )


def test_an_amendment_keeps_the_old_contract_under_its_version(w: ServicesWorld) -> None:
    define(w)
    first = w.text(CONTRACT)
    amend(w, budget=12)
    amend(w, budget=14)
    assert w.text("ceo/services/weekly-brief/history/SERVICE.v1.md") == first
    assert meta_of(w, "ceo/services/weekly-brief/history/SERVICE.v2.md")[0]["budget"] == 12
    assert meta_of(w, CONTRACT)[0]["version"] == 3


def test_an_amendment_keeps_the_creation_time_and_the_playbook(w: ServicesWorld) -> None:
    define(w, playbook=STEPS)
    created = meta_of(w, CONTRACT)[0]["created"]
    amend(w, budget=12)
    assert meta_of(w, CONTRACT)[0]["created"] == created and meta_of(w, PLAYBOOK)[1].strip() == STEPS


def test_the_owner_is_told_quietly_what_changed(w: ServicesWorld) -> None:
    define(w)
    amend(w, add_acceptance=["Cite at most five sources"], budget=12, locked=True)
    (note,) = w.d.inbox("ceo")
    assert (note.sender, note.type, note.wake, note.title) == ("runtime", "note", False, "contract of service weekly-brief changed to v2")
    assert note.body == (
        "root changed the contract of service `weekly-brief` (v1 -> v2). Read it, and follow the new criteria from the next request on:\n"
        "+ acceptance added: C3: Cite at most five sources\n"
        "budget per request: 10 -> 12 runs\n"
        "locked: false -> true (you may no longer revise the playbook)\n"
        "Acceptance criteria now:\nC1: At most 600 words\nC2: Every factual claim has a source URL\nC3: Cite at most five sources\n"
        "Contract: ceo/services/weekly-brief/SERVICE.md"
    )


def test_the_amendment_is_an_event(w: ServicesWorld) -> None:
    define(w)
    amend(w, budget=12)
    assert [(e.kind, e.fields["version"], e.fields["amendment"]) for e in w.events.events] == [("service.define", 1, False), ("service.define", 2, True)]


def test_criteria_are_added_and_removed_by_their_exact_text(w: ServicesWorld) -> None:
    define(w)
    text = amend(w, add_acceptance="Cite five sources\nNo opinions", remove_acceptance=["At most 600 words"])
    assert meta_of(w, CONTRACT)[0]["acceptance"] == ["Every factual claim has a source URL", "Cite five sources", "No opinions"]
    assert "- acceptance removed: C1: At most 600 words\n+ acceptance added: C3: Cite five sources\n+ acceptance added: C4: No opinions" in text


def test_acceptance_replaces_all_the_criteria(w: ServicesWorld) -> None:
    define(w)
    amend(w, acceptance=["Only this"])
    assert meta_of(w, CONTRACT)[0]["acceptance"] == ["Only this"]


def test_inputs_deliverable_description_and_notes_can_be_amended(w: ServicesWorld) -> None:
    define(w, notes="Old.")
    text = amend(w, inputs=[{"name": "topic", "description": "the topic", "required": True}], deliverable={"description": "a pdf"},
                 description="A brief.", notes="New.")
    assert "- input removed: week: ISO week; default the current one" in text
    assert "- input removed: topic*: what the brief is about\n" in text and "+ input added: topic*: the topic" in text
    assert 'description: "A one-page brief on the past week\'s news about a topic." -> "A brief."' in text
    assert 'deliverable: "one markdown file" (format: markdown; max_words: 600) -> "a pdf"' in text
    assert 'notes: "Old." -> "New."' in text


def test_a_change_that_changes_nothing_is_refused_with_the_current_criteria(w: ServicesWorld) -> None:
    define(w)
    with pytest.raises(OrgError) as e:
        amend(w, budget=10)
    assert str(e.value) == (
        "no change: the amendment leaves the contract of `weekly-brief` exactly as it is (v1). "
        "Current criteria:\nC1: At most 600 words\nC2: Every factual claim has a source URL"
    )
    assert meta_of(w, CONTRACT)[0]["version"] == 1 and w.d.inbox("ceo") == []


def test_reordering_the_criteria_is_a_change(w: ServicesWorld) -> None:
    define(w)
    text = amend(w, acceptance=["Every factual claim has a source URL", "At most 600 words"])
    assert "Changed:\nacceptance: order changed\n" in text


def test_acceptance_cannot_be_combined_with_add_or_remove(w: ServicesWorld) -> None:
    define(w)
    others: list[dict[str, Any]] = [{"add_acceptance": ["x"]}, {"remove_acceptance": ["At most 600 words"]}]
    for other in others:
        with pytest.raises(OrgError) as e:
            amend(w, acceptance=["y"], **other)
        assert str(e.value) == (
            "`acceptance` replaces all criteria; do not combine it with add_acceptance / remove_acceptance. Use "
            "add_acceptance / remove_acceptance alone to change single criteria."
        )


def test_removing_a_criterion_that_is_not_there_lists_the_current_ones(w: ServicesWorld) -> None:
    define(w)
    with pytest.raises(OrgError) as e:
        amend(w, remove_acceptance=["Never"])
    assert str(e.value) == (
        'remove_acceptance must be the exact text of existing criteria; not found: "Never".\n'
        "Current criteria of `weekly-brief`:\nC1: At most 600 words\nC2: Every factual claim has a source URL"
    )


def test_adding_a_criterion_that_is_there_or_twice_is_refused(w: ServicesWorld) -> None:
    define(w)
    with pytest.raises(OrgError) as e:
        amend(w, add_acceptance=["At most 600 words"])
    assert str(e.value).startswith('add_acceptance: already a criterion: "At most 600 words". Add only new criteria (to reword one, remove it and add')
    with pytest.raises(OrgError) as e:
        amend(w, add_acceptance=["New", "New"])
    assert str(e.value) == 'add_acceptance lists the same criterion twice: "New"'


def test_removing_every_criterion_is_refused(w: ServicesWorld) -> None:
    define(w)
    with pytest.raises(OrgError) as e:
        amend(w, remove_acceptance=list(BRIEF["acceptance"]))  # type: ignore[call-overload]
    assert str(e.value).startswith("that would leave `weekly-brief` without acceptance criteria: a service needs at least one.\n")


def test_the_playbook_is_not_part_of_an_amendment(w: ServicesWorld) -> None:
    define(w)
    with pytest.raises(OrgError) as e:
        amend(w, playbook=STEPS)
    assert str(e.value) == (
        "the playbook belongs to ceo, which revises it with revise_playbook: do not pass `playbook` when "
        "you redefine the contract. Leave it out; the existing playbook stays."
    )


# ============================================================================================== playbook text


def test_an_empty_playbook_is_refused_at_definition(w: ServicesWorld) -> None:
    for empty in ("", "  \n", "---\nx: 1\n---\n \n"):
        with pytest.raises(OrgError) as e:
            define(w, playbook=empty)
        assert str(e.value) == "the playbook is empty: write the workflow (steps: who does what, in which order, which check)"


def test_a_playbook_over_the_word_cap_is_refused_at_definition(w: ServicesWorld) -> None:
    w.d.configure("---\nmission: test\nplaybook_max_words: 5\n---\nrules\n")
    with pytest.raises(OrgError) as e:
        define(w, playbook="one two three four five six")
    assert str(e.value) == (
        "the playbook is 6 words; the limit is 5 (playbook_max_words). Condense it to the steps that "
        "matter and move detail into a file under your work/ directory."
    )
    define(w, playbook="one two three four five")


# ============================================================================================== retire


def test_a_service_is_retired_with_a_reason_and_its_files_are_kept(w: ServicesWorld) -> None:
    define(w, playbook=STEPS)
    text = w.commands.retire_service("root", "ceo", "weekly-brief", "  not needed any more  ")
    kept = text.split("files kept at ")[1]
    assert text == f"retired service `weekly-brief` of ceo; files kept at {kept}"
    assert kept.startswith("ceo/services/.retired/weekly-brief-") and w.text(f"{kept}/SERVICE.md") is not None
    assert w.text(CONTRACT) is None and w.catalog.service_names("ceo") == []
    (note,) = w.d.inbox("ceo")
    assert (note.type, note.wake, note.title) == ("note", False, "service weekly-brief retired")
    assert note.body == (
        "root retired the service `weekly-brief`: not needed any more. It cannot be requested any more; its files are kept at "
        f"{kept}."
    )
    assert w.events.events[-1].kind == "service.retire" and w.events.events[-1].fields == {"owner": "ceo", "service": "weekly-brief", "by": "root"}


def test_only_the_parent_retires_and_only_what_exists(w: ServicesWorld) -> None:
    define(w)
    for actor, owner in (("ceo", "ceo"), ("root", "ceo/eng"), ("root", "root"), ("root", "ghost")):
        with pytest.raises(OrgError) as e:
            w.commands.retire_service(actor, owner, "weekly-brief", "why")
        assert "you can only retire services of your direct reports (root: top-level agents)" in str(e.value) or "no such agent" in str(e.value)
    with pytest.raises(OrgError) as e:
        w.commands.retire_service("root", "ceo", "nope", "why")
    assert str(e.value) == "ceo offers no service called `nope`. Its services: weekly-brief"
    with pytest.raises(OrgError) as e:
        w.commands.retire_service("root", "ops", "nope", "why")
    assert str(e.value) == "ops offers no service called `nope`. Its services: none"


def test_a_retirement_needs_a_reason(w: ServicesWorld) -> None:
    define(w)
    with pytest.raises(OrgError) as e:
        w.commands.retire_service("root", "ceo", "weekly-brief", "  ")
    assert str(e.value) == "say why the service is retired (reason)"
    assert w.catalog.service_names("ceo") == ["weekly-brief"]


def test_a_retired_service_can_be_defined_again_as_a_new_one(w: ServicesWorld) -> None:
    define(w)
    w.commands.retire_service("root", "ceo", "weekly-brief", "redo")
    assert define(w).startswith("defined service `weekly-brief` (contract v1)")


# ============================================================================================== revise the playbook


def test_the_owner_writes_the_first_playbook(w: ServicesWorld) -> None:
    define(w)
    assert w.commands.revise_playbook("ceo", "weekly-brief", STEPS, "  first draft  ") == 1
    meta, body = meta_of(w, PLAYBOOK)
    assert (meta["version"], meta["by"], meta["reason"], meta["service"]) == (1, "ceo", "first draft", "weekly-brief") and body.strip() == STEPS
    (note,) = w.d.inbox("root")
    assert (note.type, note.wake, note.title) == ("note", False, "playbook of weekly-brief revised to v1")
    assert note.body == "ceo revised the playbook of service `weekly-brief` to v1.\nReason: first draft\nFile: ceo/services/weekly-brief/PLAYBOOK.md"
    assert w.events.events[-1].kind == "service.revise" and w.events.events[-1].fields["version"] == 1


def test_each_revision_keeps_the_old_version(w: ServicesWorld) -> None:
    define(w)
    w.commands.revise_playbook("ceo", "weekly-brief", STEPS, "one")
    first = w.text(PLAYBOOK)
    assert w.commands.revise_playbook("ceo", "weekly-brief", STEPS + "\n4. Publish.", "two") == 2
    assert w.text("ceo/services/weekly-brief/history/PLAYBOOK.v1.md") == first
    assert meta_of(w, PLAYBOOK)[0]["version"] == 2


def test_a_frontmatter_in_the_content_is_stripped(w: ServicesWorld) -> None:
    define(w)
    w.commands.revise_playbook("ceo", "weekly-brief", f"---\nversion: 99\n---\n{STEPS}", "framed")
    assert meta_of(w, PLAYBOOK)[0]["version"] == 1 and meta_of(w, PLAYBOOK)[1].strip() == STEPS


def test_only_the_owner_revises_its_playbook(w: ServicesWorld) -> None:
    define(w)
    for actor, name in (("root", "weekly-brief"), ("ops", "weekly-brief"), ("ceo", "nope"), ("ceo", "Bad Name")):
        with pytest.raises(OrgError) as e:
            w.commands.revise_playbook(actor, name, STEPS, "why")
        mine = "weekly-brief" if actor == "ceo" else "none"
        assert str(e.value) == (
            f"you do not own a service called `{name}`. Services you own: {mine}. Only the owner revises a "
            "playbook, and services are defined for you by your parent (define_service)."
        )


def test_a_locked_contract_forbids_the_revision(w: ServicesWorld) -> None:
    define(w, locked=True)
    with pytest.raises(OrgError) as e:
        w.commands.revise_playbook("ceo", "weekly-brief", STEPS, "why")
    assert str(e.value) == (
        "the contract of `weekly-brief` is locked by root: you may not revise its playbook. Follow the current "
        "one, and if you think it must change, tell root (`send`)."
    )


def test_a_manager_is_told_by_its_report_that_it_revised(w: ServicesWorld) -> None:
    define(w, owner="ceo/eng", actor="ceo", name="eng-brief")
    w.commands.revise_playbook("ceo/eng", "eng-brief", STEPS, "why")
    assert [m.title for m in w.d.inbox("ceo")] == ["playbook of eng-brief revised to v1"]


@pytest.mark.parametrize("reason", ["", "   ", "x" * 401])
def test_a_revision_needs_a_reason_of_one_to_four_hundred_characters(w: ServicesWorld, reason: str) -> None:
    define(w)
    with pytest.raises(OrgError) as e:
        w.commands.revise_playbook("ceo", "weekly-brief", STEPS, reason)
    assert str(e.value) == (
        "reason is 1-400 characters: say what changed and which cases it rests on (case ids from the "
        "evidence), so the next revision can judge it"
    )


def test_a_revision_must_say_something_and_something_new(w: ServicesWorld) -> None:
    define(w)
    with pytest.raises(OrgError, match="the playbook is empty"):
        w.commands.revise_playbook("ceo", "weekly-brief", " ", "why")
    w.commands.revise_playbook("ceo", "weekly-brief", STEPS, "one")
    with pytest.raises(OrgError) as e:
        w.commands.revise_playbook("ceo", "weekly-brief", f"\n{STEPS}\n", "again")
    assert str(e.value) == (
        "no change: this is identical to playbook v1. Revise only when the evidence calls for a different way of working."
    )


def test_the_word_cap_comes_from_the_settings(w: ServicesWorld) -> None:
    define(w)
    w.d.configure("---\nmission: test\nplaybook_max_words: 3\n---\nrules\n")
    with pytest.raises(OrgError, match="the playbook is 4 words; the limit is 3 \\(playbook_max_words\\)"):
        w.commands.revise_playbook("ceo", "weekly-brief", "a b c d", "why")


@pytest.mark.parametrize("setting", ["abc", "0", "-4", "null"])
def test_a_malformed_cap_means_one_thousand_words(w: ServicesWorld, setting: str) -> None:
    define(w)
    w.d.configure(f"---\nmission: test\nplaybook_max_words: {setting}\n---\nrules\n")
    with pytest.raises(OrgError, match="the playbook is 1001 words; the limit is 1000"):
        w.commands.revise_playbook("ceo", "weekly-brief", " ".join(["w"] * 1001), "why")
    w.commands.revise_playbook("ceo", "weekly-brief", " ".join(["w"] * 1000), "why")


# ============================================================================================== request


def test_a_request_is_a_task_built_from_the_contract(w: ServicesWorld) -> None:
    define(w, playbook=STEPS)
    task = request(w, "ai", note="  Be quick.  ")
    assert (task.sender, task.to, task.type, task.budget) == ("root", "ceo", "task", 10)
    assert (task.service, task.contract, task.playbook, task.title) == ("weekly-brief", 1, 1, "weekly-brief: ai")
    assert task.body == (
        "## Goal\nDeliver the service `weekly-brief`: A one-page brief on the past week's news about a topic.\n\n"
        "## Request\n- topic: ai\n\n"
        "## Acceptance criteria\n- C1: At most 600 words\n- C2: Every factual claim has a source URL\n\n"
        "## Deliverable\none markdown file (format: markdown; at most 600 words)\n\n"
        "## Note from the requester\nBe quick."
    )
    assert [m.id for m in w.d.inbox("ceo")] == [task.id]


def test_a_request_without_a_playbook_carries_version_zero(w: ServicesWorld) -> None:
    define(w)
    assert request(w).playbook == 0


def test_the_inputs_are_listed_in_the_order_of_the_contract_and_the_empty_ones_dropped(w: ServicesWorld) -> None:
    define(w)
    task = w.commands.request("root", "weekly-brief", {"week": " 2026-W10 ", "topic": "ai\nsecond line"})
    assert "## Request\n- topic: ai\n  second line\n- week: 2026-W10\n\n" in task.body
    assert task.title == "weekly-brief: ai second line"


def test_a_request_without_any_input_says_so(w: ServicesWorld) -> None:
    define(w, inputs=[{"name": "topic", "description": "t", "required": False}])
    task = w.commands.request("root", "weekly-brief", None)
    assert "## Request\n(no inputs)\n\n" in task.body and task.title == "weekly-brief"


def test_the_deliverable_is_described_with_its_format_size_and_path(w: ServicesWorld) -> None:
    define(w, deliverable={"description": "a report", "format": "pdf", "max_words": 90, "path": "/data/out.pdf"})
    assert "## Deliverable\na report (format: pdf; at most 90 words; path: /data/out.pdf)" in request(w).body
    amend(w, deliverable={"description": "a note"})
    assert request(w).body.endswith("## Deliverable\na note")


def test_the_budget_is_the_contracts_unless_the_caller_names_one(w: ServicesWorld) -> None:
    define(w)
    assert request(w).budget == 10 and request(w, budget=4).budget == 4


@pytest.mark.parametrize("budget", [0, -1, True])
def test_a_request_needs_a_budget_of_at_least_one(w: ServicesWorld, budget: int) -> None:
    define(w)
    with pytest.raises(OrgError) as e:
        request(w, budget=budget)
    assert str(e.value) == "a request needs a budget of at least 1 run"


def test_extra_acceptance_criteria_come_after_the_contracts(w: ServicesWorld) -> None:
    define(w)
    task = request(w, extra_acceptance=["Use bullet points", "- Mention the date"])
    assert "## Acceptance criteria\n- C1: At most 600 words\n- C2: Every factual claim has a source URL\n- this request only: Use bullet points\n- this request only: Mention the date\n\n" in task.body


def test_a_title_the_caller_gives_is_kept(w: ServicesWorld) -> None:
    define(w)
    assert request(w, title="  My title ").title == "My title"


def test_a_long_default_title_is_cut_to_eighty_characters(w: ServicesWorld) -> None:
    define(w)
    assert len(request(w, "x" * 200).title) == 80


def test_an_unknown_service_lists_the_ones_that_can_be_requested(w: ServicesWorld) -> None:
    define(w)
    with pytest.raises(OrgError) as e:
        w.commands.request("root", "nope", {})
    assert str(e.value) == (
        "no service `nope` among your direct reports. Services you can request: weekly-brief (offered by ceo). "
        "A parent defines one with define_service."
    )
    with pytest.raises(OrgError) as e:
        w.commands.request("ceo/eng", "weekly-brief", {})
    assert str(e.value).endswith("Services you can request: none. A parent defines one with define_service.")


def test_only_the_services_of_direct_reports_can_be_requested(w: ServicesWorld) -> None:
    define(w)
    with pytest.raises(OrgError, match="no service `weekly-brief` among your direct reports"):
        w.commands.request("ceo", "weekly-brief", {"topic": "ai"})  # the owner itself cannot


def test_unknown_and_missing_inputs_are_refused_with_the_known_ones(w: ServicesWorld) -> None:
    define(w)
    with pytest.raises(OrgError) as e:
        w.commands.request("root", "weekly-brief", {"topic": "ai", "colour": "red", "size": "1"})
    assert str(e.value) == "unknown input(s) for `weekly-brief`: colour, size. Its inputs: topic, week."
    for given in ({}, {"topic": "  "}, {"topic": None}, {"week": "1"}):
        with pytest.raises(OrgError) as e:
            w.commands.request("root", "weekly-brief", given)
        assert str(e.value) == "missing required input(s) for `weekly-brief`: topic. Pass them in `inputs`."


def test_a_service_without_inputs_refuses_any(w: ServicesWorld) -> None:
    define(w, inputs=[])
    with pytest.raises(OrgError) as e:
        w.commands.request("root", "weekly-brief", {"topic": "ai"})
    assert str(e.value) == "unknown input(s) for `weekly-brief`: topic. Its inputs: none."


def test_a_manager_asks_its_report_with_the_runs_it_has(w: ServicesWorld) -> None:
    define(w, owner="ceo/eng", actor="ceo", name="eng-brief", inputs=[], budget=3)
    grant(w, "ceo", 8)
    task = w.commands.request("ceo", "eng-brief", {})
    assert (task.sender, task.to, task.budget) == ("ceo", "ceo/eng", 3)
    assert w.d.query.budget("ceo") == 5


def test_the_message_rules_apply_to_a_request(w: ServicesWorld) -> None:
    define(w, owner="ceo/eng", actor="ceo", name="eng-brief", inputs=[], budget=3)
    with pytest.raises(OrgError):  # ceo has no runs to hand down
        w.commands.request("ceo", "eng-brief", {})


# ------------------------------------------------------------------------------ revises


def test_a_request_can_be_sent_back_for_rework(w: ServicesWorld) -> None:
    define(w)
    first = request(w)
    again = request(w, revises=first.id, budget=3)
    assert again.revises == first.id and (again.service, again.contract) == ("weekly-brief", 1)


def test_request_forwards_source_onto_the_rework(w: ServicesWorld) -> None:
    define(w)
    first = request(w)
    assert first.source is None  # a fresh request is the user's ask: not stamped
    assert request(w, revises=first.id).source == "relayed"  # root's own reading, unless it says the user asked
    assert request(w, revises=first.id, source="human").source == "human"
    assert request(w, revises=first.id, source="relayed").source == "relayed"


@pytest.mark.parametrize("what", ["a task of another service", "nothing", "a note", "a request to someone else"])
def test_only_an_earlier_request_for_the_same_service_to_the_same_owner_can_be_revised(w: ServicesWorld, what: str) -> None:
    define(w)
    define(w, owner="ops", name="ops-brief", inputs=[])
    other = w.commands.request("root", "ops-brief", {})
    plain = w.d.post(Message(sender="root", to="ceo", type="task", body="plain", title="Plain", budget=2))
    note = w.d.post(Message(sender="root", to="ceo", type="note", body="n"))
    target = {"a task of another service": other.id, "nothing": "20200101T000000000001-root-0000", "a note": note.id, "a request to someone else": plain.id}[what]
    with pytest.raises(OrgError) as e:
        request(w, revises=target)
    assert str(e.value) == f"revises must be the id of an earlier request for `weekly-brief` that you sent to ceo: {target}"


# ============================================================================================== feedback


def delivered(w: ServicesWorld, status: str = "done") -> Message:
    define(w)
    task = request(w)
    answer(w, task, status)
    return task


def test_an_accept_is_a_quiet_note_to_the_owner_with_the_fixed_header(w: ServicesWorld) -> None:
    task = delivered(w)
    note = w.commands.feedback("root", task.id, "accept")
    assert (note.sender, note.to, note.type, note.wake, note.reply_to, note.feedback) == ("root", "ceo", "note", False, task.id, "accept")
    assert note.title == 'feedback on "weekly-brief: ai": accept'
    assert note.body == FEEDBACK_HEADER + "\n\naccepted"
    assert FEEDBACK_HEADER.startswith("Client feedback for reflection only: it does not change this task's acceptance criteria or outcome;")


def test_a_rejection_carries_the_clients_words(w: ServicesWorld) -> None:
    task = delivered(w)
    note = w.commands.feedback("root", task.id, "reject", "  No week-over-week changes.  ")
    assert note.feedback == "reject" and note.body == FEEDBACK_HEADER + "\n\nNo week-over-week changes."


def test_every_verdict_is_kept_the_latest_does_not_replace_the_earlier(w: ServicesWorld) -> None:
    task = delivered(w)
    w.commands.feedback("root", task.id, "reject", "Too long.")
    w.commands.feedback("root", task.id, "accept")
    assert [m.feedback for m in w.d.inbox("ceo") if m.type == "note"] == ["reject", "accept"]


def test_feedback_can_be_given_on_a_rework_of_the_case(w: ServicesWorld) -> None:
    first = delivered(w)
    second = request(w, revises=first.id)
    answer(w, second)
    assert w.commands.feedback("root", second.id, "accept").reply_to == second.id


def test_a_rejection_needs_the_words(w: ServicesWorld) -> None:
    task = delivered(w)
    for note in ("", "   "):
        with pytest.raises(OrgError) as e:
            w.commands.feedback("root", task.id, "reject", note)
        assert str(e.value) == "a rejection needs a note: say what was wrong, so the owner can change its playbook"


def test_the_verdict_is_accept_or_reject(w: ServicesWorld) -> None:
    task = delivered(w)
    with pytest.raises(OrgError) as e:
        w.commands.feedback("root", task.id, "maybe")
    assert str(e.value) == "verdict must be one of ('accept', 'reject')"


def test_the_note_has_a_limit(w: ServicesWorld) -> None:
    task = delivered(w)
    with pytest.raises(OrgError) as e:
        w.commands.feedback("root", task.id, "reject", "x" * 1001)
    assert str(e.value) == "the note is 1001 characters; the limit is 1000. Keep it to what was wrong or good."
    w.commands.feedback("root", task.id, "reject", "x" * 1000)


def test_feedback_needs_a_result(w: ServicesWorld) -> None:
    define(w)
    task = request(w)
    with pytest.raises(OrgError) as e:
        w.commands.feedback("root", task.id, "accept")
    assert str(e.value) == f"task {task.id} has no result yet: wait for the result, then give feedback."


def test_a_blocked_result_is_a_result(w: ServicesWorld) -> None:
    task = delivered(w, "blocked")
    assert w.commands.feedback("root", task.id, "reject", "Blocked for no reason.").feedback == "reject"


def test_feedback_is_for_requests_the_actor_sent(w: ServicesWorld) -> None:
    task = delivered(w)
    plain = w.d.post(Message(sender="root", to="ceo", type="task", body="plain", title="Plain", budget=2))
    for target in ("nope", plain.id):
        with pytest.raises(OrgError) as e:
            w.commands.feedback("root", target, "accept")
        assert str(e.value) == (
            f"{target} is not a service request you sent. Feedback is for requests made with `request`. Yours: {task.id}"
        )
    with pytest.raises(OrgError) as e:
        w.commands.feedback("ceo", task.id, "accept")
    assert str(e.value).endswith("Yours: none")
