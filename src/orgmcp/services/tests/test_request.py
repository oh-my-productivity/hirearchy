# mypy: ignore-errors
# A test moved from tests/ by tools/relocate_tests.py: untyped until it is converted. Delete the first line when this file is typed.

import pytest
from testkit.legacy.orgmcp.core import ROOT, Message, OrgError, split_frontmatter
from testkit.reflection_world import lessons_of
from testkit.services_world import ENG, define, deliver, request, svc, work


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
    stored = org.runtime.message_parser.parse(org.dir("ceo") / "inbox" / f"{msg.id}.md")
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
    (case,) = org.runtime.case_history.cases("ceo", "weekly-brief")
    assert [t.id for t in case.tasks] == [first.id, rework.id] and case.reworks == 1


def test_old_messages_without_service_fields_parse_as_before(org):
    msg = org.delegate(ROOT, "ceo", "Plain", "g", "c", budget=2)
    stored = org.runtime.message_parser.parse(org.dir("ceo") / "inbox" / f"{msg.id}.md")
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
    assert lessons_of(blocked) == "Sources were not provided."  # required for blocked too
    org.write("ceo", "ceo/work/brief.md", "# Brief")
    final = org.report("ceo", task.id, "done", "Delivered.", ["ceo/work/brief.md"], lessons="Search first.\nTwo runs.")
    assert final.body.index("## Summary") < final.body.index("## Lessons") < final.body.index("## Artifacts")
    assert "## Lessons\nSearch first.\nTwo runs." in final.body
    assert lessons_of(final) == "Search first.\nTwo runs."


def test_lessons_are_optional_for_plain_tasks_and_kept_when_given(org):
    task = org.delegate(ROOT, "ceo", "Plain", "g", "c", budget=2)
    work(org, "ceo")
    res = org.report("ceo", task.id, "done", "Done.", lessons="Anyway.")
    assert "## Lessons\nAnyway." in res.body
    other = org.delegate(ROOT, "ceo", "Plain 2", "g", "c", budget=2)
    assert "## Lessons" not in org.report("ceo", other.id, "done", "Done.").body
