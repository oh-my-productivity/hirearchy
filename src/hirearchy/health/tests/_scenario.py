"""One organization with every health flag in it, built on disk by the ``Org`` facade with a clock that only moves when told.

The golden files in ``expected/`` were captured from the module ``health.py`` (the code before the package existed) on exactly this
organization, so the tests that compare them prove the move changed no text and no number. ``hirearchy.core`` is reached by name: a feature's
tests do not import the facade statically.
"""

from __future__ import annotations

import importlib
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import ModuleType
from typing import Any

from testkit.clocks import clock_ports

from hirearchy.kernel import TokenSource
from hirearchy.kernel.testing import CounterTokens

T0 = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
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


def add_run(org: Any, addr: str, start: float, end: float, footer: str = "") -> None:
    """A run log named after its start, last written at its end (seconds after ``T0``); ``footer`` is what the scheduler would append."""
    directory = org.dir(addr) / "runs"
    directory.mkdir(exist_ok=True)
    path = directory / f"{at(start):%Y%m%dT%H%M%S%f}.log"
    path.write_text(footer, encoding="utf-8")
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


def build(tmp_path: Path, clock: ScenarioClock) -> Any:
    """The organization:

    * ``ceo/eng``: an open task for over an hour, seven runs and no result, most of them silent (stuck, expensive, wasteful);
    * ``ceo/qa``: three tasks, two failed, one sent back by its manager (low_quality);
    * ``ceo/spare``: reported its one task blocked long ago and still holds its budget (stranded_budget), one run of it woken by the runtime alone;
    * ``ceo``: a service request the client sent back once (``client_rework``), so no ``rework`` is held against it;
    * ``ops``: all its budget used and a new task waiting (out_of_budget); ``ops/dev``: paused;
    * ``dormant``: never did anything (idle, once enough time has passed).
    """
    core: ModuleType = importlib.import_module("hirearchy.core")
    org = core.Org.init(tmp_path / "org", "Test mission", {"poll_seconds": 0.05})
    clock.at(0)
    org.hire(ROOT, "ceo", "Chief executive", "Run the company.", can_hire=True, max_children=4)
    org.hire("ceo", "eng", "Engineer", "Build things.")
    org.hire("ceo", "qa", "Tester", "Break things.")
    org.hire("ceo", "spare", "Spare hands", "Wait.")
    org.hire(ROOT, "ops", "Operations", "Keep it running.", can_hire=True, max_children=2)
    org.hire("ops", "dev", "Developer", "Fix things.")
    org.hire(ROOT, "dormant", "Sleeper", "Do nothing.")

    clock.at(10)
    org.delegate(ROOT, "ceo", "Plan", "Make a plan.", "a plan", budget=40)
    drain(org, "ceo")
    clock.at(20)
    org.delegate("ceo", "ceo/eng", "Build", "Build it.", "it builds", budget=10)
    drain(org, "ceo/eng")
    for i in range(7):
        add_run(org, "ceo/eng", 100 + i * 100, 150 + i * 100)
    add_run(org, "ceo/eng", 900, 920, "# exit 1 after 20s\n")

    clock.at(30)
    tests = [org.delegate("ceo", "ceo/qa", f"Check {i}", "Check it.", "checked", budget=3) for i in range(3)]
    drain(org, "ceo/qa")
    clock.at(60)
    org.report("ceo/qa", tests[0].id, "failed", "could not run it")
    clock.at(61)
    org.report("ceo/qa", tests[1].id, "failed", "broken")
    clock.at(62)
    org.report("ceo/qa", tests[2].id, "done", "fine")
    clock.at(70)
    org.delegate("ceo", "ceo/qa", "Check 0 again", "Check it again.", "checked", budget=2, revises=tests[0].id)
    drain(org, "ceo/qa")
    add_run(org, "ceo/qa", 200, 240)
    add_run(org, "ceo/qa", 300, 340)

    clock.at(40)
    spare_task = org.delegate("ceo", "ceo/spare", "Wait", "Wait for it.", "waited", budget=3)
    drain(org, "ceo/spare")
    clock.at(45)
    org.report("ceo/spare", spare_task.id, "blocked", "waiting for input")
    add_run(org, "ceo/spare", 300, 310, "# run of ceo/spare, 1 message(s)\n# senders: runtime\n\n# exit 0 after 10s\n")

    clock.at(80)
    memo = org.delegate(ROOT, "ceo", "Memo", "Write a memo.", "a memo", budget=4)
    drain(org, "ceo")
    clock.at(90)
    org.report("ceo", memo.id, "done", "the memo")
    clock.at(95)
    core_msg = importlib.import_module("hirearchy.kernel").Message
    org.deliver(core_msg(
        sender=ROOT, to="ceo", type="task", title="Memo again", body="Rework.", service="memo", revises=memo.id, budget=2,
    ))
    drain(org, "ceo")
    for i in range(3):
        add_run(org, "ceo", 120 + i * 60, 150 + i * 60)

    clock.at(100)
    org.delegate(ROOT, "ops", "Keep going", "Keep it up.", "up", budget=2)
    drain(org, "ops")
    add_run(org, "ops", 500, 520)
    add_run(org, "ops", 600, 620)
    clock.at(120)
    org.send(ROOT, "ops", "Are you there?")
    clock.at(130)
    org.pause("ops/dev", "taking a break", by="root")
    return org
