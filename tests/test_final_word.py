"""Final word on a task: `blocked` can be re-reported (superseded), `done`/`failed` are final (D1), and
runtime-only/failed runs do not make an agent `expensive` (D3)."""

import asyncio
from datetime import datetime, timedelta, timezone

import pytest

from orgmcp import core
from orgmcp.core import ROOT, OrgError, latest_results
from orgmcp.health import agent_health
from orgmcp.review import review
from orgmcp.server import build_server

ENG = "ceo/eng"
CRITERIA = "exactly 33 words; a non-author reviews the final text"
T0 = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)


@pytest.fixture
def clock(monkeypatch):
    """Frozen time for health (`now`), advancing 1 ms per call so message ids stay ordered."""

    class Clock:
        t = T0

        def __call__(self):
            self.t += timedelta(milliseconds=1)
            return self.t

    c = Clock()
    monkeypatch.setattr(core, "utcnow", c)
    return c


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


def results_for(org, task):
    return sorted((m for m in org.received(ROOT) if m.type == "result" and m.reply_to == task.id), key=lambda m: m.id)


# ------------------------------------------------------------------ report


def test_blocked_can_be_re_reported_and_the_new_result_supersedes_it(org, blocked):
    task, _, first, _ = blocked
    assert first.supersedes is None
    second = org.report("ceo", task.id, "done", "reviewed the final text; all criteria met")
    assert second.supersedes == first.id and second.status == "done"
    stored = org.find_received(ROOT, second.id)
    assert stored.supersedes == first.id
    assert "supersedes: " + first.id in stored.render()
    assert f"supersedes: {first.id}" in stored.path.read_text()
    assert [m.id for m in results_for(org, task)] == [first.id, second.id]


def test_second_re_report_after_a_resolved_blocker_is_refused(org, blocked):
    task, *_ = blocked
    org.report("ceo", task.id, "done", "all criteria met")
    with pytest.raises(OrgError, match="already reported done.*final.*rule 6.*`send`"):
        org.report("ceo", task.id, "done", "again")
    with pytest.raises(OrgError, match="already reported done"):
        org.report("ceo", task.id, "blocked", "or not")


def test_blocked_may_be_re_reported_blocked_once_per_prior_blocked(org, blocked):
    task, _, first, _ = blocked
    second = org.report("ceo", task.id, "blocked", "still waiting for a reviewer")
    assert second.supersedes == first.id
    third = org.report("ceo", task.id, "failed", "giving up")
    assert third.supersedes == second.id
    with pytest.raises(OrgError, match="already reported failed.*final"):
        org.report("ceo", task.id, "done", "no")


@pytest.mark.parametrize("status", ["done", "failed"])
def test_done_and_failed_are_final(org, status):
    task = org.delegate(ROOT, "ceo", "Job", "g", "a", budget=5)
    drain(org, "ceo")
    org.report("ceo", task.id, status, "x")
    with pytest.raises(OrgError, match=f"already reported {status}.*final"):
        org.report("ceo", task.id, "done", "y")
    assert all(m.supersedes is None for m in org.sent("ceo"))


def test_report_docstring_and_rules_state_the_new_rule(org):
    tools = asyncio.run(build_server(org, "ceo").list_tools())
    doc = next(t for t in tools if t.name == "report").description
    assert "final" in doc and "blocked" in doc and "supersedes" in doc and "once per blocked" in doc
    rules = org.rules()
    assert "`done` and `failed` are final" in rules and "`blocked` is not final" in rules
    assert "never changes a task's outcome" in rules and "unless you verified them" in rules


# ------------------------------------------------------- latest status derivation


def test_latest_results_picks_the_highest_id_per_task(org, blocked):
    task, _, first, _ = blocked
    second = org.report("ceo", task.id, "done", "ok")
    latest = latest_results(org.sent("ceo"))
    assert latest[task.id].id == second.id
    assert latest_results([first]) == {task.id: first}


def test_blocked_task_is_answered_not_open_but_state_says_it_can_be_re_reported(org, blocked):
    task, *_ = blocked
    assert task.id not in {t.id for t in org.open_tasks("ceo")}  # answered: it does not keep the scheduler busy
    assert task.id not in {t.id for t in org.outstanding(ROOT)}
    state = org.whoami("ceo")
    assert "reported blocked; you may re-report it once the blocker is resolved" in state
    assert f'{task.id} "Strict blurb"' in state and CRITERIA in state  # the contract to meet is in front of it
    org.report("ceo", task.id, "done", "all criteria met")
    assert "reported blocked" not in org.whoami("ceo")


def test_state_summary_does_not_repeat_a_blocked_task_shown_in_the_batch(org, blocked):
    task, *_ = blocked
    assert CRITERIA not in org.state_summary("ceo", {task.id})
    assert "full text: see the new messages below" in org.state_summary("ceo", {task.id})


def test_health_counts_a_task_once_by_its_latest_status(org, clock):
    ids = []
    for i in range(3):
        t = org.delegate(ROOT, ENG, f"Job {i}", "g", "a", budget=3)
        org.begin_run(ENG)
        ids.append(t.id)
    org.report(ENG, ids[0], "blocked", "waiting")
    org.report(ENG, ids[0], "done", "unblocked")  # blocked, then done: one done
    org.report(ENG, ids[1], "blocked", "waiting")
    org.report(ENG, ids[1], "blocked", "still waiting")  # blocked twice: one blocked
    org.report(ENG, ids[2], "failed", "no")
    h = agent_health(org, ENG, T0)
    assert (h.done, h.blocked, h.failed, h.open_tasks) == (1, 1, 1, 0)


def test_low_quality_and_review_use_the_latest_status(org, clock):
    for i in range(3):
        t = org.delegate(ROOT, ENG, f"Job {i}", "g", "a", budget=3)
        org.begin_run(ENG)
        org.report(ENG, t.id, "blocked", "waiting")
    assert "low_quality" in agent_health(org, ENG, T0).flags
    assert "low_quality" in review(org, T0, dry_run=True).render(dry_run=True)
    # every blocker is resolved by a later done: the agent is no longer low quality
    for t in [m for m in org.received(ENG) if m.type == "task"]:
        org.report(ENG, t.id, "done", "resolved")
    h = agent_health(org, ENG, T0)
    assert (h.done, h.blocked) == (3, 0) and "low_quality" not in h.flags
    assert "low_quality" not in review(org, T0, dry_run=True).render(dry_run=True)


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


# -------------------------------------------------------------- D3: expensive


def run_log(org, addr, n, senders="root", tail="\n# exit 0 after 2s\n", base=100):
    d = org.dir(addr) / "runs"
    d.mkdir(exist_ok=True)
    start = T0 + timedelta(seconds=base + n * 100)
    p = d / f"{start:%Y%m%dT%H%M%S%f}.log"
    p.write_text(f"# run of {addr}, 1 message(s)\n# senders: {senders}\n# cmd: x\n# ---- prompt ----\nP\n# ---- output ----\n{tail}")
    return p


def one_result(org, addr=ENG):
    t = org.delegate(ROOT, addr, "Job", "g", "a", budget=20)
    org.begin_run(addr)
    org.report(addr, t.id, "done", "ok")


def test_expensive_ignores_runtime_only_and_failed_runs_per_completed_task(org, clock):
    one_result(org)
    for i in range(4):
        run_log(org, ENG, i)  # four ordinary runs for one completed task: 4.0, under the limit of 5
    for i in range(4, 8):
        run_log(org, ENG, i, senders="runtime")  # stall reminders, reviews, refunds
    for i in range(8, 10):
        run_log(org, ENG, i, tail="\n# killed after 60s timeout\n")  # failed runs
    h = agent_health(org, ENG, T0 + timedelta(days=1))
    assert h.runs_used == 10  # budget truth is unchanged
    assert h.runs_per_task == 4.0 and "expensive" not in h.flags
    assert (h.runtime_runs, h.failed_runs) == (4, 2)


def test_expensive_still_fires_on_the_agents_own_runs(org, clock):
    one_result(org)
    for i in range(6):
        run_log(org, ENG, i)
    h = agent_health(org, ENG, T0 + timedelta(days=1))
    assert h.runs_per_task == 6.0 and "6.0 runs per completed task" in h.flags["expensive"]


def test_runs_without_result_ignores_runtime_only_and_failed_runs(org, clock):
    t = org.delegate(ROOT, ENG, "Job", "g", "a", budget=20)
    org.begin_run(ENG)
    for i in range(4):
        run_log(org, ENG, i)
    for i in range(4, 9):
        run_log(org, ENG, i, senders="runtime")
    run_log(org, ENG, 9, tail="\n# failed to start: nope\n")
    h = agent_health(org, ENG, T0 + timedelta(days=1))
    assert t.id and h.runs_used == 10 and "expensive" not in h.flags
    for i in range(10, 13):
        run_log(org, ENG, i)  # three more of its own: 7 > 6
    assert "7 runs without a result" in agent_health(org, ENG, T0 + timedelta(days=1)).flags["expensive"]
