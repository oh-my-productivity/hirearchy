"""Contract of ``TraceStamper``: each rule, in order, over the mailboxes on disk and over the in-memory ones.

``given > new > link > open-task > batch > ambiguous``: the first rule that matches decides, and a message lands in the same trace
as the task it answers or reworks, however the chain runs."""

from __future__ import annotations

from pathlib import Path

import pytest

from orgmcp.kernel import Message
from orgmcp.traces import TraceStamper
from orgmcp.traces.testing import IMPLEMENTATIONS, TraceHarness

from ._support import RED, make, message, put, result

pytestmark = RED


@pytest.fixture(params=IMPLEMENTATIONS[TraceStamper], ids=lambda factory: factory.__name__)
def h(request: pytest.FixtureRequest, tmp_path: Path) -> TraceHarness:
    made = make(request, tmp_path)
    assert isinstance(made.stamper, TraceStamper)
    return made


def stamp(h: TraceHarness, msg: Message) -> tuple[str, list[str]]:
    return h.stamper.stamp(msg)


# ------------------------------------------------------------------------------ given


def test_given_a_trace_that_is_set_is_kept(h: TraceHarness) -> None:
    msg = message("runtime", "ceo", "note", trace="T9")
    assert stamp(h, msg) == ("given", []) and msg.trace == "T9"


def test_given_beats_every_other_rule(h: TraceHarness) -> None:
    msg = message("root", "ceo", "task", trace="T9")  # a root task would be "new"
    assert stamp(h, msg) == ("given", []) and msg.trace == "T9"


# ------------------------------------------------------------------------------ new


def test_new_a_root_task_is_its_own_trace(h: TraceHarness) -> None:
    msg = message("root", "ceo", "task")
    assert stamp(h, msg) == ("new", []) and msg.trace == msg.id


def test_new_beats_link_for_a_root_task_that_answers_something(h: TraceHarness) -> None:
    earlier = put(h, "root", "sent", 1, sender="root", to="ceo", trace="OLD")
    msg = message("root", "ceo", "task", reply_to=earlier)
    assert stamp(h, msg) == ("new", []) and msg.trace == msg.id


def test_new_the_root_sender_may_be_spelled_differently(h: TraceHarness) -> None:
    msg = message(" /root/ ", "ceo", "task")
    assert stamp(h, msg) == ("new", []) and msg.trace == msg.id


def test_a_root_task_that_revises_one_does_not_start_a_trace(h: TraceHarness) -> None:
    first = put(h, "root", "sent", 1, sender="root", to="ceo", trace="T1")
    msg = message("root", "ceo", "task", revises=first)
    assert stamp(h, msg) == ("link", []) and msg.trace == "T1" != msg.id


def test_a_root_note_is_no_new_trace(h: TraceHarness) -> None:
    msg = message("root", "ceo", "note")
    assert stamp(h, msg) == ("ambiguous", []) and msg.trace is None


# ------------------------------------------------------------------------------ link


def test_link_an_answer_follows_the_message_it_answers(h: TraceHarness) -> None:
    task = put(h, "ceo", "read", 1, trace="T1")
    msg = message("ceo", "root", "result", reply_to=task, status="done")
    assert stamp(h, msg) == ("link", []) and msg.trace == "T1"


def test_link_a_plain_note_may_link_through_reply_to(h: TraceHarness) -> None:
    task = put(h, "ceo", "inbox", 1, trace="T1")
    msg = message("ceo", "root", "note", reply_to=task)
    assert stamp(h, msg) == ("link", []) and msg.trace == "T1"


def test_link_a_rework_stays_in_the_trace_of_the_task_it_revises(h: TraceHarness) -> None:
    sub = put(h, "ceo", "sent", 1, sender="ceo", to="ceo/eng", trace="T1")
    msg = message("ceo", "ceo/eng", "task", revises=sub)
    assert stamp(h, msg) == ("link", []) and msg.trace == "T1"


def test_link_reply_to_is_tried_before_revises(h: TraceHarness) -> None:
    a = put(h, "ceo", "inbox", 1, trace="A")
    b = put(h, "ceo", "sent", 2, sender="ceo", to="ceo/eng", trace="B")
    msg = message("ceo", "ceo/eng", "task", reply_to=a, revises=b)
    assert stamp(h, msg) == ("link", []) and msg.trace == "A"


def test_link_falls_through_to_revises_when_the_replied_message_has_no_trace(h: TraceHarness) -> None:
    a = put(h, "ceo", "inbox", 1)  # unstamped
    b = put(h, "ceo", "sent", 2, sender="ceo", to="ceo/eng", trace="B")
    msg = message("ceo", "ceo/eng", "task", reply_to=a, revises=b)
    assert stamp(h, msg) == ("link", []) and msg.trace == "B"


def test_link_falls_through_to_the_context_when_the_linked_message_has_no_trace(h: TraceHarness) -> None:
    old = put(h, "ceo", "inbox", 1, kind="note")  # unstamped: an old message
    put(h, "ceo", "read", 2, trace="T1")  # but the agent has an open task of one trace
    msg = message("ceo", "root", "result", reply_to=old, status="done")
    assert stamp(h, msg) == ("open-task", []) and msg.trace == "T1"


def test_link_to_an_unstamped_message_without_any_context_is_ambiguous(h: TraceHarness) -> None:
    old = put(h, "ceo", "inbox", 1)
    msg = message("ceo", "root", "result", reply_to=old, status="done")
    assert stamp(h, msg) == ("ambiguous", []) and msg.trace is None


def test_link_looks_in_the_boxes_of_the_sender_only(h: TraceHarness) -> None:
    other = put(h, "ceo/eng", "inbox", 1, trace="T1")
    msg = message("ceo", "root", "note", reply_to=other)
    assert stamp(h, msg) == ("ambiguous", []) and msg.trace is None


def test_link_a_reference_that_is_a_path_is_not_followed(h: TraceHarness) -> None:
    real = put(h, "ceo", "inbox", 1, trace="T1", kind="note")  # a note: no open task gives the context its trace
    msg = message("ceo", "root", "note", reply_to=f"../inbox/{real}")
    assert stamp(h, msg) == ("ambiguous", []) and msg.trace is None


def test_the_runtime_never_links(h: TraceHarness) -> None:
    task = put(h, "runtime", "sent", 1, sender="runtime", to="ceo", trace="T1")
    msg = message("runtime", "ceo", "note", reply_to=task, revises=task)
    assert stamp(h, msg) == ("ambiguous", []) and msg.trace is None


def test_the_runtime_has_no_context_either(h: TraceHarness) -> None:
    put(h, "ceo", "inbox", 1, trace="T1")
    msg = message("runtime", "ceo", "note")
    assert stamp(h, msg) == ("ambiguous", []) and msg.trace is None


# ------------------------------------------------------------------------------ open-task, batch, ambiguous


def test_open_task_a_manager_stamps_what_it_sends_with_the_trace_of_its_open_tasks(h: TraceHarness) -> None:
    put(h, "ceo", "inbox", 1, trace="T1")
    put(h, "ceo", "read", 2, trace="T1")
    msg = message("ceo", "ceo/eng", "task")
    assert stamp(h, msg) == ("open-task", []) and msg.trace == "T1"


def test_open_task_counts_a_blocked_task_as_open(h: TraceHarness) -> None:
    task = put(h, "ceo", "read", 1, trace="T1")
    result(h, "ceo", 2, task, "blocked")
    msg = message("ceo", "ceo/eng", "note")
    assert stamp(h, msg) == ("open-task", []) and msg.trace == "T1"


def test_open_task_is_skipped_when_an_open_task_has_no_trace(h: TraceHarness) -> None:
    put(h, "ceo", "inbox", 1)  # unstamped open task
    put(h, "ceo", "inflight", 2, trace="T1")
    msg = message("ceo", "ceo/eng", "task")
    assert stamp(h, msg) == ("batch", []) and msg.trace == "T1"


def test_batch_picks_the_one_trace_of_the_current_batch(h: TraceHarness) -> None:
    put(h, "ceo", "read", 1, trace="A")
    put(h, "ceo", "inflight", 2, trace="B")  # open tasks: A and B (two traces); the batch has only B
    msg = message("ceo", "ceo/eng", "note")
    assert stamp(h, msg) == ("batch", []) and msg.trace == "B"


def test_ambiguous_leaves_the_trace_empty_and_lists_every_candidate_sorted(h: TraceHarness) -> None:
    put(h, "ceo", "inflight", 1, trace="B")
    put(h, "ceo", "inflight", 2, trace="A")
    put(h, "ceo", "read", 3, trace="C")
    msg = message("ceo", "ceo/eng", "note")
    assert stamp(h, msg) == ("ambiguous", ["A", "B", "C"]) and msg.trace is None


def test_ambiguous_a_sender_without_context_has_no_candidates(h: TraceHarness) -> None:
    for sender in ("root", "ceo", "ghost"):
        msg = message(sender, "ceo", "note")
        assert stamp(h, msg) == ("ambiguous", []) and msg.trace is None


def test_the_sender_may_be_spelled_differently(h: TraceHarness) -> None:
    put(h, "ceo", "inbox", 1, trace="T1")
    msg = message(" /ceo/ ", "ceo/eng", "task")
    assert stamp(h, msg) == ("open-task", []) and msg.trace == "T1"


# ------------------------------------------------------------------------------ the whole chain


def test_the_trace_follows_the_request_down_and_up(h: TraceHarness) -> None:
    top = message("root", "ceo", "task", n=1)
    assert stamp(h, top) == ("new", [])
    h.mail.put(f"ceo/inbox/{top.id}.md", top.to_text())
    h.mail.put(f"sent/{top.id}.md", top.to_text())
    sub = message("ceo", "ceo/eng", "task", n=2)
    assert stamp(h, sub) == ("open-task", []) and sub.trace == top.id
    h.mail.put(f"ceo/sent/{sub.id}.md", sub.to_text())
    h.mail.put(f"ceo/eng/inbox/{sub.id}.md", sub.to_text())
    up = message("ceo/eng", "ceo", "result", n=3, reply_to=sub.id, status="done")
    assert stamp(h, up) == ("link", []) and up.trace == top.id
    rework = message("ceo", "ceo/eng", "task", n=4, revises=sub.id)
    assert stamp(h, rework) == ("link", []) and rework.trace == top.id
