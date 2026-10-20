"""Round G: the whole feedback history of a case, reflection at the moment of rejection, case totals, escaping, health."""

from testkit.services_world import ENG, call, define, deliver, request, svc, work  # noqa: F401  (svc is a fixture)

from orgmcp import services
from orgmcp.core import ROOT
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
