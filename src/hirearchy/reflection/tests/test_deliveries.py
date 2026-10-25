"""``deliveries_of``, ``signer_of``, ``not_on_a_delivery`` and ``unjudged_cases``: the delivery rules of the quality view (pure; design 3, 4.3, 4.4).

Message ids start with a microsecond timestamp, so a larger number is a later id. The tests build the messages and the cases by hand: the
rules read values, not files."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta, timezone

import pytest

from hirearchy.kernel import Message, latest_results, msg_time, verdict_tier
from hirearchy.reflection import Case, Delivery, Verdict, deliveries_of, not_on_a_delivery, signer_of, unjudged_cases

OWNER, AUTHOR, CHECKER = "ceo", "ceo/eng", "ceo/chk"


def ident(n: int, sender: str = "ceo") -> str:
    """The id of the message sent ``n`` seconds after the origin (so ids order like ``n``)."""
    return f"20260101T00{n // 60:02d}{n % 60:02d}000000-{sender.replace('/', '-')}-{n:04d}"


def task(n: int, *, revises: str | None = None, source: str | None = None) -> Message:
    return Message(sender="root", to=OWNER, type="task", body="b", title=f"t{n}", id=ident(n, "root"), service="s", revises=revises, source=source)


def result(for_task: Message, n: int, status: str = "done") -> Message:
    return Message(sender=OWNER, to="root", type="result", body="r", id=ident(n), reply_to=for_task.id, status=status)


def verdict(on: Message, n: int, kind: str = "reject", *, source: str | None = "human", sender: str = "root", step: int = 0) -> Verdict:
    note = Message(sender=sender, to=OWNER, type="note", body=f"words {n}", id=ident(n, sender), reply_to=on.id, feedback=kind, source=source)
    return Verdict(kind, f"words {n}", msg_time(note), on.id, step, note, tier=verdict_tier(note))


def micros(v: Verdict) -> int:
    """The send time of a verdict's note in microseconds since the epoch (what ``Delivery.edited_at`` is compared with)."""
    assert v.created is not None
    return (v.created - datetime(1970, 1, 1, tzinfo=timezone.utc)) // timedelta(microseconds=1)


def case(tasks: list[Message], results: dict[str, Message], *verdicts: Verdict, state: str = "done") -> Case:
    return Case(
        id=tasks[0].id, service="s", owner=OWNER, tasks=tasks, result=results.get(tasks[-1].id), state=state, playbook=0, used=0,
        reworks=len(tasks) - 1, budget=1, runs=1, lessons=[], verdicts=list(verdicts), started=None, finished=None,
    )


def delivered(c: Case, results: dict[str, Message]) -> tuple[Delivery, ...]:
    return deliveries_of(c, results, {})


# ------------------------------------------------------------------------------------------------------------------------ deliveries


def test_a_delivery_is_a_task_whose_latest_result_is_done() -> None:
    t1, t2, t3, t4 = task(1), task(10, revises=ident(1, "root")), task(20, revises=ident(10, "root")), task(30, revises=ident(20, "root"))
    # t1 was blocked first, then answered done: the later result is the one that counts
    results = latest_results([result(t1, 5, "blocked"), result(t1, 8, "done"), result(t2, 15, "done"), result(t3, 25, "failed")])
    c = case([t1, t2, t3, t4], results)
    got = delivered(c, results)
    assert [(d.task.id, d.result.id, d.step, d.case) for d in got] == [
        (t1.id, ident(8), 0, c.id), (t2.id, ident(15), 1, c.id),
    ]  # t3 failed and t4 has no result: no delivery


def test_the_latest_result_decides_and_a_task_turned_blocked_again_is_no_delivery() -> None:
    t = task(1)
    first, later = result(t, 5, "done"), result(t, 9, "blocked")
    got = deliveries_of(case([t], {}), latest_results([first, later]), {})
    assert got == ()


def test_the_signer_of_a_delivery_is_the_one_given_for_its_task_else_the_owner() -> None:
    t1, t2 = task(1), task(10, revises=ident(1, "root"))
    results = {t1.id: result(t1, 5), t2.id: result(t2, 15)}
    got = deliveries_of(case([t1, t2], results), results, {t1.id: CHECKER})
    assert [d.signer for d in got] == [CHECKER, OWNER]


def test_a_verdict_counts_for_the_delivery_only_after_its_done_result() -> None:
    t = task(1)
    results = {t.id: result(t, 10)}
    before, after, other = verdict(t, 5), verdict(t, 20, "accept"), verdict(task(50), 30)
    c = case([t], results, before, after, other)
    (d,) = delivered(c, results)
    assert [v.message.id for v in d.verdicts] == [after.message.id]  # the early one was given before the done; the other is on another task
    assert d.judged and not d.escape and d.outcome == "accepted"


def test_a_verdict_on_a_blocked_result_that_later_turns_done_is_not_on_the_delivery() -> None:
    t = task(1)
    results = latest_results([result(t, 5, "blocked"), result(t, 20)])
    accept = verdict(t, 10, "accept")  # E's 550c: given on the blocked result
    c = case([t], results, accept)
    (d,) = delivered(c, results)
    assert d.verdicts == () and not d.judged and d.outcome == "none"
    assert [m.id for m in not_on_a_delivery(c, (d,))] == [accept.message.id]


def test_superseded_is_the_first_later_task_sent_after_the_result() -> None:
    t1 = task(1)
    sent_before_the_result = task(8, revises=t1.id)
    sent_after, sent_later = task(30, revises=t1.id), task(40, revises=t1.id)
    results = {t1.id: result(t1, 10)}
    (d,) = deliveries_of(case([t1, sent_before_the_result, sent_after, sent_later], results), results, {})
    assert d.superseded == sent_after.id
    (alone,) = deliveries_of(case([t1], results), results, {})
    assert alone.superseded == ""  # nothing came after it


def test_a_delivery_with_a_human_verdict_is_not_superseded() -> None:
    t1 = task(1)
    t2 = task(30, revises=t1.id)
    results = {t1.id: result(t1, 10)}
    judged = case([t1, t2], results, verdict(t1, 20, "accept"))
    assert delivered(judged, results)[0].superseded == ""
    relayed_only = case([t1, t2], results, verdict(t1, 20, "accept", source="relayed"))
    assert delivered(relayed_only, results)[0].superseded == t2.id  # only a human-tier verdict keeps a delivery from being superseded


def test_counted_and_voided_split_at_the_edit_time() -> None:
    t = task(1)
    results = {t.id: result(t, 10)}
    early, late = verdict(t, 20, "reject"), verdict(t, 40, "accept")
    (d,) = delivered(case([t], results, early, late), results)
    edited = replace(d, edited=True, edited_at=micros(late))  # the file changed at the instant of the second verdict
    assert [v.message.id for v in edited.counted] == [early.message.id]
    assert [v.message.id for v in edited.voided] == [late.message.id]  # at or after the edit
    assert edited.escape and edited.outcome == "rejected"  # a verdict given before the change keeps judging the team's file
    assert [v.message.id for v in d.counted] == [early.message.id, late.message.id] and d.voided == ()  # not edited: all of them count


def test_an_edit_time_of_zero_marks_the_delivery_edited_and_voids_nothing() -> None:
    t = task(1)
    results = {t.id: result(t, 10)}
    (d,) = delivered(case([t], results, verdict(t, 20), verdict(t, 30, "accept")), results)
    unknown = replace(d, edited=True, edited_at=0)
    assert unknown.edited and len(unknown.counted) == 2 and unknown.voided == ()


def test_outcome_is_rejected_accepted_neither_or_none() -> None:
    t = task(1)
    results = {t.id: result(t, 10)}
    reject, accept = verdict(t, 20), verdict(t, 21, "accept")
    base = delivered(case([t], results), results)[0]
    assert base.outcome == "none" and not base.judged and not base.escape and base.decisive is None
    (rejected,) = delivered(case([t], results, reject), results)
    (accepted,) = delivered(case([t], results, accept), results)
    assert (rejected.outcome, rejected.judged, rejected.escape) == ("rejected", True, True)
    assert (accepted.outcome, accepted.judged, accepted.escape) == ("accepted", True, False)
    neither = replace(accepted, edited=True, edited_at=1)  # the one verdict came after the file changed
    assert (neither.outcome, neither.judged, neither.counted, len(neither.voided)) == ("neither", False, (), 1)


def test_a_reject_then_an_accept_stays_an_escape() -> None:
    t = task(1)
    results = {t.id: result(t, 10)}
    (d,) = delivered(case([t], results, verdict(t, 20), verdict(t, 21, "accept")), results)
    assert d.escape and d.outcome == "rejected"


def test_the_decisive_verdict_is_the_latest_counted_reject_else_the_latest_counted() -> None:
    t = task(1)
    results = {t.id: result(t, 10)}
    first, second, accept = verdict(t, 20), verdict(t, 21), verdict(t, 22, "accept")
    (d,) = delivered(case([t], results, first, second, accept), results)
    assert d.decisive is second  # the latest reject, not the later accept
    (only_accepts,) = delivered(case([t], results, verdict(t, 20, "accept"), accept), results)
    assert only_accepts.decisive is accept  # no reject: the latest counted verdict


def test_relayed_and_agent_verdicts_never_count() -> None:
    t = task(1)
    results = {t.id: result(t, 10)}
    relayed = verdict(t, 20, source="relayed")
    agent = verdict(t, 21, source="human", sender="ops")  # an agent cannot claim a source
    legacy = verdict(t, 22, source=None)  # written before sources existed: the user's
    for tier_only in (relayed, agent):
        (d,) = delivered(case([t], results, tier_only), results)
        assert d.verdicts == (tier_only,) and d.counted == () and d.voided == () and not d.judged and not d.escape and d.outcome == "none"
    (d,) = delivered(case([t], results, relayed, agent), results)
    assert not d.judged
    (kept,) = delivered(case([t], results, legacy), results)
    assert kept.judged and kept.escape
    edited = replace(d, edited=True, edited_at=1)
    assert edited.voided == ()  # only human-tier verdicts are ever voided


# ------------------------------------------------------------------------------------------------------------------------ unjudged cases


def two_cases() -> tuple[list[Case], tuple[Delivery, ...]]:
    judged_task, silent_task, relayed_task, agent_task, open_task = task(1), task(100), task(200), task(300), task(400)
    results = {t.id: result(t, 10 + i * 100) for i, t in enumerate((judged_task, silent_task, relayed_task, agent_task))}
    cases = [
        case([judged_task], results, verdict(judged_task, 50, "accept")),
        case([silent_task], results),
        case([relayed_task], results, verdict(relayed_task, 250, "reject", source="relayed")),
        case([agent_task], results, verdict(agent_task, 350, "reject", sender="ops")),
        case([open_task], {}, state="open"),
    ]
    return cases, tuple(d for c in cases for d in deliveries_of(c, results, {}))


def test_unjudged_cases_are_done_cases_whose_latest_delivery_has_no_human_verdict() -> None:
    cases, deliveries = two_cases()
    assert unjudged_cases(cases, deliveries) == (cases[1].id, cases[2].id, cases[3].id)  # the judged case and the open one are not
    assert unjudged_cases(cases, deliveries, relayed_only=True) == (cases[2].id, cases[3].id)  # a relayed- or agent-tier verdict only


def test_a_case_in_another_state_is_never_unjudged() -> None:
    t = task(1)
    results = {t.id: result(t, 10, "failed")}
    failed = case([t], results, state="failed")
    assert unjudged_cases([failed], deliveries_of(failed, results, {})) == ()


def test_the_latest_delivery_is_read_when_no_delivery_is_flagged_given() -> None:
    t1, t2 = task(1), task(100, revises=ident(1, "root"))
    results = {t1.id: result(t1, 10), t2.id: result(t2, 110)}
    c = case([t1, t2], results, verdict(t1, 50, "accept"))  # the first delivery was judged, the latest was not
    assert unjudged_cases([c], deliveries_of(c, results, {})) == (c.id,)


def test_the_given_delivery_is_read_when_one_is_flagged() -> None:
    t1, t2 = task(1), task(100, revises=ident(1, "root"))
    results = {t1.id: result(t1, 10), t2.id: result(t2, 110)}
    c = case([t1, t2], results, verdict(t1, 50, "accept"))
    first, second = deliveries_of(c, results, {})
    assert unjudged_cases([c], (replace(first, given=True), second)) == ()  # the user was given the first one, and judged it
    assert unjudged_cases([c], (first, replace(second, given=True))) == (c.id,)


# ------------------------------------------------------------------------------------------------------------------------ not on a delivery


def test_not_on_a_delivery_lists_human_verdicts_on_blocked_failed_or_early_results() -> None:
    blocked_task, failed_task, early_task, open_task, good_task = task(1), task(100), task(200), task(300), task(400)
    results = {
        blocked_task.id: result(blocked_task, 10, "blocked"),
        failed_task.id: result(failed_task, 110, "failed"),
        early_task.id: result(early_task, 250),
        good_task.id: result(good_task, 410),
    }
    on_blocked, on_failed = verdict(blocked_task, 20), verdict(failed_task, 120, "accept")
    on_early, on_open, on_good = verdict(early_task, 210), verdict(open_task, 310), verdict(good_task, 420)
    relayed = verdict(blocked_task, 30, source="relayed")  # not the user's: never listed
    c = case(
        [blocked_task, failed_task, early_task, open_task, good_task], results,
        on_blocked, relayed, on_failed, on_early, on_open, on_good, state="done",
    )
    ds = deliveries_of(c, results, {})
    assert [d.task.id for d in ds] == [early_task.id, good_task.id]
    got = not_on_a_delivery(c, ds)
    assert [m.id for m in got] == [on_blocked.message.id, on_failed.message.id, on_early.message.id, on_open.message.id]  # oldest first, whole messages
    assert all(isinstance(m, Message) for m in got)


def test_nothing_is_off_a_delivery_when_every_verdict_follows_its_done_result() -> None:
    t = task(1)
    results = {t.id: result(t, 10)}
    c = case([t], results, verdict(t, 20))
    assert not_on_a_delivery(c, delivered(c, results)) == ()


# ------------------------------------------------------------------------------------------------------------------------ the sign-off
# (the rule moved from health/_escapes.py; health keeps its own copy until its deliveries come from here)


def sign_off_world(*, check_status: str = "done", with_team: bool = True) -> tuple[list[Message], list[Message], Message, Message]:
    """The owner's boxes for one request ``T`` (``done`` answered at 16): the author drafts (task 11, done 12), the checker checks (task 13, ``check_status`` 14)."""
    request = Message(sender="root", to=OWNER, type="task", body="b", id=ident(10, "root"), service="s")
    owner_sent: list[Message] = []
    owner_received: list[Message] = [request]
    if with_team:
        author_task = Message(sender=OWNER, to=AUTHOR, type="task", body="b", id=ident(11))
        check_task = Message(sender=OWNER, to=CHECKER, type="task", body="b", id=ident(13))
        owner_sent += [author_task, check_task]
        owner_received += [
            Message(sender=AUTHOR, to=OWNER, type="result", body="r", id=ident(12, AUTHOR), reply_to=author_task.id, status="done"),
            Message(sender=CHECKER, to=OWNER, type="result", body="r", id=ident(14, CHECKER), reply_to=check_task.id, status=check_status),
        ]
    done = Message(sender=OWNER, to="root", type="result", body="r", id=ident(16), reply_to=request.id, status="done")
    owner_sent.append(done)
    return owner_sent, owner_received, request, done


REPORTS = {AUTHOR, CHECKER}


def test_the_sign_off_is_the_last_report_done_before_the_owners_done() -> None:
    sent, received, request, done = sign_off_world()
    assert signer_of(OWNER, request.id, done.id, sent, received, REPORTS) == CHECKER  # the checker passed the delivered version
    late = Message(sender=AUTHOR, to=OWNER, type="result", body="r", id=ident(40, AUTHOR), reply_to=sent[0].id, status="done")
    assert signer_of(OWNER, request.id, done.id, sent, [*received, late], REPORTS) == CHECKER  # a result after the owner's done signs nothing off


def test_a_report_that_is_not_done_signs_nothing_off() -> None:
    sent, received, request, done = sign_off_world(check_status="failed")
    assert signer_of(OWNER, request.id, done.id, sent, received, REPORTS) == AUTHOR


def test_the_owner_signs_alone_without_a_report() -> None:
    sent, received, request, done = sign_off_world(with_team=False)
    assert signer_of(OWNER, request.id, done.id, sent, received, REPORTS) == OWNER


def test_a_result_after_the_owners_done_signs_nothing_off() -> None:
    sent, received, request, done = sign_off_world(with_team=False)
    task_after = Message(sender=OWNER, to=AUTHOR, type="task", body="b", id=ident(20))
    answer_after = Message(sender=AUTHOR, to=OWNER, type="result", body="r", id=ident(30, AUTHOR), reply_to=task_after.id, status="done")
    assert signer_of(OWNER, request.id, done.id, [*sent, task_after], [*received, answer_after], REPORTS) == OWNER


def test_only_a_task_the_owner_sent_after_the_delivered_one_can_be_signed_off() -> None:
    sent, received, request, done = sign_off_world()
    old = Message(sender=OWNER, to=CHECKER, type="task", body="b", id=ident(2))  # sent before the request arrived
    old_answer = Message(sender=CHECKER, to=OWNER, type="result", body="r", id=ident(15, CHECKER), reply_to=old.id, status="done")
    assert signer_of(OWNER, request.id, done.id, [old, *sent], [*received, old_answer], REPORTS) == CHECKER  # still the checker's own, later task
    assert signer_of(OWNER, request.id, done.id, [old, *sent[:1]], [received[0], old_answer, received[1]], REPORTS) == AUTHOR


@pytest.mark.parametrize("who", ["ops", "ceo/other"])
def test_only_a_direct_report_can_sign_off(who: str) -> None:
    sent, received, request, done = sign_off_world(with_team=False)
    stranger_task = Message(sender=OWNER, to=who, type="task", body="b", id=ident(11))
    answer = Message(sender=who, to=OWNER, type="result", body="r", id=ident(12, who), reply_to=stranger_task.id, status="done")
    assert signer_of(OWNER, request.id, done.id, [*sent, stranger_task], [*received, answer], REPORTS) == OWNER
