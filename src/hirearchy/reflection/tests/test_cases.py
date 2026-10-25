# mypy: ignore-errors
# A test moved from tests/ by refactor step E1: not type-checked strictly (production code is). Delete the first line when this file is typed.

import time

from testkit.reach.hirearchy.core import ROOT
from testkit.services_world import contract_meta, define, deliver, request, svc, work

from hirearchy.kernel import RUNTIME, Message, run_credit_title
import hirearchy.reflection as reflection
from hirearchy.reflection import stats_by_version, summarize
from hirearchy.reflection.testing import fs_world

from . import _support as sup
from ._support import SERVICE, populated

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
    (case,) = svc.runtime.case_history.cases("ceo", WEEKDAY)
    assert [(v.verdict, v.note, v.task_id, v.step) for v in case.verdicts] == [
        ("reject", "Sam's 'before Friday' needs a date.", first.id, 0),
        ("accept", "this version is right", rework.id, 1),
    ]
    assert all(v.created is not None for v in case.verdicts)
    assert case.verdict == "accept" and case.rejected and case.accepted_after_reject
    assert case.feedback.reply_to == rework.id  # the final verdict is the latest note


def test_a_verdict_lists_its_link_notes_in_id_order(svc):
    """F-E4-7: the link notes that reply to a verdict (every tier) travel with it, so a cited link-note id can be resolved."""
    task = request(svc, "ai")
    deliver(svc, "ceo", task)
    no = svc.feedback(ROOT, task.id, "reject", "Too long.", source="human")
    plain = request(svc, "chips")
    deliver(svc, "ceo", plain)
    svc.feedback(ROOT, plain.id, "reject", "Too short.", source="human")
    time.sleep(0.002)
    first = svc.feedback(ROOT, task.id, "reject", "I read it as C1.", source="relayed", criterion=["C1"], confirms=no.id)
    time.sleep(0.002)
    second = svc.feedback(ROOT, task.id, "reject", "No: C2.", source="human", criterion=["C2"], confirms=no.id)
    cases = {c.id: c for c in svc.runtime.case_history.cases("ceo", WEEKDAY)}
    (verdict,) = cases[task.id].verdicts
    assert [m.id for m in verdict.link_notes] == [first.id, second.id]
    (other,) = cases[plain.id].verdicts
    assert other.link_notes == ()


def test_lesson_sources_parallel_lessons(svc):
    """Each lesson carries the ``source`` of the task its result answers, so the digest can mark the ones a relayed rework wrote (4.4)."""
    first = request(svc, "ai")
    deliver(svc, "ceo", first, lessons="One.")
    svc.feedback(ROOT, first.id, "reject", "Too long.", source="human")
    human = svc.request(ROOT, WEEKDAY, {"topic": "ai"}, revises=first.id, source="human")
    deliver(svc, "ceo", human, lessons="Two.")
    relayed = svc.request(ROOT, WEEKDAY, {"topic": "ai"}, revises=human.id)  # no source: the assistant's own rework is relayed
    deliver(svc, "ceo", relayed, lessons="Three.")
    (case,) = svc.runtime.case_history.cases("ceo", WEEKDAY)
    assert case.lessons == ["One.", "Two.", "Three."]
    assert case.lesson_sources == ["", "human", "relayed"]
    assert len(case.lesson_sources) == len(case.lesson_ids) == len(case.lessons)


def test_stats_keep_the_final_counts_and_say_how_many_accepts_came_after_a_reject(svc):
    rejected_then_accepted(svc)
    plain = request(svc, "chips")
    deliver(svc, "ceo", plain)
    svc.feedback(ROOT, plain.id, "accept")
    bad = request(svc, "bio")
    deliver(svc, "ceo", bad)
    svc.feedback(ROOT, bad.id, "reject", "Too long.")
    items = svc.runtime.case_history.cases("ceo", WEEKDAY)
    total = summarize(items)
    assert (total.accept, total.reject, total.accept_after_reject) == (2, 1, 1)
    assert total.line().endswith("feedback 2 accept (1 after a reject), 1 reject")
    record = svc.runtime.service_reports.services_text(ROOT)
    assert "feedback 2 accept (1 after a reject), 1 reject" in record


def test_stats_per_playbook_version_carry_the_after_a_reject_count(svc):
    rejected_then_accepted(svc)
    (v0,) = stats_by_version(svc.runtime.case_history.cases("ceo", WEEKDAY)).values()
    assert v0.line().endswith("feedback 1 accept (1 after a reject), 0 reject")


def test_a_case_rejected_twice_ends_as_a_reject_and_shows_both_verdicts(svc):
    first = request(svc, "ai")
    deliver(svc, "ceo", first)
    svc.feedback(ROOT, first.id, "reject", "No summary.", source="human")
    time.sleep(0.002)
    rework = svc.request(ROOT, WEEKDAY, {"topic": "ai"}, revises=first.id, budget=4)
    deliver(svc, "ceo", rework)
    svc.feedback(ROOT, rework.id, "reject", "Still no summary.", source="human")
    (case,) = svc.runtime.case_history.cases("ceo", WEEKDAY)
    assert case.verdict == "reject" and not case.accepted_after_reject
    assert 'client feedback: reject R1 "No summary." -> reject R2 "Still no summary."' in svc.runtime.reflection_digest.reflection_digest("ceo", WEEKDAY)
    assert summarize([case]).line().endswith("feedback 0 accept, 1 reject")


def test_a_long_verdict_history_is_cut_to_the_latest_ones(svc):
    first = request(svc, "ai")
    deliver(svc, "ceo", first)
    task = first
    for i in range(5):
        svc.feedback(ROOT, task.id, "reject", f"problem {i}")
        time.sleep(0.002)
        task = svc.request(ROOT, WEEKDAY, {"topic": "ai"}, revises=task.id, budget=2)
        deliver(svc, "ceo", task)
    line = svc.runtime.reflection_digest.reflection_digest("ceo", WEEKDAY)
    assert "client feedback: … -> reject" in line and "problem 4" in line and "problem 0" not in line


# ------------------------------------------------------------------------- cases, stats, digest
def test_cases_group_rework_chains_and_derive_runs_budget_and_lessons(svc):
    org = svc
    first = request(org, "ai")
    deliver(org, "ceo", first, runs=2, lessons="First pass was thin.")
    rework = request(org, "ai", revises=first.id, budget=4)
    deliver(org, "ceo", rework, runs=1, lessons="Added sources.")
    second = request(org, "chips")
    work(org, "ceo", 1)
    one, two = org.runtime.case_history.cases("ceo", "weekly-brief")
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
    blocked, failed = org.runtime.case_history.cases("ceo", "weekly-brief")
    assert (blocked.state, blocked.finished) == ("blocked", None) and failed.state == "failed"
    stats = summarize([blocked, failed])
    assert (stats.requests, stats.done, stats.failed, stats.open) == (2, 0, 1, 1)


def test_stats_per_playbook_version_and_the_one_line_summary(svc):
    org = svc
    a = request(org, "a")
    deliver(org, "ceo", a, runs=2)
    org.feedback(ROOT, a.id, "reject", "Bad.")
    org.revise_playbook("ceo", "weekly-brief", "Better steps.", "case a rejected", [])
    b = request(org, "b")
    deliver(org, "ceo", b, runs=1)
    org.feedback(ROOT, b.id, "accept")
    c = request(org, "c")
    deliver(org, "ceo", c, status="failed", runs=3)
    all_cases = org.runtime.case_history.cases("ceo", "weekly-brief")
    per = stats_by_version(all_cases)
    assert sorted(per) == [0, 1]
    v0, v1 = per[0], per[1]
    assert (v0.requests, v0.done, v0.reject, v0.avg_runs) == (1, 1, 1, 2.0)
    assert (v1.requests, v1.done, v1.failed, v1.accept, v1.avg_runs) == (2, 1, 1, 1, 2.0)
    assert v1.line() == "2 request(s): 1 done, 1 failed, 0 open; 0 reworked; avg 2 runs; feedback 1 accept, 0 reject"
    total = summarize(all_cases)
    assert total.requests == 3 and total.reworked == 0


def test_a_service_defined_again_after_a_delivery_continues_its_cases(svc):
    """Design 5.10 (Rule C): a service retired after a request that has a result and defined again is the same service, so its earlier request is
    a case of it again; the contract is v2 with the old ``created`` (a copy none of whose requests has a result starts fresh: test_contract_case_history)."""
    org = svc
    old = request(org)
    deliver(org, "ceo", old)
    org.feedback(ROOT, old.id, "accept", "dropped", source="relayed")  # a service is retired only after the verdict on its delivery (design 5.2a)
    created = contract_meta(org)[0]["created"]
    org.retire_service(ROOT, "ceo", "weekly-brief", "redo")
    time.sleep(0.002)
    define(org)
    assert [c.id for c in org.runtime.case_history.cases("ceo", "weekly-brief")] == [old.id]
    meta = contract_meta(org)[0]
    assert meta["version"] == 2 and meta["created"] == created


# ------------------------------------------------------------------------- relayed_runs (0b 4.2, built in 0a.3)
def chain_world(tmp_path):
    """The reflection world over files, with ``ceo`` offering weekly-brief to root; its clock stamps messages and run logs alike."""
    w = populated(fs_world(tmp_path))
    sup.define(w)
    return w


def the_case(w):
    (case,) = w.history.cases("ceo", SERVICE)
    return case


def test_relayed_runs_are_the_runs_of_the_last_interval_of_a_chain_that_ends_with_a_relayed_rework(tmp_path):
    """0b 4.2: the charged runs from a relayed task's send up to its successor's send (the window's end for the last one)."""
    w = chain_world(tmp_path)
    head = sup.ask(w)
    sup.deliver(w, head, runs=2)
    human = sup.rework(w, head)
    sup.deliver(w, human, runs=1)
    relayed = sup.rework(w, human, source="relayed")
    sup.deliver(w, relayed, runs=3)
    case = the_case(w)
    assert (case.runs, case.relayed_runs) == (6, 3)


def test_the_interval_of_a_relayed_rework_ends_at_the_id_of_the_next_task(tmp_path):
    w = chain_world(tmp_path)
    head = sup.ask(w)
    sup.deliver(w, head, runs=1)
    relayed = sup.rework(w, head, source="relayed")
    sup.deliver(w, relayed, runs=2)
    human = sup.rework(w, relayed)
    sup.deliver(w, human, runs=4)
    case = the_case(w)
    assert (case.runs, case.relayed_runs) == (7, 2)


def test_a_case_without_a_relayed_task_has_no_relayed_runs(tmp_path):
    w = chain_world(tmp_path)
    head = sup.ask(w)
    sup.deliver(w, head, runs=2)
    sup.deliver(w, sup.rework(w, head), runs=3)
    case = the_case(w)
    assert (case.runs, case.relayed_runs) == (5, 0)


def test_credited_runs_are_in_neither_count(tmp_path):
    w = chain_world(tmp_path)
    head = sup.ask(w)
    sup.deliver(w, head, runs=1)
    relayed = sup.rework(w, head, source="relayed")
    sup.deliver(w, relayed, runs=3)
    last = max(w.runs.files("ceo"), key=lambda f: f.stem).stem  # the relayed rework's last run ended on a throttle and was given back
    w.s.d.post(Message(sender=RUNTIME, to="ceo", type="note", budget=1, wake=False, title=run_credit_title("ceo", last), body="returned"))
    case = the_case(w)
    assert (case.runs, case.relayed_runs) == (3, 2)


def test_an_agent_clients_case_with_an_inherited_relayed_rework_still_gets_relayed_runs(tmp_path):
    """0b's definition holds for every client kind: a rework that carries ``source: relayed`` (inherited from the work it was made in) counts."""
    w = chain_world(tmp_path)
    w.s.d.post(Message(sender="root", to="ceo", type="note", body="runs for you", title="grant", budget=20))
    sup.define(w, "ceo/eng", "inner", actor="ceo")
    first = w.s.commands.request("ceo", "inner", {"topic": "ai"})
    sup.deliver(w, first, runs=2)
    second = w.s.d.post(Message(
        sender="ceo", to="ceo/eng", type="task", title="inner: ai", body="again", budget=5, revises=first.id, service="inner", source="relayed",
    ))
    sup.deliver(w, second, runs=3)
    (case,) = w.history.cases("ceo/eng", "inner")
    assert case.client_kind == "agent" and (case.runs, case.relayed_runs) == (5, 3)


# ------------------------------------------------------------------------- the user's spend, ceiling and overlap (D-E5-1, 4.3)
def ceiling_world(tmp_path, budget=12):
    """``chain_world`` with a contract of ``budget`` runs per request (E5's is 12)."""
    w = populated(fs_world(tmp_path))
    sup.define(w, budget=budget)
    return w


def grant(w, runs, to="ceo", sender="root"):
    """``sender``, the client, hands ``runs`` more runs down to ``to`` with a note."""
    return w.s.d.post(Message(sender=sender, to=to, type="note", body="more runs", title="grant", budget=runs))


def test_relayed_returned_is_what_the_relayed_results_carried_back_each_at_most_its_tasks_budget(tmp_path):
    w = ceiling_world(tmp_path)
    head = sup.ask(w)
    sup.deliver(w, head, runs=1, budget=9)  # a user task's return is not a relayed return
    first = sup.rework(w, head, source="relayed", budget=6)
    sup.deliver(w, first, runs=1, budget=9)  # more than the task's 6: counts 6
    second = sup.rework(w, first, source="relayed", budget=5)
    sup.deliver(w, second, runs=1, budget=2)
    assert the_case(w).relayed_returned == 6 + 2


def test_a_grant_in_a_user_interval_is_a_user_grant_and_one_in_a_relayed_interval_is_not(tmp_path):
    w = ceiling_world(tmp_path)
    head = sup.ask(w)
    grant(w, 3)  # in the head's interval
    sup.deliver(w, head, runs=1)
    relayed = sup.rework(w, head, source="relayed", budget=6)
    grant(w, 4, to="ceo/eng")  # in the relayed rework's interval: the assistant's, not the user's
    sup.deliver(w, relayed, runs=1)
    assert the_case(w).user_granted == 3


def test_a_note_outside_the_window_is_not_a_grant(tmp_path):
    w = ceiling_world(tmp_path)
    grant(w, 5)  # before the first request
    head = sup.ask(w)
    sup.deliver(w, head, runs=1)
    grant(w, 6)  # after the final result
    assert the_case(w).user_granted == 0


def test_an_agent_clients_case_has_no_user_grants_and_no_user_ceiling(tmp_path):
    w = ceiling_world(tmp_path)
    grant(w, 40, to="ceo")
    sup.define(w, "ceo/eng", "inner", actor="ceo")
    first = w.s.commands.request("ceo", "inner", {"topic": "ai"})
    grant(w, 3, to="ceo/eng", sender="ceo")
    sup.deliver(w, first, runs=2)
    second = w.s.commands.request("ceo", "inner", {"topic": "ai"}, revises=first.id, budget=4)
    sup.deliver(w, second, runs=1)
    (case,) = w.history.cases("ceo/eng", "inner")
    assert case.client_kind == "agent" and case.user_granted == case.user_ceiling == 0


def test_the_ceiling_of_e5s_s1_t6_is_17(tmp_path):
    """Ceilings 12 and 5 + 12 = 17 (design 4.3): the old default handed the contract's 12 again, and the files cannot tell that from a top-up."""
    w = ceiling_world(tmp_path)
    sup.s1_t6(w)
    case = the_case(w)
    assert (case.runs, case.relayed_runs, case.relayed_returned, case.user_ceiling, case.user_granted, case.relayed_overlap) == (15, 5, 1, 17, 0, 0)
    assert reflection.user_spend(case) == 10 and reflection.user_approved(case, 12) == 17


def relayed_return(w, *, returned, runs=5, grant_to=None, successor=False):
    """A user request, then a relayed rework (6 runs handed down) with ``runs`` runs in its interval, optionally a grant of 4 to the team inside it,
    answered with ``returned`` runs; ``successor``: the user's rework was sent first, so the relayed result came after its successor."""
    head = sup.ask(w)
    sup.deliver(w, head, runs=1)
    relayed = sup.rework(w, head, source="relayed", budget=6)
    if grant_to:
        grant(w, 4, to=grant_to)
    if successor:
        sup.rework(w, relayed, budget=2)
    sup.deliver(w, relayed, runs=runs, budget=returned)
    return relayed


def test_relayed_to_user_is_the_return_beyond_what_the_relayed_task_still_had(tmp_path):
    """D-E6-2, B1 (E6 s3's 406b): the relayed task had 6 and 5 runs in its interval, so it still had 1; its result returns 7: 6 are the user's."""
    w = ceiling_world(tmp_path)
    relayed_return(w, returned=7)
    case = the_case(w)
    assert (case.relayed_runs, case.relayed_returned, case.relayed_to_user) == (5, 6, 6)


def test_a_relayed_result_returning_at_most_what_the_task_still_had_gives_the_user_nothing_back(tmp_path):
    """D-E6-2, B1 (E5 s1's 592f): 6 handed down, 5 used, 1 returned: that is the relayed task's own; nothing, and no result at all, the same."""
    for n, returned in enumerate((1, 0)):
        (tmp_path / str(n)).mkdir()
        w = ceiling_world(tmp_path / str(n))
        relayed_return(w, returned=returned)
        assert the_case(w).relayed_to_user == 0


def test_a_grant_in_the_relayed_interval_is_part_of_what_the_relayed_task_had(tmp_path):
    """D-E6-2, B1: a grant of 4 in the interval of the relayed task makes its funds 10: with 5 runs it still had 5, so a return of 9 gives 4 back."""
    w = ceiling_world(tmp_path)
    relayed_return(w, returned=9, grant_to="ceo/eng")
    case = the_case(w)
    assert (case.relayed_returned, case.relayed_to_user) == (6, 4)


def test_a_relayed_result_that_came_after_its_successor_gives_the_user_nothing_back(tmp_path):
    """D-E6-2, B1, conservative (design 5.7, declared limit 6): the interval of the relayed task ends at its successor, so the runs it spent after
    that are not in the interval and what it still had cannot be told."""
    w = ceiling_world(tmp_path)
    relayed_return(w, returned=7, successor=True)
    assert the_case(w).relayed_to_user == 0


def test_a_relayed_task_without_a_result_gives_the_user_nothing_back(tmp_path):
    w = ceiling_world(tmp_path)
    head = sup.ask(w)
    sup.deliver(w, head, runs=1)
    sup.rework(w, head, source="relayed", budget=6)
    assert the_case(w).relayed_to_user == 0


def test_an_agent_clients_case_has_no_relayed_to_user(tmp_path):
    """D-E6-2, B1: an agent client has no user; the same shape as the 406b case gives 0 (``case_spend`` and the agent's text are today's)."""
    w = ceiling_world(tmp_path)
    grant(w, 40, to="ceo")
    sup.define(w, "ceo/eng", "inner", actor="ceo")
    first = w.s.commands.request("ceo", "inner", {"topic": "ai"})
    sup.deliver(w, first, runs=2)
    second = w.s.d.post(Message(
        sender="ceo", to="ceo/eng", type="task", title="inner: ai", body="again", budget=6, revises=first.id, service="inner", source="relayed",
    ))
    sup.deliver(w, second, runs=5, budget=7)
    (case,) = w.history.cases("ceo/eng", "inner")
    assert case.client_kind == "agent" and case.relayed_returned == 6 and case.relayed_to_user == 0


def test_a_case_without_a_relayed_task_has_no_relayed_to_user(tmp_path):
    w = ceiling_world(tmp_path)
    head = sup.ask(w)
    sup.deliver(w, head, runs=2, budget=3)
    sup.deliver(w, sup.rework(w, head, budget=4), runs=1, budget=9)
    assert the_case(w).relayed_to_user == 0


def test_the_ceiling_after_a_relayed_return_does_not_grow_when_the_user_rework_takes_what_is_left(tmp_path):
    """D-E6-2, B1 (E6 s3's 9a5b): the 6 runs the relayed result carried back are the user's, so a rework handed down what is left (6) raises no
    ceiling: the approval stays 12. Read as held (before B1), they put the ceiling at 18."""
    w = ceiling_world(tmp_path)
    relayed = relayed_return(w, returned=7)
    case = the_case(w)
    left = reflection.user_approved(case, 12) - reflection.user_committed(case)
    assert (case.relayed_to_user, left) == (6, 6)
    sup.rework(w, relayed, budget=left)
    case = the_case(w)
    assert (case.user_ceiling, reflection.user_approved(case, 12), reflection.user_committed(case)) == (12, 12, 12)


def test_open_tasks_are_the_tasks_of_the_chain_without_a_result_or_with_a_blocked_one(tmp_path):
    """D-E6-2, B2 (P-8): a task is open until a ``done`` or ``failed`` result answers it; ``open_tasks`` lists them oldest first."""
    w = chain_world(tmp_path)
    head = sup.ask(w)
    sup.deliver(w, head, runs=1)  # done
    blocked = sup.rework(w, head)
    sup.deliver(w, blocked, status="blocked")
    failed = sup.rework(w, blocked)
    sup.deliver(w, failed, status="failed")
    unanswered = sup.rework(w, failed)
    assert the_case(w).open_tasks == (blocked.id, unanswered.id)


def test_a_blocked_task_answered_again_by_a_done_result_is_closed(tmp_path):
    w = chain_world(tmp_path)
    head = sup.ask(w)
    sup.deliver(w, head, status="blocked")
    assert the_case(w).open_tasks == (head.id,)
    time.sleep(0.002)
    sup.deliver(w, head)  # the latest result of the task is done
    assert the_case(w).open_tasks == ()


def s2_t5(w, answered):
    """E5 s2 at T5: ebe2 (12, 9 runs, 3 returned) and 6c4f human (5 handed down), answered (5 runs, none returned) or still open."""
    first = sup.ask(w, "s2")
    sup.deliver(w, first, runs=9, budget=3)
    human = sup.rework(w, first, budget=5)
    if answered:
        sup.deliver(w, human, runs=5)


def test_the_ceiling_of_e5s_s2_t5_is_14_open_and_answered(tmp_path):
    for answered, runs, spend in ((False, 9, 14), (True, 14, 14)):
        (tmp_path / str(answered)).mkdir()
        w = ceiling_world(tmp_path / str(answered))
        s2_t5(w, answered)
        case = the_case(w)
        assert (case.runs, case.relayed_runs, case.user_ceiling) == (runs, 0, 14)
        assert reflection.user_spend(case) == spend and reflection.user_approved(case, 12) == 14


def test_the_ceiling_of_e5s_s3_final_is_14_and_the_grant_in_the_human_interval_counts(tmp_path):
    """e268 (12, 9 runs, 3 returned); c209 human (3, 3 runs, blocked); a grant of 2 in c209's interval; daff relayed (6, 5 runs): ceilings 12, 12, 14."""
    w = ceiling_world(tmp_path)
    first = sup.ask(w, "s3")
    sup.deliver(w, first, runs=9, budget=3)
    blocked = sup.rework(w, first, budget=3)
    sup.deliver(w, blocked, status="blocked", runs=3)
    grant(w, 2)
    w.use_run("ceo")  # c209 resumes after the grant
    relayed = sup.rework(w, blocked, source="relayed", budget=6)
    sup.deliver(w, relayed, runs=5)
    case = the_case(w)
    assert (case.runs, case.relayed_runs, case.user_granted, case.user_ceiling) == (18, 5, 2, 14)
    assert reflection.user_spend(case) == 13 and reflection.user_approved(case, 12) == 14


def overlapping_chain(w, answered):
    """A done request; a relayed rework R (budget 6) with 2 runs; then a human rework H; R's 4 later runs fall in H's interval. ``answered``: R was
    answered (with its whole budget back) before H was sent, so nothing of it can lie in H's interval."""
    head = sup.ask(w)
    sup.deliver(w, head, runs=1)
    relayed = sup.rework(w, head, source="relayed", budget=6)
    if answered:
        sup.deliver(w, relayed, runs=2, budget=6)
    else:
        for _ in range(2):
            w.use_run("ceo")
    sup.rework(w, relayed)
    for _ in range(4 if not answered else 0):
        w.use_run("ceo")


def test_a_relayed_rework_still_running_when_the_next_one_is_sent_overlaps_it_by_its_unspent_runs(tmp_path):
    """DR-0a3-1, P-1: R (6) ran 2 in its interval and has no result before H: up to 4 of its runs can lie in H's interval, and they are the
    ``unsplit_runs`` of the user's interval."""
    w = ceiling_world(tmp_path, budget=10)
    overlapping_chain(w, answered=False)
    case = the_case(w)
    assert (case.relayed_runs, case.relayed_overlap, case.unsplit_runs) == (2, 4, 4)


def test_a_relayed_rework_answered_before_the_next_one_overlaps_nothing(tmp_path):
    w = ceiling_world(tmp_path, budget=10)
    overlapping_chain(w, answered=True)
    case = the_case(w)
    assert (case.relayed_overlap, case.unsplit_runs) == (0, 0)


def test_a_relayed_rework_that_is_the_last_task_overlaps_nothing(tmp_path):
    w = ceiling_world(tmp_path, budget=10)
    head = sup.ask(w)
    sup.deliver(w, head, runs=1)
    for _ in range(2):
        w.use_run("ceo")
    sup.rework(w, head, source="relayed", budget=6)
    case = the_case(w)
    assert (case.relayed_overlap, case.unsplit_runs) == (0, 0)


def nothing_left(w):
    """The head used the contract's 12 runs and returned none, then the user's rework of 1 run (the default with nothing left); both returned."""
    head = sup.ask(w)
    sup.deliver(w, head, runs=12)  # the contract's 12, all used, none returned
    return head, sup.rework(w, head, budget=1)


def test_a2_with_nothing_left_a_rework_of_one_run_raises_no_approval(tmp_path):
    """D-E7-2 A2 and declared limit 1 (design 4.3): the default's 1 run with nothing left (here the explicit ``budget=1``, which the files cannot tell it
    from) is no approval of the user's: the case marks it in ``unapproved_reworks`` and the ceiling stays 12 (it was 13)."""
    w = ceiling_world(tmp_path)
    _, rework = nothing_left(w)
    case = the_case(w)
    assert case.unapproved_reworks == (rework.id,)
    assert case.user_ceiling == 12 and reflection.user_approved(case, 12) == 12


def test_a2_the_marker_changes_no_spend_figure(tmp_path):
    """D-E7-2 A2 changes only the ceiling: ``user_committed``, ``user_spend`` and ``user_held`` are today's numbers (13, 13, 0), pinned as literals."""
    w = ceiling_world(tmp_path)
    _, rework = nothing_left(w)
    case = the_case(w)
    assert (reflection.user_committed(case), reflection.user_spend(case), reflection.user_held(case, rework)) == (13, 13, 0)


def test_a2_a_grant_after_the_marked_rework_counts_in_full(tmp_path):
    """D-E7-2 A2, I-A2: root's grant of 2 after the user's yes counts in full. 13 are committed (12 used, the marked run held) and the marked run is
    left out, so the grant term is 12 + 2 = 14."""
    w = ceiling_world(tmp_path)
    nothing_left(w)
    grant(w, 2)
    case = the_case(w)
    assert reflection.user_approved(case, 12) == 14


def test_a2_the_marked_run_is_left_out_whether_it_is_held_or_charged(tmp_path):
    """D-E7-2 A2, Deviation 2: the marked run charged before the grant (nothing else held) is not counted again through the runs: still 14."""
    w = ceiling_world(tmp_path)
    nothing_left(w)
    w.use_run("ceo")  # the marked rework's run
    grant(w, 2)
    assert reflection.user_approved(the_case(w), 12) == 14


def test_a2_e7_s2_shape_a_grant_of_one_approves_13_and_a_cost_of_14_is_over_it(tmp_path):
    """D-E7-2 A2 (E7 s2): 9 runs used of 12, the rework of 1 run (3 held + 1 = 12 committed, nothing left), a grant of 1: the approval is 13; the
    rework then uses 5 runs, so the user's requests cost 14, and the case total says so."""
    w = ceiling_world(tmp_path)
    head = sup.ask(w)
    for _ in range(9):
        w.use_run("ceo")
    rework = sup.rework(w, head, budget=1)
    grant(w, 1)
    assert the_case(w).unapproved_reworks == (rework.id,) and reflection.user_approved(the_case(w), 12) == 13
    sup.deliver(w, rework, runs=5)
    case = the_case(w)
    assert reflection.user_cost(case) == 14 and reflection.user_approved(case, 12) == 13
    assert w.reports.case_total(rework).endswith(
        "The user's requests now cost 14 runs, more than the 13 the user approved for this case (contract: 12 per request, plus 1 approved beyond it): "
        "tell the user."
    )


def test_a2_a_rework_of_one_run_with_one_left_is_no_default_with_nothing_left(tmp_path):
    """D-E7-2 A2: 11 of 12 used and 1 returned leaves 1 run held for the user's requests (11 committed): the 1-run rework had 1 left, so it is not
    marked, and the approval stays 12."""
    w = ceiling_world(tmp_path)
    head = sup.ask(w)
    sup.deliver(w, head, runs=11, budget=1)
    sup.rework(w, head, budget=1)
    case = the_case(w)
    assert case.unapproved_reworks == () and reflection.user_approved(case, 12) == 12


def test_a2_a_rework_of_two_runs_with_nothing_left_is_root_s_own_hand_down_and_raises_the_approval(tmp_path):
    """D-E7-2 A2: only the 1-run rework is the default; a rework of 2 runs sent with nothing left is root's explicit hand-down: 12 + 2 = 14."""
    w = ceiling_world(tmp_path)
    head = sup.ask(w)
    sup.deliver(w, head, runs=12)
    sup.rework(w, head, budget=2)
    case = the_case(w)
    assert case.unapproved_reworks == () and reflection.user_approved(case, 12) == 14


def test_a2_a_marked_rework_that_gave_its_run_back_leaves_nothing_out_at_a_later_grant(tmp_path):
    """D-E7-2 A2: the marked rework was answered ``blocked`` with its run returned and not used, so a later grant of 2 finds nothing to leave out:
    12 committed + 2 = 14 (the window stays open: ``blocked`` is not final)."""
    w = ceiling_world(tmp_path)
    head = sup.ask(w)
    sup.deliver(w, head, runs=12)
    marked = sup.rework(w, head, budget=1)
    sup.deliver(w, marked, status="blocked", runs=0, budget=1)
    grant(w, 2)
    case = the_case(w)
    assert case.unapproved_reworks == (marked.id,) and reflection.user_approved(case, 12) == 14


def test_a2_two_reworks_of_one_run_in_a_row_are_both_marked(tmp_path):
    """D-E7-2 A2: the second default also had nothing left (the first one's run is committed), so both are marked and the approval stays 12."""
    w = ceiling_world(tmp_path)
    head = sup.ask(w)
    sup.deliver(w, head, runs=12)
    first = sup.rework(w, head, budget=1)
    second = sup.rework(w, first, budget=1)
    case = the_case(w)
    assert case.unapproved_reworks == (first.id, second.id) and reflection.user_approved(case, 12) == 12


def test_a2_an_agent_clients_case_and_a_relayed_rework_have_no_marker(tmp_path):
    """D-E7-2 A2: an agent client has no user and no approval; a relayed rework of 1 run is not the default's case (root's own, ``source="relayed"``)."""
    w = ceiling_world(tmp_path)
    head = sup.ask(w)
    sup.deliver(w, head, runs=12)
    sup.rework(w, head, source="relayed", budget=1)
    assert the_case(w).unapproved_reworks == ()
    grant(w, 40, to="ceo")
    sup.define(w, "ceo/eng", "inner", actor="ceo")
    first = w.s.commands.request("ceo", "inner", {"topic": "ai"})
    sup.deliver(w, first, runs=12)
    w.s.commands.request("ceo", "inner", {"topic": "ai"}, revises=first.id, budget=1)
    (case,) = w.history.cases("ceo/eng", "inner")
    assert case.client_kind == "agent" and case.unapproved_reworks == ()


def test_limit_2_a_reopened_window_counts_another_requests_runs_as_the_users_and_as_approved(tmp_path):
    """Declared limit 2 (design 4.3): memo 1 is done at E; memo 2 runs 4 runs; then memo 1's human rework (the default would hand down what is
    left, 4) reopens the window: the 4 runs count in this case, and the ceiling is approved + 4."""
    w = ceiling_world(tmp_path)
    memo1 = sup.ask(w, "memo 1")
    sup.deliver(w, memo1, runs=8, budget=4)
    sup.ask(w, "memo 2")
    for _ in range(4):
        w.use_run("ceo")
    sup.rework(w, memo1, budget=4)
    case = next(c for c in w.history.cases("ceo", SERVICE) if c.id == memo1.id)
    assert case.runs == 8 + 4 and case.user_ceiling == 12 + 4 and reflection.user_spend(case) == 12
