"""The legacy functions of ``progress``: the permanent ``progress(org, task_id)`` of the README, ``describe_progress``, ``work_in_flight`` and the private names that
the dashboard, the scheduler and ``observe`` still import. The texts are pinned by ``tests/test_progress``, ``test_progress_wait`` and the golden suite
(unchanged); here are the seams: they build the reporter over the runtime in force, and take the waits of their caller."""

from __future__ import annotations

import dataclasses
import inspect
import time
from collections.abc import Collection
from pathlib import Path

import pytest

from orgmcp import progress as progress_module
from orgmcp.app import Org
from orgmcp.eligibility import RunnableQuery
from orgmcp.kernel import ROOT
from orgmcp.progress import describe_progress, progress, work_in_flight

RED = pytest.mark.xfail(strict=True, reason="red: C-progress")


class Runnable(RunnableQuery):
    """What may start is what the test says."""

    def __init__(self, *startable: str) -> None:
        self.startable_agents = set(startable)

    def runnable(self, exclude: Collection[str] = ()) -> list[str]:
        return sorted(self.startable_agents - set(exclude))

    def startable(self, addr: str) -> bool:
        return addr in self.startable_agents


@pytest.fixture
def org(tmp_path: Path) -> Org:
    made = Org.init(tmp_path / "org", "mission")
    made.hire("root", "ceo", "Chief", "Run it.")
    return made


def test_the_permanent_function_keeps_its_signature() -> None:
    parameters = inspect.signature(progress).parameters
    assert list(parameters) == ["org", "task_id", "now", "wait_seconds", "poll", "sleep", "clock"]
    assert [p.default for p in parameters.values()][1:] == [None, None, 0, 2.0, time.sleep, time.monotonic]
    assert parameters["wait_seconds"].kind is inspect.Parameter.KEYWORD_ONLY and parameters["org"].default is inspect.Parameter.empty


@RED
def test_the_function_says_what_the_reporter_of_the_runtime_says(org: Org) -> None:
    org.delegate(ROOT, "ceo", "Ship it", "Ship", "Shipped", budget=3)
    assert progress(org) == org.runtime.progress_reporter.progress() and "working" in progress(org)
    assert describe_progress(org) == org.runtime.progress_reporter.describe_progress()
    assert work_in_flight(org) is org.runtime.progress_reporter.work_in_flight() is True


def test_the_waits_of_the_caller_are_the_clock_of_the_wait(org: Org) -> None:
    org.delegate(ROOT, "ceo", "Ship it", "Ship", "Shipped", budget=3)
    slept: list[float] = []
    now = [0.0]

    def sleep(seconds: float) -> None:
        slept.append(seconds)
        now[0] += seconds

    assert progress(org, wait_seconds=5, poll=2, sleep=sleep, clock=lambda: now[0]).startswith("Waited 5s:")
    assert slept == [2, 2, 1]


def test_the_function_asks_the_runnable_query_of_the_runtime_in_force(org: Org) -> None:
    org.delegate(ROOT, "ceo", "Ship it", "Ship", "Shipped", budget=1)
    org.start_run_log("ceo")  # its one run is used: nothing can start
    org.begin_run("ceo")
    org.end_run("ceo", ok=True)
    org.report("ceo", org.sent(ROOT)[0].id, "blocked", "stuck")
    assert work_in_flight(org) is False
    org.runtime = dataclasses.replace(org.runtime, runnable_query=Runnable("ceo"))
    assert work_in_flight(org) is True


def test_a_running_agent_could_run_whatever_the_runnable_query_says(org: Org) -> None:
    org.delegate(ROOT, "ceo", "Ship it", "Ship", "Shipped", budget=1)
    org.begin_run("ceo")
    org.runtime = dataclasses.replace(org.runtime, runnable_query=Runnable())
    assert progress_module._can_run(org, "ceo") is True


@RED
def test_human_items_are_the_queue_of_the_package(org: Org) -> None:
    sent = org.send("ceo", ROOT, "I need 2 more runs", title="Budget request")
    assert progress_module._human_items(org) == [
        (sent.id, f'Needs you: note from ceo "Budget request": I need 2 more runs (message {sent.id})')
    ]
    assert org.runtime.human_queue.lines() == [line for _, line in progress_module._human_items(org)]
    assert not hasattr(progress_module, "_needs_human")


def test_the_private_names_of_the_dashboard_answer_as_before(org: Org) -> None:
    task = org.delegate(ROOT, "ceo", "Ship it", "Ship", "Shipped", budget=3)
    team = ["ceo"]
    assert progress_module._state(org, task, None, team) == ("working", "unread work: ceo")
    assert progress_module._runs(org, task, None, team) == "runs 0 of 3"
    assert progress_module._last_activity(org, team) is not None
    assert progress_module._section("## Summary\nx\n## Artifacts\n- a.md (2 words)", "artifacts") == ["- a.md (2 words)"]
    result = org.report("ceo", task.id, "done", "ok")
    assert progress_module._artifacts(result) == []
