"""The permanent ``progress(org, task_id)`` of the README: it keeps its signature, says what the ``ProgressReporter`` of the runtime of its ``org`` says, and takes the
waits of its caller. The texts are pinned by ``progress/tests`` and the golden suite; here are the seams."""

from __future__ import annotations

import inspect
import time
from pathlib import Path

import pytest

from orgmcp.app import Org, wiring
from orgmcp.attention import HumanQueue
from orgmcp.attention.testing import ListHumanQueue
from orgmcp.kernel import ROOT
from orgmcp.progress import progress


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


def test_the_function_says_what_the_reporter_of_the_runtime_says(org: Org) -> None:
    org.delegate(ROOT, "ceo", "Ship it", "Ship", "Shipped", budget=3)
    assert progress(org) == org.runtime.progress_reporter.progress() and "working" in progress(org)


def test_the_waits_of_the_caller_are_the_clock_of_the_wait(org: Org) -> None:
    org.delegate(ROOT, "ceo", "Ship it", "Ship", "Shipped", budget=3)
    slept: list[float] = []
    now = [0.0]

    def sleep(seconds: float) -> None:
        slept.append(seconds)
        now[0] += seconds

    assert progress(org, wait_seconds=5, poll=2, sleep=sleep, clock=lambda: now[0]).startswith("Waited 5s:")
    assert slept == [2, 2, 1]


def test_the_function_reads_the_ports_of_the_runtime_of_its_org(tmp_path: Path) -> None:
    Org.init(tmp_path / "org", "mission")
    with wiring.overriding({HumanQueue: ListHumanQueue([("m1", "Needs you: x (message m1)")])}):
        assert progress(Org(tmp_path / "org")) == "No open tasks.\nNeeds you: x (message m1)"
