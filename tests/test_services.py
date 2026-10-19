"""Services (a standing task with a contract and a playbook) and reflection (lessons -> digest -> revise_playbook)."""

import asyncio
import time

import pytest
import yaml

from testkit.services_world import (  # noqa: F401  (svc is a fixture)
    BRIEF, ENG, call, cli, contract_meta, define, deliver, fails, playbook_meta, request, svc, work,
)

from orgmcp import services
from orgmcp.core import ROOT, Message, OrgError, split_frontmatter
from orgmcp.progress import progress
from orgmcp.server import build_server

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
    assert services.read_playbook(org, "ceo", "weekly-brief").version == 1


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
    assert "- acceptance removed: At most 600 words" in note.body and "+ acceptance added: At most 500 words" in note.body
    assert "budget per request: 10 -> 12 runs" in note.body and "locked: false -> true" in note.body
    assert "Every factual claim" not in note.body  # unchanged criteria are not repeated


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


# --------------------------------------------------------------------------------------------- request


def test_request_builds_a_task_from_the_contract(svc):
    org = svc
    msg = org.request(ROOT, "weekly-brief", {"topic": " ai chips ", "week": 42}, note="Short please.",
                      extra_acceptance=["Mention one risk"])
    assert isinstance(msg, Message) and msg.to == "ceo" and msg.type == "task"
    assert (msg.service, msg.contract, msg.playbook, msg.budget) == ("weekly-brief", 1, 0, 10)
    assert msg.title == "weekly-brief: ai chips"
    assert msg.body == (
        "## Goal\nDeliver the service `weekly-brief`: A one-page brief on the past week's news about a topic.\n\n"
        "## Request\n- topic: ai chips\n- week: 42\n\n"
        "## Acceptance criteria\n- At most 600 words\n- Every factual claim has a source URL\n- Mention one risk\n\n"
        "## Deliverable\none markdown file (format: markdown; at most 600 words)\n\n"
        "## Note from the requester\nShort please."
    )
    stored = Message.load(org.dir("ceo") / "inbox" / f"{msg.id}.md")
    assert (stored.service, stored.contract, stored.playbook) == ("weekly-brief", 1, 0)
    head = stored.render().splitlines()[1]
    assert "service: weekly-brief (contract v1, playbook v0)" in head
    meta = split_frontmatter((org.dir("ceo") / "inbox" / f"{msg.id}.md").read_text())[0]
    assert meta["service"] == "weekly-brief" and meta["contract"] == 1 and meta["playbook"] == 0
    assert [m.id for m in org.outstanding(ROOT)] == [msg.id]


def test_request_records_the_current_playbook_version_and_optional_sections_are_absent(org):
    define(org, playbook="Steps.", deliverable={"description": "a file"}, inputs=[])
    msg = org.request(ROOT, "weekly-brief", None)
    assert msg.playbook == 1 and msg.title == "weekly-brief"
    assert "## Note from the requester" not in msg.body and "(no inputs)" in msg.body
    assert "## Deliverable\na file\n" in msg.body + "\n"


def test_request_checks_inputs(svc):
    org = svc
    with pytest.raises(OrgError, match="missing required input.*topic"):
        org.request(ROOT, "weekly-brief", {"week": "3"})
    with pytest.raises(OrgError, match="missing required input.*topic"):
        org.request(ROOT, "weekly-brief", {"topic": "  "})
    with pytest.raises(OrgError, match=r"unknown input\(s\).*colour.*Its inputs: topic, week"):
        org.request(ROOT, "weekly-brief", {"topic": "x", "colour": "red"})
    msg = org.request(ROOT, "weekly-brief", {"topic": "x", "week": ""})  # an empty optional input is simply absent
    assert "- week" not in msg.body and "- topic: x" in msg.body


def test_request_names_the_available_services_when_it_is_unknown(svc):
    with pytest.raises(OrgError, match=r"Services you can request: weekly-brief \(offered by ceo\)"):
        svc.request(ROOT, "nope", {})
    with pytest.raises(OrgError, match="Services you can request: none"):
        svc.request("ceo", "weekly-brief", {"topic": "x"})  # ceo has no reports that offer anything


def test_request_resolves_among_direct_reports_only(org):
    define(org, owner=ENG, actor="ceo", name="eng-brief", budget=4)
    with pytest.raises(OrgError, match="no service `eng-brief`"):
        org.request(ROOT, "eng-brief", {"topic": "x"})  # root's direct reports are top-level agents
    org.delegate(ROOT, "ceo", "Project", "g", "c", budget=10)
    msg = org.request("ceo", "eng-brief", {"topic": "x"})
    assert msg.to == ENG and msg.service == "eng-brief"


def test_request_budget_defaults_to_the_contract_and_follows_the_reserve_rule(org):
    define(org, owner=ENG, actor="ceo", name="eng-brief", budget=4)
    org.delegate(ROOT, "ceo", "Project", "g", "c", budget=5)
    work(org, "ceo")  # 1 run used: 4 left
    # 4 left, 1 reserved for the result of this request: 3 can be handed down, the contract wants 4
    with pytest.raises(OrgError, match="not enough budget.*at most 3"):
        org.request("ceo", "eng-brief", {"topic": "x"})
    msg = org.request("ceo", "eng-brief", {"topic": "x"}, budget=3)
    assert msg.budget == 3 and org.budget("ceo") == 1
    define(org, name="plain", description="d")  # root has no limit: the contract budget is used as is
    root_msg = org.request(ROOT, "plain", {"topic": "y"})
    assert root_msg.budget == 10
    with pytest.raises(OrgError, match="at least 1"):
        org.request(ROOT, "plain", {"topic": "y"}, budget=0)


def test_request_revises_must_be_an_earlier_request_of_the_same_service(svc):
    org = svc
    first = request(org)
    plain = org.delegate(ROOT, "ceo", "Other", "g", "c", budget=2)
    with pytest.raises(OrgError, match="revises must be"):
        request(org, revises=plain.id)  # not a request of this service
    with pytest.raises(OrgError, match="revises must be"):
        request(org, revises="nope")
    rework = request(org, revises=first.id)
    assert rework.revises == first.id and rework.service == "weekly-brief"


def test_delegate_revises_a_service_task_and_stays_in_the_case(org):
    define(org, playbook="v1 steps.")
    first = request(org)
    deliver(org, "ceo", first)
    rework = org.delegate(ROOT, "ceo", "Fix it", "Add sources", "Every claim has a URL", budget=3, revises=first.id)
    assert (rework.service, rework.contract, rework.playbook, rework.revises) == ("weekly-brief", 1, 1, first.id)
    plain = org.delegate(ROOT, "ceo", "Plain", "g", "c", budget=2)
    assert plain.service is None and plain.contract is None and plain.playbook is None
    plain_rework = org.delegate(ROOT, "ceo", "Plain 2", "g", "c", budget=2, revises=plain.id)
    assert plain_rework.service is None
    (case,) = services.cases(org, "ceo", "weekly-brief")
    assert [t.id for t in case.tasks] == [first.id, rework.id] and case.reworks == 1


def test_old_messages_without_service_fields_parse_as_before(org):
    msg = org.delegate(ROOT, "ceo", "Plain", "g", "c", budget=2)
    stored = Message.load(org.dir("ceo") / "inbox" / f"{msg.id}.md")
    assert stored.service is stored.contract is stored.playbook is stored.feedback is None
    assert "service" not in stored.meta() and "feedback" not in stored.meta()
    assert "service:" not in stored.render()


# ---------------------------------------------------------------------------------------------- report


def test_report_on_a_service_request_requires_lessons(svc):
    org = svc
    task = request(org)
    work(org, "ceo")
    for status in ("done", "failed", "blocked"):
        with pytest.raises(OrgError, match="request for service `weekly-brief`: pass `lessons`"):
            org.report("ceo", task.id, status, "Delivered.")
        with pytest.raises(OrgError, match="pass `lessons`"):
            org.report("ceo", task.id, status, "Delivered.", lessons="   ")
    with pytest.raises(OrgError, match="limit is 800"):
        org.report("ceo", task.id, "done", "Delivered.", lessons="x" * 801)
    blocked = org.report("ceo", task.id, "blocked", "Waiting for sources.", lessons="Sources were not provided.")
    assert services.lessons_of(blocked) == "Sources were not provided."  # required for blocked too
    org.write("ceo", "ceo/work/brief.md", "# Brief")
    final = org.report("ceo", task.id, "done", "Delivered.", ["ceo/work/brief.md"], lessons="Search first.\nTwo runs.")
    assert final.body.index("## Summary") < final.body.index("## Lessons") < final.body.index("## Artifacts")
    assert "## Lessons\nSearch first.\nTwo runs." in final.body
    assert services.lessons_of(final) == "Search first.\nTwo runs."


def test_lessons_are_optional_for_plain_tasks_and_kept_when_given(org):
    task = org.delegate(ROOT, "ceo", "Plain", "g", "c", budget=2)
    work(org, "ceo")
    res = org.report("ceo", task.id, "done", "Done.", lessons="Anyway.")
    assert "## Lessons\nAnyway." in res.body
    other = org.delegate(ROOT, "ceo", "Plain 2", "g", "c", budget=2)
    assert "## Lessons" not in org.report("ceo", other.id, "done", "Done.").body


# ----------------------------------------------------------------------------------- revise_playbook


def test_revise_playbook_versions_archives_and_tells_the_client(svc):
    org = svc
    assert org.revise_playbook("ceo", "weekly-brief", "---\nversion: 99\n---\n## Steps\n1. Search.", "first draft") == 1
    meta, body = playbook_meta(org)
    assert meta["version"] == 1 and meta["by"] == "ceo" and meta["reason"] == "first draft" and meta["service"] == "weekly-brief"
    assert body.strip() == "## Steps\n1. Search."  # the caller's frontmatter was stripped, the runtime's is used
    assert org.revise_playbook("ceo", "weekly-brief", "## Steps\n1. Search.\n2. Cite.", "Cases A and B lacked sources") == 2
    hist = org.dir("ceo") / "services" / "weekly-brief" / "history" / "PLAYBOOK.v1.md"
    assert "1. Search." in hist.read_text() and "2. Cite." not in hist.read_text()
    assert playbook_meta(org)[0]["version"] == 2
    notes = org.messages(ROOT, "inbox")
    assert [n.title for n in notes] == [
        "playbook of weekly-brief revised to v1", "playbook of weekly-brief revised to v2",
    ]
    assert all(n.wake is False and n.sender == "runtime" for n in notes)
    assert "Cases A and B lacked sources" in notes[1].body and "ceo/services/weekly-brief/PLAYBOOK.md" in notes[1].body
    assert org.unread(ROOT) == 0


def test_the_client_of_a_nested_owner_gets_the_note_without_being_woken(org):
    define(org, owner=ENG, actor="ceo", name="eng-brief")
    org.revise_playbook(ENG, "eng-brief", "Steps.", "first")
    (note,) = org.messages("ceo", "inbox")
    assert note.wake is False and org.unread("ceo") == 0 and "revised to v1" in note.title


def test_only_the_owner_revises_and_only_unlocked_services(svc):
    org = svc
    with pytest.raises(OrgError, match="do not own a service called `weekly-brief`.*none"):
        org.revise_playbook(ENG, "weekly-brief", "Steps.", "r")
    with pytest.raises(OrgError, match="do not own"):
        org.revise_playbook(ROOT, "weekly-brief", "Steps.", "r")
    with pytest.raises(OrgError, match="do not own a service called `nope`.*weekly-brief"):
        org.revise_playbook("ceo", "nope", "Steps.", "r")
    define(org, locked=True)
    with pytest.raises(OrgError, match="locked by root"):
        org.revise_playbook("ceo", "weekly-brief", "Steps.", "r")
    define(org, locked=False)
    assert org.revise_playbook("ceo", "weekly-brief", "Steps.", "r") == 1


def test_revise_playbook_checks_content_reason_and_no_op(svc):
    org = svc
    with pytest.raises(OrgError, match="playbook is empty"):
        org.revise_playbook("ceo", "weekly-brief", "---\nx: 1\n---\n", "r")
    with pytest.raises(OrgError, match="reason is 1-400"):
        org.revise_playbook("ceo", "weekly-brief", "Steps.", " ")
    with pytest.raises(OrgError, match="reason is 1-400"):
        org.revise_playbook("ceo", "weekly-brief", "Steps.", "r" * 401)
    with pytest.raises(OrgError, match="the limit is 1000"):
        org.revise_playbook("ceo", "weekly-brief", "word " * 1001, "r")
    org.revise_playbook("ceo", "weekly-brief", "word " * 1000, "at the cap")
    with pytest.raises(OrgError, match="no change: this is identical to playbook v1"):
        org.revise_playbook("ceo", "weekly-brief", "---\nanything: 1\n---\n" + "word " * 1000, "again")
    assert playbook_meta(org)[0]["version"] == 1


def test_the_word_cap_is_configurable(svc):
    org = svc
    text = (org.root / "ORG.md").read_text().replace("playbook_max_words: 1000", "playbook_max_words: 5")
    (org.root / "ORG.md").write_text(text)
    with pytest.raises(OrgError, match="the limit is 5"):
        org.revise_playbook("ceo", "weekly-brief", "one two three four five six", "r")


# ----------------------------------------------------------------------------------------- feedback


def test_feedback_is_a_quiet_note_from_the_requester(svc):
    org = svc
    task = request(org)
    with pytest.raises(OrgError, match="wait for the result"):
        org.feedback(ROOT, task.id, "accept")
    deliver(org, "ceo", task)
    with pytest.raises(OrgError, match="verdict must be"):
        org.feedback(ROOT, task.id, "meh")
    with pytest.raises(OrgError, match="rejection needs a note"):
        org.feedback(ROOT, task.id, "reject")
    with pytest.raises(OrgError, match="limit is 1000"):
        org.feedback(ROOT, task.id, "reject", "x" * 1001)
    ceo_unread = org.unread("ceo")
    note = org.feedback(ROOT, task.id, "reject", "No week-over-week changes.")
    assert (note.type, note.to, note.reply_to, note.feedback, note.wake) == ("note", "ceo", task.id, "reject", False)
    assert note.title == f'feedback on "{task.title}": reject'
    assert note.body == services.FEEDBACK_HEADER + "\n\nNo week-over-week changes."
    assert org.unread("ceo") == ceo_unread and note.budget == 0
    assert "feedback: reject" in Message.load(org.dir("ceo") / "inbox" / f"{note.id}.md").render()
    assert org.feedback(ROOT, task.id, "accept").body == services.FEEDBACK_HEADER + "\n\naccepted"


def test_only_the_requester_gives_feedback_on_a_service_request(org):
    define(org, owner=ENG, actor="ceo", name="eng-brief")
    org.delegate(ROOT, "ceo", "Project", "g", "c", budget=10)
    task = org.request("ceo", "eng-brief", {"topic": "x"}, budget=3)
    deliver(org, ENG, task)
    with pytest.raises(OrgError, match="not a service request you sent"):
        org.feedback(ROOT, task.id, "accept")  # root did not send it
    with pytest.raises(OrgError, match="not a service request you sent"):
        org.feedback("ceo", "nope", "accept")
    plain = org.delegate(ROOT, "ceo", "Plain", "g", "c", budget=2)
    with pytest.raises(OrgError, match="not a service request you sent"):
        org.feedback(ROOT, plain.id, "accept")  # not a service task
    assert org.feedback("ceo", task.id, "accept").to == ENG


def test_feedback_on_a_rework_belongs_to_the_case_and_the_latest_is_the_final_verdict(svc):
    org = svc
    first = request(org)
    deliver(org, "ceo", first)
    org.feedback(ROOT, first.id, "reject", "Too long.")
    rework = org.delegate(ROOT, "ceo", "Shorten", "g", "c", budget=3, revises=first.id)
    deliver(org, "ceo", rework)
    (case,) = services.cases(org, "ceo", "weekly-brief")
    assert case.verdict == "reject"  # feedback on the first task counts for the case
    time.sleep(0.002)
    org.feedback(ROOT, rework.id, "accept")
    (case,) = services.cases(org, "ceo", "weekly-brief")
    assert case.verdict == "accept" and case.feedback.reply_to == rework.id
    assert services.summarize([case]).accept == 1 and services.summarize([case]).reject == 0


# ------------------------------------------------------------------------- cases, stats, digest


def test_cases_group_rework_chains_and_derive_runs_budget_and_lessons(svc):
    org = svc
    first = request(org, "ai")
    deliver(org, "ceo", first, runs=2, lessons="First pass was thin.")
    rework = request(org, "ai", revises=first.id, budget=4)
    deliver(org, "ceo", rework, runs=1, lessons="Added sources.")
    second = request(org, "chips")
    work(org, "ceo", 1)
    one, two = services.cases(org, "ceo", "weekly-brief")
    assert one.id == first.id and [t.id for t in one.tasks] == [first.id, rework.id]
    assert (one.state, one.reworks, one.playbook, one.budget, one.runs) == ("done", 1, 0, 14, 3)
    assert one.lessons == ["First pass was thin.", "Added sources."] and one.result.reply_to == rework.id
    assert one.finished is not None and one.feedback is None
    assert (two.id, two.state, two.reworks, two.finished) == (second.id, "open", 0, None)
    assert two.runs == 1
    assert one.title == "weekly-brief: ai"


def test_a_blocked_case_is_not_finished_and_a_failed_one_counts_as_failed(svc):
    org = svc
    a, b = request(org, "a"), request(org, "b")
    work(org, "ceo")
    org.report("ceo", a.id, "blocked", "Need data.", lessons="Input was missing.")
    org.report("ceo", b.id, "failed", "Could not.", lessons="Source was down.")
    org.end_run("ceo", ok=True)
    blocked, failed = services.cases(org, "ceo", "weekly-brief")
    assert (blocked.state, blocked.finished) == ("blocked", None) and failed.state == "failed"
    stats = services.summarize([blocked, failed])
    assert (stats.requests, stats.done, stats.failed, stats.open) == (2, 0, 1, 1)


def test_stats_per_playbook_version_and_the_one_line_summary(svc):
    org = svc
    a = request(org, "a")
    deliver(org, "ceo", a, runs=2)
    org.feedback(ROOT, a.id, "reject", "Bad.")
    org.revise_playbook("ceo", "weekly-brief", "Better steps.", "case a rejected")
    b = request(org, "b")
    deliver(org, "ceo", b, runs=1)
    org.feedback(ROOT, b.id, "accept")
    c = request(org, "c")
    deliver(org, "ceo", c, status="failed", runs=3)
    all_cases = services.cases(org, "ceo", "weekly-brief")
    per = services.stats_by_version(all_cases)
    assert sorted(per) == [0, 1]
    v0, v1 = per[0], per[1]
    assert (v0.requests, v0.done, v0.reject, v0.avg_runs) == (1, 1, 1, 2.0)
    assert (v1.requests, v1.done, v1.failed, v1.accept, v1.avg_runs) == (2, 1, 1, 1, 2.0)
    assert v1.line() == "2 request(s): 1 done, 1 failed, 0 open; 0 reworked; avg 2 runs; feedback 1 accept, 0 reject"
    total = services.summarize(all_cases)
    assert total.requests == 3 and total.reworked == 0


def test_requests_from_before_a_service_was_retired_are_not_cases_of_the_new_one(svc):
    org = svc
    old = request(org)
    deliver(org, "ceo", old)
    org.retire_service(ROOT, "ceo", "weekly-brief", "redo")
    time.sleep(0.002)
    define(org)
    assert services.cases(org, "ceo", "weekly-brief") == []


def test_digest_is_none_without_new_evidence(svc):
    org = svc
    assert services.reflection_digest(org, "ceo", "weekly-brief") is None  # no cases
    request(org)
    work(org, "ceo")
    assert services.reflection_digest(org, "ceo", "weekly-brief") is None  # an open case is no evidence yet


def test_digest_shows_finished_cases_feedback_and_stats(svc):
    org = svc
    task = request(org, "ai")
    deliver(org, "ceo", task, runs=2, lessons="Sources first.")
    digest = services.reflection_digest(org, "ceo", "weekly-brief")  # no playbook: any finished case is evidence
    assert digest is not None and task.id in digest and "done" in digest and "2 of 10 runs" in digest
    assert 'lessons: "Sources first."' in digest and "By playbook version:" in digest and "- v0: 1 request(s): 1 done" in digest
    org.feedback(ROOT, task.id, "reject", "No week-over-week changes.")
    digest = services.reflection_digest(org, "ceo", "weekly-brief")
    assert 'client feedback: reject "No week-over-week changes."' in digest


def test_a_revision_resets_the_evidence_and_later_feedback_counts_as_new(svc):
    org = svc
    task = request(org)
    deliver(org, "ceo", task)
    assert services.reflection_digest(org, "ceo", "weekly-brief") is not None
    org.revise_playbook("ceo", "weekly-brief", "Steps v1.", "first draft")
    assert services.reflection_digest(org, "ceo", "weekly-brief") is None  # everything so far is older than v1
    time.sleep(0.002)
    org.feedback(ROOT, task.id, "reject", "Missing sources.")  # feedback after the revision: new evidence
    digest = services.reflection_digest(org, "ceo", "weekly-brief")
    assert digest is not None and "Missing sources." in digest and task.id in digest
    org.revise_playbook("ceo", "weekly-brief", "Steps v2.", "added sources")
    assert services.reflection_digest(org, "ceo", "weekly-brief") is None
    nxt = request(org)
    deliver(org, "ceo", nxt, runs=1)
    assert services.reflection_digest(org, "ceo", "weekly-brief") is not None  # a case finished after v2


def test_digest_is_compact(svc):
    org = svc
    for i in range(9):
        t = request(org, f"topic {i} " + "x" * 60)
        deliver(org, "ceo", t, lessons="L" * 790)
    digest = services.reflection_digest(org, "ceo", "weekly-brief")
    assert len(digest) <= 3000
    assert digest.count("\n- case ") <= 6 and "- v0: 9 request(s)" in digest


# ------------------------------------------------------------------------------------------ prompt


def headers(prompt):
    return [line for line in prompt.splitlines() if line.startswith("# ")]


def test_an_org_without_services_gets_the_prompt_it_always_had(org):
    org.delegate(ROOT, "ceo", "Plan", "Make a plan", "plan.md exists", budget=4)
    batch = org.begin_run("ceo")
    prompt = org.run_prompt("ceo", batch)
    assert headers(prompt) == [
        "# orgmcp run: you are `ceo`", "# Organization", "# Your charter (ceo/AGENT.md, owned by your parent)",
        "# Role: Chief executive", "# Your memory (ceo/MEMORY.md)", "# Your state", "# New messages for this run (1)",
    ]
    assert "Your services" not in prompt and "Playbook:" not in prompt and "Reflect before" not in prompt
    assert prompt.count("\n\n\n") == 0 and "- Paths: every path" in prompt
    # the gap between the state and the messages is the single blank line it always was
    assert "Yours start with `ceo/`.\n\n# New messages for this run (1)\n" in prompt
    org.end_run("ceo", ok=True)
    # a service offered by someone else changes nothing for ceo
    define(org, owner=ENG, actor="ceo")
    org.delegate(ROOT, "ceo", "Plan 2", "Make a plan", "plan.md exists", budget=4)
    assert headers(org.run_prompt("ceo", org.begin_run("ceo"))) == headers(prompt)
    # and the tree and tools of a service-less agent are unchanged
    assert "services:" not in org.tree().split("ceo ")[1].split("\n")[0]


def test_the_prompt_lists_the_owners_services_every_run(svc):
    org = svc
    org.delegate(ROOT, "ceo", "Plain", "g", "c", budget=2)  # a plain task: no playbook, no reflection
    prompt = org.run_prompt("ceo", org.begin_run("ceo"))
    assert "# Your services" in prompt and "# Playbook" not in prompt and "# Reflect" not in prompt
    assert (
        "- weekly-brief: contract v1, no playbook yet, 0 request(s) so far; contract: ceo/services/weekly-brief/SERVICE.md; "
        "playbook: ceo/services/weekly-brief/PLAYBOOK.md"
    ) in prompt
    assert prompt.index("# Your services") < prompt.index("# New messages")


def test_the_playbook_is_shown_only_with_an_open_service_task(org):
    define(org, playbook="## Steps\n1. Search the web.\n2. Write the brief.")
    prompt = org.run_prompt("ceo", org.begin_run("ceo"))  # nothing to do
    assert "# Your services" in prompt and "# Playbook" not in prompt and "Search the web" not in prompt
    org.end_run("ceo", ok=True)
    task = request(org)
    prompt = org.run_prompt("ceo", org.begin_run("ceo"))
    assert "# Playbook: weekly-brief (v1, yours to improve)" in prompt
    assert "> ## Steps\n> 1. Search the web.\n> 2. Write the brief." in prompt
    org.end_run("ceo", ok=True)
    deliver(org, "ceo", task)
    assert "# Playbook" not in org.run_prompt("ceo", org.begin_run("ceo"))  # the task is answered


def test_a_service_without_a_playbook_says_how_to_start_one(svc):
    org = svc
    request(org)
    prompt = org.run_prompt("ceo", org.begin_run("ceo"))
    assert "# Playbook: weekly-brief (v0, yours to improve)" in prompt
    assert "No playbook yet: plan as usual; when you report this request, write v1 with revise_playbook" in prompt
    assert "# Reflect" not in prompt  # no evidence yet


def test_v0_playbook_section_agrees_with_the_reflect_section(svc):
    org = svc
    first = request(org, "ai")
    deliver(org, "ceo", first, lessons="Thin on sources.")
    request(org, "chips")  # a new request with evidence from an earlier case and still no playbook
    prompt = org.run_prompt("ceo", org.begin_run("ceo"))
    playbook = prompt.split("# Playbook: weekly-brief")[1].split("\n# ")[0]
    assert "# Reflect before you start: weekly-brief" in prompt
    assert "No playbook yet: write v1 now from the evidence below (Reflect before you start), then follow it." in playbook
    assert "when you report this request" not in prompt  # the old text would contradict the reflect section
    assert prompt.index("# Playbook: weekly-brief") < prompt.index("# Reflect before you start")  # "below" is true
    org.end_run("ceo", ok=True)


def test_a_long_playbook_is_cut_with_a_pointer_to_the_file(org):
    define(org, playbook="wordwordword " * 700)  # under the word cap, over the render limit (8000 characters)
    request(org)
    prompt = org.run_prompt("ceo", org.begin_run("ceo"))
    assert "playbook cut" in prompt and 'read(path="ceo/services/weekly-brief/PLAYBOOK.md")' in prompt


def test_the_reflect_section_comes_before_a_new_request_when_there_is_evidence(svc):
    org = svc
    first = request(org, "ai")
    deliver(org, "ceo", first, runs=2, lessons="Thin on sources.")
    org.feedback(ROOT, first.id, "reject", "No week-over-week changes.")
    new = request(org, "chips")
    prompt = org.run_prompt("ceo", org.begin_run("ceo"))
    assert "# Reflect before you start: weekly-brief" in prompt
    section = prompt.split("# Reflect before you start: weekly-brief")[1].split("# New messages")[0]
    assert "Evidence so far (there is no playbook yet):" in section and "No week-over-week changes." in section
    assert "revise_playbook(service, content, reason)" in section and "at most 1000 words" in section
    assert "A rejection or a failure is enough on its own" in section and "never lower it" in section
    assert "restore" not in section  # nothing earlier to restore at v0
    assert section.rstrip().endswith("Then handle the request following the playbook.")
    assert [line[:2] for line in section.splitlines() if line[:1].isdigit()] == ["1.", "2.", "3.", "4.", "5."]
    assert prompt.index("# Reflect before") < prompt.index("# New messages") < prompt.index(new.id, prompt.index("# New messages"))
    org.end_run("ceo", ok=True)


def test_the_reflect_section_offers_restoring_an_older_version_from_v2_on(svc):
    org = svc
    org.revise_playbook("ceo", "weekly-brief", "Steps one.", "first")
    org.revise_playbook("ceo", "weekly-brief", "Steps two.", "second")
    time.sleep(0.002)
    first = request(org)
    deliver(org, "ceo", first)
    request(org, "again")
    section = org.run_prompt("ceo", org.begin_run("ceo")).split("# Reflect before you start")[1].split("# New messages")[0]
    assert "Evidence since v2:" in section and "restore that one" in section
    assert "ceo/services/weekly-brief/history/PLAYBOOK.v<k>.md" in section


def test_no_reflect_section_for_rework_old_evidence_or_a_locked_playbook_edit_step(svc):
    org = svc
    first = request(org)
    deliver(org, "ceo", first)
    rework = org.delegate(ROOT, "ceo", "Fix", "g", "c", budget=3, revises=first.id)  # not a NEW request
    prompt = org.run_prompt("ceo", org.begin_run("ceo"))
    assert "# Reflect" not in prompt and "# Playbook: weekly-brief" in prompt
    org.end_run("ceo", ok=True)
    deliver(org, "ceo", rework)
    org.revise_playbook("ceo", "weekly-brief", "Steps.", "after the rework")
    request(org)  # new request, but no evidence since v1
    assert "# Reflect" not in org.run_prompt("ceo", org.begin_run("ceo"))


def test_the_locked_variant_shows_evidence_but_no_revision_steps(org):
    define(org, locked=True)
    first = request(org)
    deliver(org, "ceo", first)
    org.feedback(ROOT, first.id, "reject", "Too long.")
    request(org)
    prompt = org.run_prompt("ceo", org.begin_run("ceo"))
    section = prompt.split("# Reflect before you start: weekly-brief")[1].split("# New messages")[0]
    assert "locked by your parent" in section and "Too long." in section
    assert "call `revise_playbook" not in section and "restore" not in section
    assert "(v0, locked by your parent)" in prompt and "No playbook yet, and the contract is locked" in prompt
    assert "(locked)" in prompt.split("# Your services")[1].split("# ")[0]


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
    org.revise_playbook("ceo", "weekly-brief", "Steps.", "r")
    org.delegate(ROOT, "ceo", "Plain", "g", "c", budget=2)
    work(org, "ceo")
    assert org.agents() == ["ceo", ENG] and org.runs_used("ceo") == 1
    r = org.retire_team(ROOT, "ceo", "done")
    assert r.addr == "ceo"
    retired = list((org.root / ".retired").glob("ceo-*"))
    assert (retired[0] / "services" / "weekly-brief" / "SERVICE.md").is_file()  # the service moved with its owner


# ------------------------------------------------------------------------------------ tools by role


def tool_names(org, addr):
    return {t.name for t in asyncio.run(build_server(org, addr).list_tools())}


CLIENT_TOOLS = {"services", "define_service", "request", "feedback"}


def test_tools_are_registered_by_role(org):
    assert not tool_names(org, ENG) & (CLIENT_TOOLS | {"revise_playbook"})  # a plain worker sees none
    assert CLIENT_TOOLS <= tool_names(org, "ceo") and "revise_playbook" not in tool_names(org, "ceo")
    assert CLIENT_TOOLS <= tool_names(org, ROOT) and "revise_playbook" not in tool_names(org, ROOT)
    define(org)
    define(org, owner=ENG, actor="ceo", name="eng-brief")
    assert {"services", "revise_playbook"} <= tool_names(org, ENG) and not {"define_service", "request"} & tool_names(org, ENG)
    assert CLIENT_TOOLS | {"revise_playbook"} <= tool_names(org, "ceo")  # ceo is both a client and an owner
    org.hire(ROOT, "lone", "Lone worker", "Works alone.")
    define(org, owner="lone", name="lone-brief")
    assert tool_names(org, "lone") & (CLIENT_TOOLS | {"revise_playbook"}) == {"services", "revise_playbook"}


def test_the_services_tool_describes_what_you_can_request_and_offer(org):
    server = build_server(org, ROOT)
    assert "No services yet" in call(server, "services") and "define_service" in call(server, "services")
    define(org, playbook="Steps.")
    t1 = request(org, "ai")
    deliver(org, "ceo", t1, runs=3)
    org.feedback(ROOT, t1.id, "reject", "Bad.")
    org.revise_playbook("ceo", "weekly-brief", "Better steps.", "Case rejected for missing sources")
    out = call(server, "services")
    assert out.splitlines()[0] == "Services you can request (from your direct reports):"
    assert "- weekly-brief (offered by ceo; contract v1, playbook v2): A one-page brief" in out
    assert "inputs: topic* (what the brief is about), week (ISO week; default the current one)   (* required)" in out
    assert ("each request: 10 runs; acceptance criteria (ceo/services/weekly-brief/SERVICE.md):\n"
            "    1. At most 600 words\n    2. Every factual claim has a source URL\n  record:") in out
    assert "record: 1 request(s): 1 done, 0 failed, 0 open; 0 reworked; avg 3 runs; feedback 0 accept, 1 reject" in out
    assert '  playbook v2 (' in out and '"Case rejected for missing sources"' in out
    assert "Services you offer" not in out
    mine = call(build_server(org, "ceo"), "services")
    assert "Services you offer:" in mine and "playbook file: ceo/services/weekly-brief/PLAYBOOK.md" in mine
    assert "Services you can request" not in mine  # ceo's report offers nothing


# ----------------------------------------------------------------------------------------------- CLI


def test_cli_commands(org, capsys, tmp_path):
    criteria = tmp_path / "criteria.txt"
    criteria.write_text("At most 600 words\n- Every claim has a URL\n")
    playbook = tmp_path / "pb.md"
    playbook.write_text("## Steps\n1. Search.")
    cli(org, "define-service", "ceo", "weekly-brief", "--description", "A weekly brief.",
        "--input", "topic*:what it is about", "--input", "week:ISO week", "--acceptance", f"@{criteria}",
        "--acceptance", "Mention a risk", "--deliverable", "one file", "--format", "markdown", "--max-words", "600",
        "--path", str(tmp_path / "out"), "--budget", "8", "--playbook", f"@{playbook}", "--locked")
    meta, _ = contract_meta(org)
    assert meta["acceptance"] == ["At most 600 words", "Every claim has a URL", "Mention a risk"]
    assert meta["inputs"] == [{"name": "topic", "description": "what it is about", "required": True},
                              {"name": "week", "description": "ISO week", "required": False}]
    assert meta["deliverable"] == {"description": "one file", "format": "markdown", "max_words": 600, "path": str(tmp_path / "out")}
    assert meta["budget"] == 8 and meta["locked"] is True and playbook_meta(org)[0]["version"] == 1
    assert "defined service `weekly-brief`" in capsys.readouterr().out

    cli(org, "services")
    assert "weekly-brief (offered by ceo; contract v1, playbook v1)" in capsys.readouterr().out
    cli(org, "request", "weekly-brief", "--input", "topic=ai chips", "--input", "week=3", "--note", "Hurry")
    out = capsys.readouterr().out
    (task,) = org.outstanding(ROOT)
    assert task.id in out and task.budget == 8 and "- week: 3" in task.body and "Hurry" in task.body
    deliver(org, "ceo", task)
    cli(org, "feedback", task.id, "reject", "--note", "Too long")
    assert "feedback reject on" in capsys.readouterr().out
    assert [m.feedback for m in org.sent(ROOT) if m.type == "note"] == ["reject"]
    with pytest.raises(SystemExit):
        cli(org, "feedback", task.id, "reject")  # a rejection needs a note
    assert "needs a note" in capsys.readouterr().err
    with pytest.raises(SystemExit):
        cli(org, "request", "weekly-brief", "--input", "no-equals-sign")
    assert "key=value" in capsys.readouterr().err
    cli(org, "retire-service", "ceo", "weekly-brief", "--reason", "done with it")
    assert "retired service" in capsys.readouterr().out and org.service_names("ceo") == []
    log = __import__("subprocess").run(["git", "log", "--format=%s"], cwd=org.root, capture_output=True, text=True).stdout
    assert "root: service weekly-brief of ceo" in log and "root: retired service" in log


# ---------------------------------------------------------------------------- progress and status


def test_progress_tags_service_tasks_and_notes_missing_feedback(svc):
    org = svc
    org.revise_playbook("ceo", "weekly-brief", "Steps.", "r")
    task = request(org, "ai")
    (line,) = progress(org).splitlines()
    assert line.startswith('"weekly-brief: ai" [service weekly-brief v1]: working.') and "no feedback yet" not in line
    deliver(org, "ceo", task)
    org.delegate(ROOT, "ceo", "Plain", "g", "c", budget=2)
    out = progress(org)
    line = next(x for x in out.splitlines() if "weekly-brief: ai" in x)
    assert "[service weekly-brief v1]: done." in line and line.count("no feedback yet") == 1
    assert "[service" not in next(x for x in out.splitlines() if '"Plain"' in x)
    assert "Needs you" not in out  # neither the missing feedback nor the revision note asks for the human
    org.feedback(ROOT, task.id, "accept")
    assert "no feedback yet" not in progress(org)


def test_playbook_revisions_are_quiet_notices_for_root(svc):
    org = svc
    org.revise_playbook("ceo", "weekly-brief", "Steps.", "first")
    assert org.messages(ROOT, "inbox") and "Needs you" not in progress(org)
    org.notify(ROOT, "loud", "Needs a decision")
    assert "Needs you: runtime notice" in progress(org)


def test_status_tree_names_the_services_an_agent_offers(svc):
    tree = svc.tree()
    assert "ceo [Chief executive]" in tree and " services: weekly-brief" in tree.split("\n")[1]
    assert "services:" not in tree.split("\n")[2]


def test_new_organizations_carry_rule_10_and_upgrade_rules_propagates_it(org):
    assert "10. Services: a service is a standing kind of task your parent defined for you" in org.rules()
    assert "report it with `lessons`" in org.rules() and "revise_playbook" in org.rules()
    path = org.root / "ORG.md"
    text = path.read_text()
    path.write_text(text.split("10. Services:")[0].rstrip() + "\n")  # an organization created before services
    assert "10. Services" not in org.rules()
    cli(org, "upgrade-rules")
    assert "10. Services: a service is a standing kind of task" in org.rules()
    assert path.read_text() == text  # back to exactly the current template, settings and mission untouched


# ------------------------------------------------------------------------------- the whole loop


def test_define_request_report_reject_reflect_revise_and_compare_versions(org):
    root = build_server(org, ROOT)

    out = call(root, "define_service", owner="ceo", name="weekly-brief", description=BRIEF["description"],
               acceptance=BRIEF["acceptance"], deliverable=BRIEF["deliverable"], budget=10, inputs=BRIEF["inputs"])
    assert "defined service `weekly-brief`" in out
    ceo = build_server(org, "ceo")  # the owner's run starts after the definition: it now has revise_playbook
    out = call(root, "request", service="weekly-brief", inputs={"topic": "ai"})
    assert "requested service `weekly-brief` from ceo" in out and "Call start() if the scheduler is not running." in out
    task = org.outstanding(ROOT)[0]

    # the owner's first run: no playbook yet
    prompt = org.run_prompt("ceo", work(org, "ceo", 2))
    assert "No playbook yet" in prompt and "# Reflect" not in prompt
    assert "pass `lessons`" in fails(ceo, "report", task_id=task.id, status="done", summary="Delivered.")
    out = call(ceo, "report", task_id=task.id, status="done", summary="Delivered.", lessons="Used 2 runs; no checks.")
    assert "reported done" in out and "This service has no playbook yet: write v1 now with revise_playbook" in out
    org.end_run("ceo", ok=True)
    assert "now v1" in call(ceo, "revise_playbook", service="weekly-brief", content="## Steps\n1. Search.",
                            reason="first draft")
    assert services.read_playbook(org, "ceo", "weekly-brief").version == 1

    # the client rejects the delivery
    out = call(root, "feedback", task_id=task.id, verdict="reject", note="Missing week-over-week changes.")
    assert "feedback reject recorded" in out
    assert "needs a note" in fails(root, "feedback", task_id=task.id, verdict="reject")

    # the next request: the prompt shows the rejection before the new message
    second = org.request(ROOT, "weekly-brief", {"topic": "chips"})
    prompt = org.run_prompt("ceo", work(org, "ceo", 1))
    section = prompt.split("# Reflect before you start: weekly-brief")[1].split("# New messages")[0]
    assert "Evidence since v1:" in section and "Missing week-over-week changes." in section
    assert "Used 2 runs; no checks." in section
    out = call(ceo, "revise_playbook", service="weekly-brief",
               content="## Steps\n1. Search.\n2b. Compare with last week.", reason=f"case {task.id} rejected: no changes")
    assert "playbook of `weekly-brief` is now v2" in out
    out = call(ceo, "report", task_id=second.id, status="done", summary="Delivered again.", lessons="Step 2b worked.")
    assert "Lessons recorded. If they call for a playbook change now, use revise_playbook" in out
    org.end_run("ceo", ok=True)
    call(root, "feedback", task_id=second.id, verdict="accept")

    # stats show both versions
    listing = call(root, "services")
    assert "playbook v2" in listing and "2 request(s): 2 done, 0 failed, 0 open" in listing
    assert "feedback 1 accept, 1 reject" in listing
    per = services.stats_by_version(services.cases(org, "ceo", "weekly-brief"))
    # request 1 was delivered with no playbook (v1 was written after its report); request 2 was sent at v1 but
    # revised to v2 before it was worked on, so v2 is the version that delivered it
    assert sorted(per) == [0, 2] and [c.playbook for c in services.cases(org, "ceo", "weekly-brief")] == [0, 1]
    assert (per[0].reject, per[0].requests) == (1, 1) and (per[2].accept, per[2].requests) == (1, 1)
    # the evidence was consumed by the revision: nothing new until the next case finishes
    assert services.reflection_digest(org, "ceo", "weekly-brief") is not None  # case 2 finished after v2
    ids = [m.id for m in org.received(ROOT) if m.type == "result"]
    assert len(ids) == 2
    meta = yaml.safe_load((org.dir("ceo") / "services" / "weekly-brief" / "PLAYBOOK.md").read_text().split("---\n")[1])
    assert meta["version"] == 2 and meta["by"] == "ceo"


def test_a_locked_service_reports_without_the_revision_hint(org):
    define(org, locked=True)
    ceo = build_server(org, "ceo")
    task = request(org)
    work(org, "ceo")
    out = call(ceo, "report", task_id=task.id, status="done", summary="Delivered.", lessons="Fine.")
    assert out.startswith("reported done") and "revise_playbook" not in out
    assert "locked by root" in fails(ceo, "revise_playbook", service="weekly-brief", content="x", reason="r")
