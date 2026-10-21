"""Contract of ``HumanQueue``: the unread messages of root that wait for a decision, as one line each, oldest first.

Listed: a ``blocked`` or ``failed`` result, and every note or runtime notice that wakes (questions, budget requests, escalations). Not listed: a ``done``
result (the task line already says it), a message that does not wake (budget returned, refunds, news of a playbook or a contract), and anything root has
already read. Over mailboxes on disk and in memory."""

from __future__ import annotations

from pathlib import Path

import pytest

from hirearchy.attention import HumanQueue
from hirearchy.attention.testing import IMPLEMENTATIONS, AttentionWorld
from hirearchy.kernel import ROOT, RUNTIME, Message

from ._support import give, make_world


@pytest.fixture(params=IMPLEMENTATIONS[HumanQueue], ids=lambda factory: factory.__name__)
def w(request: pytest.FixtureRequest, tmp_path: Path) -> AttentionWorld:
    made = make_world(request, tmp_path)
    assert isinstance(made.queue, HumanQueue)
    return made


def note(w: AttentionWorld, sender: str, title: str, body: str, wakes: bool = True) -> Message:
    if sender != RUNTIME:
        w.hire(sender)
    return w.write(sender, ROOT, title, body, wakes)


# ------------------------------------------------------------------------------ what is listed


def test_there_is_nothing_to_decide_in_an_empty_inbox(w: AttentionWorld) -> None:
    assert w.queue.items() == [] and w.queue.lines() == []


def test_a_note_from_an_agent_is_a_line_with_its_id(w: AttentionWorld) -> None:
    sent = note(w, "ceo", "Budget request", "I need 2 more runs for the rework")
    assert w.queue.items() == [(sent.id, f'Needs you: note from ceo "Budget request": I need 2 more runs for the rework (message {sent.id})')]


def test_a_notice_of_the_runtime_is_a_runtime_notice(w: AttentionWorld) -> None:
    sent = note(w, RUNTIME, "ceo is out of budget", "`ceo` has 1 unread message and no runs left.\nGrant runs.")
    assert w.queue.items() == [
        (sent.id, f'Needs you: runtime notice "ceo is out of budget": `ceo` has 1 unread message and no runs left (message {sent.id})')
    ]


def test_the_first_line_of_a_note_that_has_text_is_what_is_shown(w: AttentionWorld) -> None:
    sent = note(w, "ceo", "Question", "\n\n   First line  with   spaces \nsecond line")
    assert w.queue.lines() == [f'Needs you: note from ceo "Question": First line with spaces (message {sent.id})']


def test_a_note_without_text_has_no_colon_after_the_title(w: AttentionWorld) -> None:
    sent = note(w, "ceo", "Ping", "")
    assert w.queue.lines() == [f'Needs you: note from ceo "Ping" (message {sent.id})']


def test_a_note_without_a_title_has_none(w: AttentionWorld) -> None:
    sent = note(w, "ceo", "", "hello")
    assert w.queue.lines() == [f"Needs you: note from ceo: hello (message {sent.id})"]


def test_a_blocked_result_is_listed_with_its_summary(w: AttentionWorld) -> None:
    task = give(w, "ceo", "Write the report", 5)
    result = w.answer(task, "blocked", "## Summary\n\nNeed the 2025 sales figures\n\n## Artifacts\n- none")
    assert w.queue.items() == [
        (result.id, f'Needs you: blocked result from ceo "re: Write the report": Need the 2025 sales figures (message {result.id})')
    ]


def test_a_failed_result_is_listed_with_its_summary(w: AttentionWorld) -> None:
    task = give(w, "ceo", "Gather data", 5)
    result = w.answer(task, "failed", "## Summary\nThe source site is gone.")
    assert w.queue.lines() == [f'Needs you: failed result from ceo "re: Gather data": The source site is gone (message {result.id})']


def test_a_result_without_a_summary_section_shows_its_first_line(w: AttentionWorld) -> None:
    task = give(w)
    result = w.answer(task, "blocked", "Cannot go on: no access.\nMore text.")
    assert w.queue.lines() == [f'Needs you: blocked result from ceo "re: Ship it": Cannot go on: no access (message {result.id})']


def test_the_summary_is_the_first_line_of_the_section_whatever_the_case_of_its_heading(w: AttentionWorld) -> None:
    task = give(w)
    result = w.answer(task, "failed", "Intro that is not shown\n## SUMMARY\n\n  the reason \nmore\n## Other\nnot this")
    assert w.queue.lines() == [f'Needs you: failed result from ceo "re: Ship it": the reason (message {result.id})']


def test_a_result_with_an_empty_body_has_no_text(w: AttentionWorld) -> None:
    task = give(w)
    result = w.answer(task, "blocked", "")
    assert w.queue.lines() == [f'Needs you: blocked result from ceo "re: Ship it" (message {result.id})']


def test_long_text_is_cut_to_a_line(w: AttentionWorld) -> None:
    sent = note(w, "ceo", "Long", "word " * 60)
    (line,) = w.queue.lines()
    shown = line.split(": ", 2)[2].rsplit(f" (message {sent.id})", 1)[0]
    assert len(shown) == 110 and shown.endswith("…") and shown.startswith("word word")


def test_the_period_that_ends_the_text_is_not_shown(w: AttentionWorld) -> None:
    sent = note(w, "ceo", "Short", "Done.")
    assert w.queue.lines() == [f'Needs you: note from ceo "Short": Done (message {sent.id})']


# ------------------------------------------------------------------------------ what is not listed


def test_a_done_result_is_not_listed(w: AttentionWorld) -> None:
    task = give(w)
    w.answer(task, "done", "## Summary\nAll done")
    assert w.queue.items() == []


def test_a_message_that_does_not_wake_is_not_listed(w: AttentionWorld) -> None:
    note(w, RUNTIME, "Budget returned from ceo/eng", "2 runs came back.", wakes=False)
    note(w, "ceo", "FYI", "no reply needed", wakes=False)
    assert w.queue.items() == []


def test_a_message_that_root_has_read_is_not_listed(w: AttentionWorld) -> None:
    note(w, "ceo", "Question", "yes or no?")
    w.begin_run(ROOT)
    w.end_run(ROOT)
    assert w.queue.items() == []


def test_a_message_to_someone_else_is_not_listed(w: AttentionWorld) -> None:
    w.hire("ceo")
    w.hire("ops")
    w.write("ceo", "ops", "Question", "to ops", True)
    assert w.queue.items() == []


# ------------------------------------------------------------------------------ order


def test_the_items_are_oldest_first_and_the_lines_follow_them(w: AttentionWorld) -> None:
    first = note(w, "ceo", "One", "first")
    task = give(w, "ceo", "T", 3)
    second = w.answer(task, "blocked", "second")
    third = note(w, RUNTIME, "Three", "third")
    note(w, "ceo", "Quiet", "quiet", wakes=False)
    assert [mid for mid, _ in w.queue.items()] == [first.id, second.id, third.id]
    assert w.queue.lines() == [line for _, line in w.queue.items()]


def test_asking_does_not_read_the_messages(w: AttentionWorld) -> None:
    note(w, "ceo", "One", "first")
    assert w.queue.items() == w.queue.items()
    assert len(w.inbox(ROOT)) == 1
