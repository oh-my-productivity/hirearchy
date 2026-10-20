# mypy: ignore-errors
# A test moved from tests/ by refactor step E1: not type-checked strictly (production code is). Delete the first line when this file is typed.

import pytest
from testkit.reach.orgmcp.core import ROOT

ENG = "ceo/eng"
CRITERIA = "exactly 33 words; a non-author reviews the final text"


def drain(org, addr):
    org.begin_run(addr)
    org.end_run(addr, ok=True)


@pytest.fixture
def blocked(org):
    """root -> ceo task; ceo delegated to eng (serving it); eng reported done; ceo reported the root task blocked."""
    task = org.delegate(ROOT, "ceo", "Strict blurb", "Write it.", CRITERIA, budget=20)
    drain(org, "ceo")
    sub = org.delegate("ceo", ENG, "Draft blurb", "Draft it.", "exactly 33 words", budget=4)
    first = org.report("ceo", task.id, "blocked", "review judged a stale draft; no budget to rework")
    result = org.report(ENG, sub.id, "done", "33 words")
    return task, sub, first, result


def test_state_summary_does_not_repeat_a_blocked_task_shown_in_the_batch(org, blocked):
    task, *_ = blocked
    assert CRITERIA not in org.state_summary("ceo", {task.id})
    assert "full text: see the new messages below" in org.state_summary("ceo", {task.id})


# ------------------------------------------------------------- prompt guard
def prompt_with_result(org, task, sub, result):
    return org.run_prompt("ceo", [org.find_received("ceo", result.id)])


def test_guard_when_the_upstream_task_is_already_reported_done(org):
    task = org.delegate(ROOT, "ceo", "Strict blurb", "Write it.", CRITERIA, budget=20)
    drain(org, "ceo")
    sub = org.delegate("ceo", ENG, "Draft blurb", "Draft it.", "exactly 33 words", budget=4)
    org.report("ceo", task.id, "done", "all good")
    result = org.report(ENG, sub.id, "done", "33 words")
    prompt = prompt_with_result(org, task, sub, result)
    assert f'serves your task {task.id} "Strict blurb", which you already reported done: that is final' in prompt
    assert "Do not claim in a note that its criteria are met" in prompt
    assert "information only" in prompt and "probably serves your open task" not in prompt


def test_guard_when_the_upstream_task_is_already_reported_failed(org):
    task = org.delegate(ROOT, "ceo", "Strict blurb", "Write it.", CRITERIA, budget=20)
    drain(org, "ceo")
    sub = org.delegate("ceo", ENG, "Draft blurb", "Draft it.", "exactly 33 words", budget=4)
    org.report("ceo", task.id, "failed", "gave up")
    prompt = prompt_with_result(org, task, sub, org.report(ENG, sub.id, "done", "33 words"))
    assert "which you already reported failed: that is final" in prompt
    assert "Do not claim in a note" in prompt


def test_guard_when_the_upstream_task_is_reported_blocked(org, blocked):
    task, sub, _, result = blocked
    prompt = prompt_with_result(org, task, sub, result)
    assert f'serves your task {task.id} "Strict blurb", which you already reported blocked. That is not final' in prompt
    assert "you may `report` it again, once, if the blocker is resolved" in prompt
    assert "rule 6" in prompt and "required review of the FINAL version" in prompt
    assert "Do not claim in a note that criteria are met" in prompt
    assert "that is final" not in prompt.split("# New messages")[1]
    assert "reported blocked; you may re-report it once the blocker is resolved" in prompt  # in the state block


def test_guard_is_silent_when_the_upstream_task_is_ambiguous(org, blocked):
    # a second task that was open before the next delegation: two candidates, so no link is guessed
    other = org.delegate(ROOT, "ceo", "Other job", "g", "a", budget=3)
    drain(org, "ceo")
    sub2 = org.delegate("ceo", ENG, "Second draft", "g", "a", budget=1)
    res2 = org.report(ENG, sub2.id, "done", "ok")
    prompt = prompt_with_result(org, other, sub2, res2)
    assert "probably serves" not in prompt and "already reported" not in prompt
