# mypy: ignore-errors
# A test moved from tests/ by refactor step E1: not type-checked strictly (production code is). Delete the first line when this file is typed.

import asyncio

import testkit.reach.yaml as yaml
from testkit.reach.hirearchy.core import ROOT
from testkit.mcp_server_world import build_server, services
from testkit.services_world import BRIEF, ENG, call, define, deliver, fails, request, svc, work

from hirearchy.services import ServiceCommands

WEEKDAY = "weekly-brief"


def test_the_feedback_tool_text_no_longer_says_a_later_one_replaces_the_earlier(svc):
    doc = ServiceCommands.feedback.__doc__
    assert "replaces" not in doc and "stays in the case" in doc
    tools = {t.name: t for t in __import__("asyncio").run(build_server(svc, ROOT).list_tools())}
    assert "replaces this one" not in tools["feedback"].description
    assert "every verdict stays" in tools["feedback"].description


def test_root_request_rework_without_source_is_relayed(svc):
    server = build_server(svc, ROOT)
    first = request(svc, "ai")
    deliver(svc, "ceo", first, runs=1)
    call(server, "request", service=WEEKDAY, inputs={"topic": "ai"}, revises=first.id, budget=3)
    call(server, "request", service=WEEKDAY, inputs={"topic": "ai"}, revises=first.id, budget=3, source="human")
    plain = call(server, "request", service=WEEKDAY, inputs={"topic": "other"})
    sent = svc.received("ceo")
    assert [m.source for m in sent if m.revises == first.id] == ["relayed", "human"]
    assert [m.source for m in sent if m.id in plain] == [None]  # a fresh request is the user's ask: not stamped
    assert "source: relayed" in [m for m in sent if m.revises == first.id][0].to_text()


# ----------------------------------------------------------------------------------------- 4. case totals
def test_the_rework_reply_states_the_case_total_and_warns_when_it_exceeds_the_contract(svc):
    server = build_server(svc, ROOT)
    first = request(svc, "ai")  # 10 runs handed down (the contract's)
    deliver(svc, "ceo", first, runs=4)
    plain = call(server, "request", service=WEEKDAY, inputs={"topic": "other"})
    assert "case total" not in plain  # not a rework: nothing to total
    reply = call(server, "request", service=WEEKDAY, inputs={"topic": "ai"}, revises=first.id, budget=6)
    assert "case total: 4 runs used of 16 handed down (contract: 10 per request)" in reply
    assert "This case now exceeds the per-request budget of 10: tell the user." in reply


def test_a_rework_within_the_contract_budget_gets_no_warning(svc):
    server = build_server(svc, ROOT)
    first = svc.request(ROOT, WEEKDAY, {"topic": "ai"}, budget=3)
    deliver(svc, "ceo", first, runs=2)
    reply = call(server, "request", service=WEEKDAY, inputs={"topic": "ai"}, revises=first.id, budget=4)
    assert "case total: 2 runs used of 7 handed down (contract: 10 per request)" in reply and "exceeds" not in reply


# ------------------------------------------------------------------------------------------ 5. escaping
def test_angle_brackets_and_ampersands_are_stored_exactly_as_given(svc):
    reason = 'Cases rejected for <weekday> & "dates"; keep &lt;literal&gt; -> done'
    content = "## Steps\n1. Resolve <weekday> and <date> & check \"quotes\" and &amp; entities.\n"
    server = build_server(svc, "ceo")
    call(server, "revise_playbook", service=WEEKDAY, content=content, reason=reason)
    pb = services.read_playbook(svc, "ceo", WEEKDAY)
    assert pb.reason == reason and pb.body == content.strip()
    raw = (svc.dir("ceo") / "services" / WEEKDAY / "PLAYBOOK.md").read_text()
    assert "<weekday>" in raw and "&lt;literal&gt;" in raw and "&amp;lt;" not in raw
    # the notice to the client, the listing and the owner's prompt carry the same characters
    assert reason in [m.body for m in svc.messages(ROOT, "inbox")][-1]
    assert f'"{reason}"' in services.services_text(svc, ROOT)
    request(svc, "ai")
    assert "Resolve <weekday> and <date> & check" in svc.run_prompt("ceo", svc.begin_run("ceo"))

    # the same through the Org API, and in the archived history
    svc.revise_playbook("ceo", WEEKDAY, "## Steps\n1. Other <b>.", "second <i> & more")
    assert services.read_playbook(svc, "ceo", WEEKDAY).reason == "second <i> & more"
    assert "<weekday>" in (svc.dir("ceo") / "services" / WEEKDAY / "history" / "PLAYBOOK.v1.md").read_text()


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
            "    C1: At most 600 words\n    C2: Every factual claim has a source URL\n  record:") in out
    assert "record: 1 request(s): 1 done, 0 failed, 0 open; 0 reworked; avg 3 runs; feedback 0 accept, 1 reject" in out
    assert '  playbook v2 (' in out and '"Case rejected for missing sources"' in out
    assert "Services you offer" not in out
    mine = call(build_server(org, "ceo"), "services")
    assert "Services you offer:" in mine and "playbook file: ceo/services/weekly-brief/PLAYBOOK.md" in mine
    assert "Services you can request" not in mine  # ceo's report offers nothing


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
