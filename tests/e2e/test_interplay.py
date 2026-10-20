import os
import re

import pytest
from testkit.e2e_world import agent_health
from testkit.legacy.orgmcp.app import wiring
from testkit.scheduler_loop import loop_over, runnable_of

from orgmcp import core
from orgmcp.core import ROOT, word_count
from orgmcp.kernel import AtomicWriter
from orgmcp.kernel.testing import FailingAtomicWriter, fs_atomic_writer

ENG = "ceo/eng"
HEAD = "Exact criteria: 33 words, acrostic PLANT."


def long_acceptance(n: int = 15000) -> str:
    return HEAD + "\nfiller " * (n // 7) + "\nTAIL-MARKER-END"


# ------------------------------------------------- long task bodies in prompts
def test_long_open_task_is_cut_in_the_state_with_a_readable_pointer(org):
    big = org.delegate(ROOT, "ceo", "Huge", "goal", long_acceptance(), budget=20)
    org.begin_run("ceo")
    org.end_run("ceo", ok=True)  # an old open task: shown by state_summary rather than as a new message
    prompt = org.run_prompt("ceo", [])
    assert HEAD in prompt and "TAIL-MARKER-END" not in prompt
    assert len(prompt) < 40_000
    pointer = re.search(r'read\(path="([^"]+)"\)', prompt).group(1)
    assert pointer == f"ceo/read/{big.id}.md"
    assert "TAIL-MARKER-END" in org.read(pointer)


def test_long_delegated_task_shown_with_its_result_points_at_the_senders_copy(org):
    org.delegate(ROOT, "ceo", "Parent", "goal", "crit", budget=20)
    org.begin_run("ceo")
    org.end_run("ceo", ok=True)
    sub = org.delegate("ceo", ENG, "Big sub", "goal", long_acceptance(), budget=4)
    result = org.report(ENG, sub.id, "done", "ok")
    prompt = org.run_prompt("ceo", [org.find_received("ceo", result.id)])
    assert HEAD in prompt and "TAIL-MARKER-END" not in prompt
    assert len(prompt) < 40_000
    pointer = re.search(r'read\(path="([^"]+)"\)', prompt).group(1)
    assert pointer == f"ceo/sent/{sub.id}.md"  # not eng/sent/..., which would not exist
    assert "TAIL-MARKER-END" in org.read(pointer)


def test_long_task_in_the_batch_uses_render_truncation_once(org):
    task = org.delegate(ROOT, "ceo", "Huge", "goal", long_acceptance(), budget=10)
    prompt = org.run_prompt("ceo", org.begin_run("ceo"))
    assert prompt.count("message cut") == 1 and "TAIL-MARKER-END" not in prompt
    assert f"ceo/inflight/{task.id}.md" in prompt


def test_short_bodies_are_not_cut(org):
    org.delegate(ROOT, "ceo", "Small", "goal", "crit", budget=10)
    assert "message cut" not in org.run_prompt("ceo", org.begin_run("ceo"))


# --------------------------------------------- retire refund vs health/scheduler
def _retire_with_refund(org):
    org.delegate(ROOT, "ceo", "T", "g", "a", budget=20)
    org.begin_run("ceo")
    org.end_run("ceo", ok=True)
    org.hire("ceo", "ops", "Ops", "Do ops.")
    org.send("ceo", "ceo/ops", "grant", budget=5)
    return org.retire_team("ceo", "ops", "done")


def test_refund_note_is_not_rework_or_a_quality_problem(org):
    ret = _retire_with_refund(org)
    assert ret.refunded == 5
    h = agent_health(org, "ceo")
    assert h.rework == 0 and h.failed == 0 and h.blocked == 0 and "low_quality" not in h.flags
    assert h.tasks_received == 1  # only the real task; the note is not a task
    assert h.budget_received >= 5  # but the budget it carries is counted as received
    note = [m for m in org.messages("ceo", "inbox") if m.title.startswith("Budget returned")][0]
    assert note.type == "note" and note.sender == core.RUNTIME and not note.revises and note.reply_to is None


def test_refund_note_wakes_a_budget_paused_parent_but_not_a_failure_paused_one(org):
    org.delegate(ROOT, "ceo", "T", "g", "a", budget=20)
    org.hire("ceo", "ops", "Ops", "Do ops.")
    org.send("ceo", "ceo/ops", "grant", budget=5)
    sched = loop_over(org, echo=lambda _: None)
    org.pause("ceo", "3 consecutive failed runs")
    org.retire_team("ceo", "ops", "done")
    assert org.unread("ceo") >= 1 and "ceo" not in runnable_of(org, sched)  # a human-only pause stays paused
    org.resume("ceo")
    org.pause("ceo", "budget")
    assert "ceo" in runnable_of(org, sched)  # budget came back with the note, so a budget pause is lifted


def test_runtime_only_refund_run_is_not_counted_as_wasteful(org):
    _retire_with_refund(org)
    org.notify("ceo", "reminder: T", "still open")  # the refund note alone no longer wakes (tests/test_wakes.py)
    assert [m.sender for m in org.messages("ceo", "inbox")] == [core.RUNTIME] * 2
    sched = loop_over(org, runner=lambda o, a, p: (["true"], str(o.dir(a)), dict(os.environ)), echo=lambda _: None)
    sched.serve(until_idle=True, max_runs=1)
    h = agent_health(org, "ceo")
    assert h.runs_used == 1 and h.runtime_runs == 1 and h.empty_runs == 0 and "wasteful" not in h.flags


# ------------------------------------------------------------------ word counts
def test_artifact_annotation_and_read_use_the_same_markdown_aware_count(org):
    md = "# Title\n\n- one two\n- three\n\n---\n\n| a | b |\n|---|---|\n"
    path = org.dir("ceo") / "work"
    path.mkdir(exist_ok=True)
    (path / "doc.md").write_text(md, encoding="utf-8")
    expected = word_count(md)
    assert expected != len(md.split())  # the markers matter for this file
    task = org.delegate(ROOT, "ceo", "T", "g", "a", budget=5)
    result = org.report("ceo", task.id, "done", "ok", ["ceo/work/doc.md"])
    assert f"{expected} words" in result.body
    assert f"{expected} words" in org.read("ceo/work/doc.md")


# ------------------------------------------------- Message.load cache vs deliver
def test_cache_stays_correct_across_redelivery_and_inflight_moves(org):
    armed = {"on": True}

    def flaky(path):
        return armed["on"] and "/ceo/eng/inbox/" in str(path)

    org.runtime = wiring.open_runtime(org.root, {AtomicWriter: FailingAtomicWriter(fs_atomic_writer(org.root).writer, fails=flaky, error=OSError("disk full"))})
    org.delegate(ROOT, "ceo", "T", "g", "a", budget=10)
    with pytest.raises(OSError):
        org.send("ceo", ENG, "grant", budget=4)
    armed["on"] = False
    sent = [m for m in org.messages("ceo", "sent") if m.to == ENG]  # parses (and caches) the sender copy
    assert [m.budget for m in sent] == [4] and org.unread(ENG) == 0
    org.recover()
    got = org.messages(ENG, "inbox")
    assert [(m.id, m.budget, m.body) for m in got] == [(sent[0].id, 4, "grant")]
    org.begin_run(ENG)
    assert [m.id for m in org.messages(ENG, "inflight")] == [sent[0].id]
    org.end_run(ENG, ok=False)
    assert [m.id for m in org.messages(ENG, "inbox")] == [sent[0].id]
    assert org.budget(ENG) == 4 and org.budget("ceo") == 6
