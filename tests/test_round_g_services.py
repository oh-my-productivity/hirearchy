"""Round G: the whole feedback history of a case, reflection at the moment of rejection, case totals, escaping, health."""

import time

from testkit.services_world import ENG, call, define, deliver, request, svc, work  # noqa: F401  (svc is a fixture)

from orgmcp import services
from orgmcp.core import ROOT
from orgmcp.health import agent_health
from orgmcp.progress import progress

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
