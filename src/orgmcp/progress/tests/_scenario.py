"""One organization with a root task in every state, built on disk by the legacy ``Org`` with a clock that only moves when told.

The golden files in ``expected/`` were captured from the module ``progress.py`` (the code before the package existed) on exactly this
organization, so the tests that compare them prove the move changed no text and no number. ``orgmcp.core`` is reached by name: a feature's
tests do not import the facade statically.
"""

from __future__ import annotations

import importlib
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import ModuleType
from typing import Any

from testkit.clocks import clock_ports

from orgmcp.kernel import TokenSource
from orgmcp.kernel.testing import CounterTokens

T0 = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
NOW = T0 + timedelta(hours=2)  # the moment the golden texts are rendered at
ROOT = "root"


def at(seconds: float) -> datetime:
    return T0 + timedelta(seconds=seconds)


class ScenarioClock:
    """The clock of the runtimes (``Clock.now``): fixed until told to move, then 1 ms per call so that message ids stay ordered."""

    def __init__(self) -> None:
        self.t = T0

    def __call__(self) -> datetime:
        self.t += timedelta(milliseconds=1)
        return self.t

    def at(self, seconds: float) -> None:
        self.t = at(seconds)


def add_run(org: Any, addr: str, start: float, end: float) -> None:
    """A run log named after its start, last written at its end (seconds after ``T0``)."""
    directory = org.dir(addr) / "runs"
    directory.mkdir(exist_ok=True)
    path = directory / f"{at(start):%Y%m%dT%H%M%S%f}.log"
    path.write_text("# run\n", encoding="utf-8")
    os.utime(path, (at(end).timestamp(), at(end).timestamp()))


def drain(org: Any, addr: str) -> None:
    """The agent reads its inbox: no unread mail is left."""
    org.begin_run(addr)
    org.end_run(addr, ok=True)


def install(process_overrides: Any) -> ScenarioClock:
    """Give every runtime opened from now on (until the test ends) the clock of the scenario and ids that count (the ``process_overrides`` fixture);
    the returned clock is the one in force."""
    clock = ScenarioClock()
    process_overrides({**clock_ports(clock), TokenSource: CounterTokens(start=1)})
    return clock


SERVICE = dict(
    description="A weekly brief.",
    inputs=[{"name": "topic", "description": "what it is about", "required": True}],
    acceptance=["Short"],
    deliverable={"description": "one file", "format": "markdown", "max_words": 600},
    budget=10,
)


def build(tmp_path: Path, clock: ScenarioClock) -> Any:
    """The organization (every task is root's; the text of each state in ``expected/``):

    * ``ceo``: "Plan" done with two artifacts and runs returned; "Memo" a request for a service, delivered, rejected, sent back and
      delivered again (a rework chain: the case total and "no feedback yet");
    * ``eng``: "Build" in flight (running); ``qa``: "Check" failed; ``spare``: "Wait" reported blocked;
    * ``ops``: "Keep going" held by ``ops``, which waits on its paused ``ops/dev``;
    * ``dormant``: "Idle" read and left alone (stalled); ``ghost``: "Haunt" assigned to an agent that was retired (failed);
    * in root's inbox: a budget request, a blocked result, a runtime notice and a quiet refund (not listed).
    """
    core: ModuleType = importlib.import_module("orgmcp.core")
    org = core.Org.init(tmp_path / "org", "Test mission", {"poll_seconds": 0.05})
    clock.at(0)
    org.hire(ROOT, "ceo", "Chief executive", "Run the company.", can_hire=True, max_children=4)
    for name in ("eng", "qa", "spare", "dormant", "ghost"):
        org.hire(ROOT, name, name.title(), "Do the work.")
    org.hire(ROOT, "ops", "Operations", "Keep it running.", can_hire=True, max_children=2)
    org.hire("ops", "dev", "Developer", "Fix things.")

    clock.at(10)
    plan = org.delegate(ROOT, "ceo", "Plan", "Make a plan.", "a plan", budget=8)
    drain(org, "ceo")
    add_run(org, "ceo", 20, 40)
    add_run(org, "ceo", 50, 70)
    add_run(org, "ceo", 80, 100)
    org.write("ceo", "ceo/work/plan.md", "# Plan\nfirst second third")
    org.write("ceo", "ceo/work/risks.md", "risks")
    clock.at(110)
    org.report("ceo", plan.id, "done", "The plan is ready.", ["ceo/work/plan.md", "ceo/work/risks.md"])

    clock.at(120)
    org.define_service(ROOT, "ceo", "weekly-brief", **SERVICE)
    first = org.request(ROOT, "weekly-brief", {"topic": "ai"})
    drain(org, "ceo")
    add_run(org, "ceo", 200, 220)
    add_run(org, "ceo", 230, 250)
    clock.at(260)
    org.report("ceo", first.id, "done", "Delivered.", lessons="Fine.")
    clock.at(270)
    org.feedback(ROOT, first.id, "reject", "Too long.")
    clock.at(280)
    rework = org.request(ROOT, "weekly-brief", {"topic": "ai"}, revises=first.id, budget=6)
    drain(org, "ceo")
    add_run(org, "ceo", 300, 320)
    clock.at(330)
    org.report("ceo", rework.id, "done", "Delivered again.", lessons="Shorter.")

    clock.at(400)
    org.delegate(ROOT, "eng", "Build", "Build it.", "it builds", budget=5)
    org.begin_run("eng")
    started = org.start_run_log("eng")
    os.utime(started, (at(405).timestamp(), at(405).timestamp()))
    add_run(org, "eng", 410, 430)

    clock.at(440)
    check = org.delegate(ROOT, "qa", "Check", "Check it.", "checked", budget=3)
    drain(org, "qa")
    add_run(org, "qa", 450, 470)
    clock.at(480)
    org.report("qa", check.id, "failed", "The source site is gone.")

    clock.at(500)
    wait = org.delegate(ROOT, "spare", "Wait", "Wait for it.", "waited", budget=3)
    drain(org, "spare")
    clock.at(510)
    org.report("spare", wait.id, "blocked", "Need the 2025 sales figures.\nAnd more words.")

    clock.at(520)
    org.delegate(ROOT, "ops", "Keep going", "Keep it up.", "up", budget=6)
    drain(org, "ops")
    clock.at(530)
    org.delegate("ops", "ops/dev", "Fix it", "Fix.", "fixed", budget=2)
    drain(org, "ops/dev")
    org.pause("ops/dev", "taking a break", by="root")

    clock.at(540)
    org.delegate(ROOT, "dormant", "Idle", "Do nothing.", "nothing", budget=2)
    drain(org, "dormant")

    clock.at(550)
    org.delegate(ROOT, "ghost", "Haunt", "Boo.", "scared", budget=1)
    org.retire(ROOT, "ghost", "gone")

    clock.at(600)
    org.send("ceo", ROOT, "I need 2 more runs for the rework.\nDetails follow.", title="Budget request")
    org.notify(ROOT, "ceo is out of budget", "`ceo` has no budget left.")
    org.notify(ROOT, "refund", "returned", wake=False)
    return org


class WaitClock:
    """A fake monotonic clock whose ``sleep`` moves it, and that runs an action at the n-th sleep."""

    def __init__(self, actions: dict[int, Any] | None = None) -> None:
        self.now, self.sleeps, self.actions = 0.0, 0, actions or {}

    def __call__(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.sleeps += 1
        self.now += seconds
        action = self.actions.get(self.sleeps)
        if action:
            action()


def task_named(org: Any, title: str) -> Any:
    return next(m for m in org.sent(ROOT) if m.type == "task" and m.title == title)


def wait_cases(org: Any, progress: Any) -> str:
    """Six waits on the scenario, one after the other, as one text (``progress``: the function with the signature of the legacy one)."""
    out: list[str] = []

    def wait(label: str, task_id: str | None, seconds: int, poll: float, clock: WaitClock) -> None:
        text = progress(org, task_id, now=NOW, wait_seconds=seconds, poll=poll, sleep=clock.sleep, clock=clock)
        out.append(f"=== {label} (slept {clock.sleeps}x)\n{text}")

    build = task_named(org, "Build")
    wait("nothing to wait for", task_named(org, "Plan").id, 60, 2.0, WaitClock())
    wait("timeout", build.id, 6, 2.0, WaitClock())
    wait("capped at 900", build.id, 5000, 400.0, WaitClock())
    org.send(ROOT, "spare", "Here are more runs.", budget=3)
    spare = task_named(org, "Wait")
    wait("stopped", spare.id, 60, 2.0, WaitClock({1: lambda: drain(org, "spare")}))
    wait("new item", build.id, 60, 2.0, WaitClock({1: lambda: org.send("eng", ROOT, "Which branch?", title="Question")}))
    wait("changed", build.id, 60, 2.0, WaitClock({2: lambda: org.report("eng", build.id, "done", "built")}))
    return re.sub(r"\(message [^)]+\)", "(message <id>)", "\n".join(out) + "\n")  # (what the clock said when the note was written does not matter)
