# mypy: ignore-errors
# A test moved from tests/ by refactor step E1: not type-checked strictly (production code is). Delete the first line when this file is typed.

import pytest
from testkit.reach.hirearchy.core import ROOT

from hirearchy.progress import WAIT_MAX, progress


@pytest.fixture(autouse=True)
def env(monkeypatch, tmp_path):
    for var in ("ORG_ROOT", "ORG_AGENT", "ORG_REQUIRE_AGENT"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("HIREARCHY_WORKSPACE_ROOTS", str(tmp_path))
    work = tmp_path / "cwd"
    (work / "<folder-with-your-files>").mkdir(parents=True)  # the documents example's input folder
    (work / "<folder-with-your-data>").mkdir()  # the analysis example's input folder
    monkeypatch.chdir(work)
    return work


# -------------------------------------------------------------------------------------- progress wait
class Clock:
    """A fake clock whose ``sleep`` advances time and can run an action at the n-th sleep."""

    def __init__(self, actions=None):
        self.now, self.sleeps, self.actions = 0.0, 0, actions or {}

    def __call__(self):
        return self.now

    def sleep(self, seconds):
        self.sleeps += 1
        self.now += seconds
        action = self.actions.get(self.sleeps)
        if action:
            action()


def waiting(org, clock, wait=60, poll=2.0, task_id=None):
    return progress(org, task_id, wait_seconds=wait, poll=poll, sleep=clock.sleep, clock=clock)


@pytest.fixture
def task(org):
    return org.delegate(ROOT, "ceo", "Write the report", "goal", "criteria", budget=8)


def test_wait_returns_when_a_task_finishes(org, task):
    def finish():
        org.begin_run("ceo")
        org.report("ceo", task.id, "done", "Finished.")
        org.end_run("ceo", ok=True)

    clock = Clock({3: finish})
    out = waiting(org, clock)
    first, *rest = out.splitlines()
    assert first == 'Changed after waiting 6s: "Write the report": working -> done'
    assert any(': done.' in line for line in rest) and clock.sleeps == 3


def test_wait_returns_when_a_task_is_blocked_and_says_why(org, task):
    def block_it():
        org.begin_run("ceo")
        org.report("ceo", task.id, "blocked", "Need the API key.")
        org.end_run("ceo", ok=True)

    out = waiting(org, Clock({1: block_it}))
    assert out.splitlines()[0].startswith('Changed after waiting 2s: "Write the report": working -> blocked: Need the API key')


def test_wait_returns_when_something_new_needs_the_human(org, task):
    org.begin_run("ceo")
    clock = Clock({2: lambda: org.send("ceo", ROOT, "May I spend 5 more runs?", title="Budget question")})
    out = waiting(org, clock)
    assert out.startswith("Changed after waiting 4s: new item for you: Needs you: note from ceo")
    assert "Budget question" in out.splitlines()[0]


def test_an_item_that_was_already_waiting_does_not_end_the_wait(org, task):
    org.begin_run("ceo")
    org.send("ceo", ROOT, "Old question", title="Old")
    out = waiting(org, Clock(), wait=10, poll=5)
    assert out.startswith("Waited 10s:") and "Old" in out  # still listed, but not a change


def test_wait_times_out_with_the_current_lines(org, task):
    clock = Clock()
    out = waiting(org, clock, wait=10, poll=3)
    assert out.startswith("Waited 10s: no task finished") and "progress(wait_seconds=" in out
    assert '"Write the report": working' in out
    assert clock.now == 10 and clock.sleeps == 4  # 3 + 3 + 3 + 1: never past the deadline


def test_wait_is_capped_at_900_seconds(org, task):
    clock = Clock()
    out = waiting(org, clock, wait=10**6, poll=300)
    assert out.startswith("Waited 15m") and clock.now == WAIT_MAX == 900 and clock.sleeps == 3


def test_wait_zero_or_negative_does_not_wait(org, task):
    for w in (0, -5):
        clock = Clock()
        assert waiting(org, clock, wait=w) == progress(org) and clock.sleeps == 0


def test_nothing_to_wait_for_when_every_task_is_finished(org, task):
    org.begin_run("ceo")
    org.report("ceo", task.id, "done", "Finished.")
    clock = Clock()
    out = waiting(org, clock)
    assert out.startswith("Nothing to wait for") and ": done." in out and clock.sleeps == 0


def test_a_stall_must_persist_for_two_looks_before_it_ends_the_wait(org, task):
    def reads_and_stops():  # ceo reads its task, then nothing happens: stalled
        org.begin_run("ceo")
        org.end_run("ceo", ok=True)

    clock = Clock({1: reads_and_stops})
    out = waiting(org, clock)
    assert out.splitlines()[0].startswith('Changed after waiting 4s: "Write the report": working -> stalled') and clock.sleeps == 2


def test_a_hand_over_that_looks_like_a_stall_once_is_ignored(org, task):
    def reads():
        org.begin_run("ceo")
        org.end_run("ceo", ok=True)

    clock = Clock({1: reads, 2: lambda: org.delegate("ceo", "ceo/eng", "Sub", "goal", "criteria", budget=3)})
    out = waiting(org, clock, wait=8)
    assert out.startswith("Waited 8s:")


def test_waiting_only_reads_files(org, task):
    def snapshot():
        return sorted((str(p), p.stat().st_mtime_ns, p.stat().st_size) for p in org.root.rglob("*") if p.is_file())

    before = snapshot()
    waiting(org, Clock(), wait=20, poll=2)
    assert snapshot() == before


def test_wait_for_one_task_ignores_the_others(org, task):
    other = org.delegate(ROOT, "ceo", "Other", "goal", "criteria", budget=2)

    def finish_other():
        org.begin_run("ceo")
        org.report("ceo", other.id, "done", "x")

    out = waiting(org, Clock({1: finish_other}), wait=6, poll=2, task_id=task.id)
    assert out.startswith("Waited 6s:")
