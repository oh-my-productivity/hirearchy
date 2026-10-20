"""Round G: the whole feedback history of a case, reflection at the moment of rejection, case totals, escaping, health."""

import time

from testkit.services_world import ENG, call, define, deliver, request, svc, work  # noqa: F401  (svc is a fixture)

from orgmcp import services
from orgmcp.core import ROOT
from orgmcp.health import agent_health
from orgmcp.progress import progress
from orgmcp.server import build_server

WEEKDAY = "weekly-brief"


def test_the_feedback_tool_text_no_longer_says_a_later_one_replaces_the_earlier(svc):
    doc = services.feedback.__doc__
    assert "replaces" not in doc and "stays in the case" in doc
    tools = {t.name: t for t in __import__("asyncio").run(build_server(svc, ROOT).list_tools())}
    assert "replaces this one" not in tools["feedback"].description
    assert "every verdict stays" in tools["feedback"].description


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


def test_progress_lines_of_a_rework_chain_show_the_case_total(svc):
    first = request(svc, "ai")
    deliver(svc, "ceo", first, runs=3)
    svc.feedback(ROOT, first.id, "reject", "Too long.")
    time.sleep(0.002)
    rework = svc.request(ROOT, WEEKDAY, {"topic": "ai"}, revises=first.id, budget=6)
    deliver(svc, "ceo", rework, runs=2)
    text = progress(svc)
    assert text.count("case total: 5 runs used of 16 handed down (contract: 10 per request)") == 2  # one per task line
    assert "exceeds the per-request budget of 10: tell the user" in text
    assert ".." not in text.replace("...", "")  # the sentences join cleanly
    # the rework is delivered and not yet rated by the client; the first one has her verdict
    lines = {line.split("(task ")[1].rstrip(")"): line for line in text.splitlines() if "(task " in line}
    assert "no feedback yet" in lines[rework.id] and "no feedback yet" not in lines[first.id]


def test_a_single_request_case_has_no_case_total_line(svc):
    first = request(svc, "ai")
    deliver(svc, "ceo", first)
    assert "case total" not in progress(svc)


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


def test_messages_between_agents_keep_angle_brackets_too(svc):
    svc.delegate(ROOT, "ceo", "Plan", "Plan", "a plan", budget=10)
    msg = svc.delegate("ceo", ENG, "T", "Resolve 'before <weekday>' & \"for <date>\"", "c", budget=1)
    assert "before <weekday>" in msg.body and "&lt;" not in msg.body
    sent = svc.sent("ceo")[-1]
    assert "before <weekday>" in sent.body and "&lt;" not in sent.body


# ----------------------------------------------------------------------------------------- 6. health
def first_pass_and_client_rework(org, rounds=3):
    """root requests a service from ceo; ceo has eng review it; root sends the delivery back; ceo has eng re-check."""
    first = org.request(ROOT, WEEKDAY, {"topic": "ai"}, budget=20)
    work(org, "ceo")
    review = org.delegate("ceo", ENG, "Review", "Review the brief", "a verdict", budget=2)
    org.end_run("ceo", ok=True)
    work(org, ENG)
    org.report(ENG, review.id, "done", "PASS")
    org.end_run(ENG, ok=True)
    work(org, "ceo")
    org.report("ceo", first.id, "done", "Delivered.", lessons="Fine.")
    org.end_run("ceo", ok=True)
    rework = org.request(ROOT, WEEKDAY, {"topic": "ai"}, revises=first.id, budget=10)  # the client rejects
    work(org, "ceo")
    prev, checks = review, []
    for i in range(rounds):
        prev = org.delegate("ceo", ENG, f"Re-check {i}", "Review again", "a verdict", budget=1, revises=prev.id)
        checks.append(prev)
    return first, rework, checks


def test_reworks_that_come_from_the_client_of_a_service_case_are_not_held_against_the_agent(svc):
    first_pass_and_client_rework(svc)
    eng, ceo = agent_health(svc, ENG), agent_health(svc, "ceo")
    assert (eng.tasks_received, eng.rework, eng.client_rework) == (4, 0, 3)
    assert (ceo.rework, ceo.client_rework) == (0, 1)
    assert "low_quality" not in eng.flags and "low_quality" not in ceo.flags


def test_the_same_chain_without_a_service_still_counts_as_rework(svc):
    svc.delegate(ROOT, "ceo", "Plan", "Plan", "a plan", budget=20)
    work(svc, "ceo")
    prev = svc.delegate("ceo", ENG, "Review", "Review", "a verdict", budget=1)
    for i in range(3):
        prev = svc.delegate("ceo", ENG, f"Re-check {i}", "Review again", "a verdict", budget=1, revises=prev.id)
    eng = agent_health(svc, ENG)
    assert (eng.rework, eng.client_rework) == (3, 0) and "low_quality" in eng.flags


def test_a_rework_in_the_first_pass_of_a_service_request_still_counts(svc):
    request(svc, "ai")
    work(svc, "ceo")
    first = svc.delegate("ceo", ENG, "Write", "Write", "a draft", budget=1)
    svc.delegate("ceo", ENG, "Fix", "Fix it", "a draft", budget=1, revises=first.id)  # the lead's own quality control
    eng = agent_health(svc, ENG)
    assert (eng.rework, eng.client_rework) == (1, 0)


def test_the_rework_a_client_sends_after_a_failed_service_request_is_not_exempt(svc):
    first = request(svc, "ai")
    deliver(svc, "ceo", first, status="failed")
    svc.request(ROOT, WEEKDAY, {"topic": "ai"}, revises=first.id, budget=2)
    ceo = agent_health(svc, "ceo")
    assert (ceo.rework, ceo.client_rework) == (1, 0)
