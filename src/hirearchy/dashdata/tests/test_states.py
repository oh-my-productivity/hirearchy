"""``classify``: the one state of an agent, in words (moved from ``tests/test_dashboard_data.py``; the assertions are those)."""

from __future__ import annotations

import itertools

from hirearchy.dashdata import STATE_KINDS, AgentState, classify, pause_text


def test_an_agent_is_in_exactly_one_state_for_every_combination() -> None:
    """``classify`` over every combination of its inputs: one state; the words never contradict each other."""
    n = 0
    for running, unread, paused, budget, open_n, out_n, up, free in itertools.product(
            (True, False), (0, 2), (None, "broken", "paused by the user: x", "budget"), (0, 3), (0, 1), (0, 1), (True, False), (0, 1)):
        st = classify(running=running, unread=unread, paused=paused, budget=budget, open_tasks=open_n, delegated=out_n,
                      scheduler_up=up, free_slots=free, max_parallel=2, elapsed_s=72.0 if running else None)
        n += 1
        word, ctx = st.word, (running, unread, paused, budget, open_n, out_n, up, free)
        assert st.kind in STATE_KINDS and word == st.main + st.note, ctx
        effective_pause = paused is not None and not (paused == "budget" and budget > 0)
        has_pause_word, has_queued_word, has_budget_word = "paused" in word, "queued" in word, "out of budget" in word
        if running:
            assert st.kind == "running" and word.startswith("running 1m12s") and not has_queued_word, ctx
            assert (f"+{unread} unread" in word) == bool(unread), ctx
            assert (up or "scheduler not running" in word) and (not up or "scheduler not running" not in word), ctx
            assert (st.reason != "") == bool(unread), ctx
        elif effective_pause and paused != "budget":  # paused wins over mail, budget, tasks
            assert paused is not None and st.kind == "paused" and word.startswith(pause_text(paused)), ctx
            assert not has_queued_word and not has_budget_word and word.endswith(f", {unread} unread" if unread else word), ctx
        elif effective_pause or (budget <= 0 and (unread or open_n or out_n)):  # out of budget wins over queued
            assert st.kind == "budget" and word == "out of budget" + (f", {unread} unread" if unread else ""), ctx
            assert not has_pause_word and not has_queued_word, ctx
        elif unread:  # queued: it would run, and why it has not yet
            assert st.kind == "queued" and word.startswith("queued: ") and not has_pause_word and not has_budget_word, ctx
            assert budget > 0 and not effective_pause, ctx
            expected = ("scheduler is not running" if not up else "max_parallel (2) runs are busy" if free <= 0
                        else "starts on the next tick")
            assert st.main == f"queued: {expected}" and word.endswith(f", {unread} unread"), ctx
        else:
            assert st.kind in ("waiting", "working", "idle") and not (has_queued_word or has_pause_word or has_budget_word), ctx
            assert st.kind == ("waiting" if out_n else "working" if open_n else "idle"), ctx
    assert n == 2 * 2 * 4 * 2 * 2 * 2 * 2 * 2


def test_specific_state_words() -> None:
    kw = dict(open_tasks=0, delegated=0, scheduler_up=True, free_slots=1, max_parallel=2)
    # paused wins over queued: the old 'queued: paused: ...' is gone
    st = classify(running=False, unread=1, paused="2 consecutive failed runs", budget=1, **kw)  # type: ignore[arg-type]
    assert st.word == "paused: 2 consecutive failed runs, 1 unread" and st.kind == "paused"
    # a reason that already says 'paused' is not prefixed again
    assert classify(running=False, unread=0, paused="paused by the user: window closed", budget=1, **kw).word == "paused by the user: window closed"  # type: ignore[arg-type]
    # out of budget wins over queued
    st = classify(running=False, unread=3, paused=None, budget=0, **kw)  # type: ignore[arg-type]
    assert (st.kind, st.word) == ("budget", "out of budget, 3 unread")
    # and over a pause that only says 'budget'
    assert classify(running=False, unread=1, paused="budget", budget=0, **kw).word == "out of budget, 1 unread"  # type: ignore[arg-type]
    # a stale 'budget' pause with budget granted since: the scheduler starts it -> queued
    assert classify(running=False, unread=1, paused="budget", budget=2, **kw).kind == "queued"  # type: ignore[arg-type]
    # a running agent keeps running; mail waits for the next run; a pause is announced
    st = classify(running=True, unread=2, paused="broken", budget=1, elapsed_s=61, **kw)  # type: ignore[arg-type]
    assert (st.kind, st.word) == ("running", "running 1m01s, +2 unread, then paused: broken")
    assert st.reason == "its current run is still going; the next run starts after it"
    # queued, with each reason
    assert classify(running=False, unread=1, paused=None, budget=1, **{**kw, "scheduler_up": False}).main == "queued: scheduler is not running"  # type: ignore[arg-type]
    assert classify(running=False, unread=1, paused=None, budget=1, **{**kw, "free_slots": 0}).main == "queued: max_parallel (2) runs are busy"  # type: ignore[arg-type]
    assert classify(running=False, unread=1, paused=None, budget=1, **kw).main == "queued: starts on the next tick"  # type: ignore[arg-type]


def test_the_short_form_of_a_queued_state_is_for_a_narrow_tree() -> None:
    kw = dict(open_tasks=0, delegated=0, free_slots=1, max_parallel=2, unread=1, paused=None, budget=1, running=False)
    assert classify(scheduler_up=False, **kw).short == "queued: scheduler off"  # type: ignore[arg-type]
    assert classify(scheduler_up=True, **{**kw, "free_slots": 0}).short == "queued: all slots busy"  # type: ignore[arg-type]
    assert classify(scheduler_up=True, **kw).short == "queued: next tick"  # type: ignore[arg-type]
    assert classify(scheduler_up=True, **{**kw, "unread": 0}).short == ""  # type: ignore[arg-type]


def test_a_state_is_its_main_words_and_its_note() -> None:
    assert AgentState("idle", "idle").word == "idle" and AgentState("paused", "paused: x", ", 2 unread").word == "paused: x, 2 unread"
