"""Round G: the whole feedback history of a case, reflection at the moment of rejection, case totals, escaping, health."""

import time

from testkit.services_world import ENG, call, define, deliver, request, svc, work  # noqa: F401  (svc is a fixture)

from orgmcp import services
from orgmcp.core import ROOT
from orgmcp.server import build_server

WEEKDAY = "weekly-brief"


def rejected_then_accepted(org, *, reject="Sam's 'before Friday' needs a date.", accept="this version is right", runs=(2, 3)):
    """A request, rejected after its delivery, sent back with ``request(revises=...)``, delivered again and accepted."""
    first = request(org, "ai")
    deliver(org, "ceo", first, runs=runs[0], lessons="Clean run; no issues.")
    org.feedback(ROOT, first.id, "reject", reject)
    time.sleep(0.002)
    rework = org.request(ROOT, WEEKDAY, {"topic": "ai"}, revises=first.id, budget=6)
    deliver(org, "ceo", rework, runs=runs[1], lessons="Applied the date rule.")
    time.sleep(0.002)
    org.feedback(ROOT, rework.id, "accept", accept)
    return first, rework


# ------------------------------------------------------------------------------- 1. every verdict stays
def test_a_case_keeps_every_verdict_in_order_with_the_task_it_was_given_on(svc):
    first, rework = rejected_then_accepted(svc)
    (case,) = services.cases(svc, "ceo", WEEKDAY)
    assert [(v.verdict, v.note, v.task_id, v.step) for v in case.verdicts] == [
        ("reject", "Sam's 'before Friday' needs a date.", first.id, 0),
        ("accept", "this version is right", rework.id, 1),
    ]
    assert all(v.created is not None for v in case.verdicts)
    assert case.verdict == "accept" and case.rejected and case.accepted_after_reject
    assert case.feedback.reply_to == rework.id  # the final verdict is the latest note


def test_the_digest_shows_the_rejection_with_her_words_and_then_the_accept(svc):
    rejected_then_accepted(svc)
    digest = services.reflection_digest(svc, "ceo", WEEKDAY)
    assert 'client feedback: reject "Sam\'s \'before Friday\' needs a date." -> accept "this version is right"' in digest
    # the client's verdicts come before the lessons
    assert digest.index("client feedback:") < digest.index("lessons")
    # the lesson of the rework was written after the reject: the digest says so
    assert 'lessons (written after the reject: check it against her words): "Applied the date rule."' in digest


def test_a_bare_accept_has_no_quotes_and_a_clean_case_is_unchanged(svc):
    first = request(svc, "ai")
    deliver(svc, "ceo", first, lessons="Fine.")
    svc.feedback(ROOT, first.id, "accept")
    digest = services.reflection_digest(svc, "ceo", WEEKDAY)
    assert "; client feedback: accept; lessons: " in digest and "written after" not in digest
    assert "feedback 1 accept, 0 reject" in digest and "after a reject" not in digest


def test_stats_keep_the_final_counts_and_say_how_many_accepts_came_after_a_reject(svc):
    rejected_then_accepted(svc)
    plain = request(svc, "chips")
    deliver(svc, "ceo", plain)
    svc.feedback(ROOT, plain.id, "accept")
    bad = request(svc, "bio")
    deliver(svc, "ceo", bad)
    svc.feedback(ROOT, bad.id, "reject", "Too long.")
    items = services.cases(svc, "ceo", WEEKDAY)
    total = services.summarize(items)
    assert (total.accept, total.reject, total.accept_after_reject) == (2, 1, 1)
    assert total.line().endswith("feedback 2 accept (1 after a reject), 1 reject")
    record = services.services_text(svc, ROOT)
    assert "feedback 2 accept (1 after a reject), 1 reject" in record


def test_stats_per_playbook_version_carry_the_after_a_reject_count(svc):
    rejected_then_accepted(svc)
    (v0,) = services.stats_by_version(services.cases(svc, "ceo", WEEKDAY)).values()
    assert v0.line().endswith("feedback 1 accept (1 after a reject), 0 reject")


def test_a_case_rejected_twice_ends_as_a_reject_and_shows_both_verdicts(svc):
    first = request(svc, "ai")
    deliver(svc, "ceo", first)
    svc.feedback(ROOT, first.id, "reject", "No summary.")
    time.sleep(0.002)
    rework = svc.request(ROOT, WEEKDAY, {"topic": "ai"}, revises=first.id, budget=4)
    deliver(svc, "ceo", rework)
    svc.feedback(ROOT, rework.id, "reject", "Still no summary.")
    (case,) = services.cases(svc, "ceo", WEEKDAY)
    assert case.verdict == "reject" and not case.accepted_after_reject
    assert 'client feedback: reject "No summary." -> reject "Still no summary."' in services.reflection_digest(svc, "ceo", WEEKDAY)
    assert services.summarize([case]).line().endswith("feedback 0 accept, 1 reject")


def test_a_long_verdict_history_is_cut_to_the_latest_ones(svc):
    first = request(svc, "ai")
    deliver(svc, "ceo", first)
    task = first
    for i in range(5):
        svc.feedback(ROOT, task.id, "reject", f"problem {i}")
        time.sleep(0.002)
        task = svc.request(ROOT, WEEKDAY, {"topic": "ai"}, revises=task.id, budget=2)
        deliver(svc, "ceo", task)
    line = services.reflection_digest(svc, "ceo", WEEKDAY)
    assert "client feedback: … -> reject" in line and "problem 4" in line and "problem 0" not in line


def test_the_feedback_tool_text_no_longer_says_a_later_one_replaces_the_earlier(svc):
    doc = services.feedback.__doc__
    assert "replaces" not in doc and "stays in the case" in doc
    tools = {t.name: t for t in __import__("asyncio").run(build_server(svc, ROOT).list_tools())}
    assert "replaces this one" not in tools["feedback"].description
    assert "every verdict stays" in tools["feedback"].description


# --------------------------------------------------------------------- 2/3. reflect at the moment of rejection
def reflect_section(prompt):
    return prompt.split("# Reflect before you start: weekly-brief")[1].split("# New messages")[0]


def test_a_rejection_with_its_rework_request_brings_the_reflect_section(svc):
    first = request(svc, "ai")
    deliver(svc, "ceo", first, lessons="Clean run.")
    svc.feedback(ROOT, first.id, "reject", "Sam's date is wrong.")
    svc.request(ROOT, WEEKDAY, {"topic": "ai"}, revises=first.id, budget=5)  # a rework: not a NEW request
    prompt = svc.run_prompt("ceo", svc.begin_run("ceo"))
    section = reflect_section(prompt)
    assert 'client feedback: reject "Sam\'s date is wrong."' in section
    assert (
        "The client rejected a delivery: decide now whether the playbook must change so this does not happen again "
        "(revise_playbook), then handle the rework."
    ) in section
    assert "Before working on the new request" not in section
    assert "When a lesson of yours conflicts with the client's feedback, the client is right: fix the playbook to match "\
           "the feedback (and say so in the reason)." in section
    assert section.rstrip().endswith("Then handle the rework following the playbook.")
    assert prompt.count("# Reflect before you start") == 1
    assert prompt.index("# Reflect before") < prompt.index("# New messages")


def test_two_rejections_in_one_batch_give_one_reflect_section_per_service(svc):
    a, b = request(svc, "a"), request(svc, "b")
    work(svc, "ceo")
    svc.report("ceo", a.id, "done", "ok", lessons="fine")
    svc.report("ceo", b.id, "done", "ok", lessons="fine")
    svc.end_run("ceo", ok=True)
    svc.feedback(ROOT, a.id, "reject", "first problem")
    svc.feedback(ROOT, b.id, "reject", "second problem")
    prompt = svc.run_prompt("ceo", svc.begin_run("ceo"))
    assert prompt.count("# Reflect before you start: weekly-brief") == 1
    assert "first problem" in prompt and "second problem" in prompt


def test_an_accept_or_a_rework_without_a_reject_brings_no_reflect_section(svc):
    first = request(svc, "ai")
    deliver(svc, "ceo", first)
    svc.feedback(ROOT, first.id, "accept", "good")
    assert "# Reflect" not in svc.run_prompt("ceo", svc.begin_run("ceo"))
    svc.end_run("ceo", ok=True)


def test_a_reject_with_a_new_request_keeps_the_new_request_wording(svc):
    first = request(svc, "ai")
    deliver(svc, "ceo", first)
    svc.feedback(ROOT, first.id, "reject", "Too long.")
    request(svc, "chips")
    section = reflect_section(svc.run_prompt("ceo", svc.begin_run("ceo")))
    assert "The client rejected a delivery: decide now" in section and "then handle the request." in section
    assert section.rstrip().endswith("Then handle the request following the playbook.")


def test_the_client_wins_step_is_in_every_reflect_section(svc):
    first = request(svc, "ai")
    deliver(svc, "ceo", first)
    request(svc, "chips")
    section = reflect_section(svc.run_prompt("ceo", svc.begin_run("ceo")))
    assert "the client is right: fix the playbook to match the feedback (and say so in the reason)" in section
    assert [line[:2] for line in section.splitlines() if line[:1].isdigit()][:2] == ["1.", "2."]


def test_a_locked_service_reflects_on_a_rejection_without_revising(svc):
    define(svc, name="locked-brief", owner="ceo", locked=True, description="Locked brief.")
    first = svc.request(ROOT, "locked-brief", {"topic": "ai"})
    deliver(svc, "ceo", first)
    svc.feedback(ROOT, first.id, "reject", "Too long.")
    svc.request(ROOT, "locked-brief", {"topic": "ai"}, revises=first.id, budget=3)
    section = svc.run_prompt("ceo", svc.begin_run("ceo")).split("# Reflect before you start: locked-brief")[1].split("# New messages")[0]
    assert "The client rejected a delivery. The contract is locked, so you cannot revise the playbook" in section
    assert "call `revise_playbook" not in section and "the client is right: follow the feedback" in section


def test_a_playbook_revised_after_the_rejection_leaves_no_reflect_section(svc):
    first = request(svc, "ai")
    deliver(svc, "ceo", first)
    svc.feedback(ROOT, first.id, "reject", "Too long.")
    time.sleep(0.002)
    svc.revise_playbook("ceo", WEEKDAY, "Steps.", "after the rejection")
    svc.request(ROOT, WEEKDAY, {"topic": "ai"}, revises=first.id, budget=3)
    assert "# Reflect" not in svc.run_prompt("ceo", svc.begin_run("ceo"))


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


def test_messages_between_agents_keep_angle_brackets_too(svc):
    svc.delegate(ROOT, "ceo", "Plan", "Plan", "a plan", budget=10)
    msg = svc.delegate("ceo", ENG, "T", "Resolve 'before <weekday>' & \"for <date>\"", "c", budget=1)
    assert "before <weekday>" in msg.body and "&lt;" not in msg.body
    sent = svc.sent("ceo")[-1]
    assert "before <weekday>" in sent.body and "&lt;" not in sent.body
