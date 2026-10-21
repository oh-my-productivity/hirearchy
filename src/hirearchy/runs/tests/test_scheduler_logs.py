"""Format golden: the logs the scheduler writes (with a stand-in agent) are exactly what the package reads.

The scheduler and the readers of the logs were written apart and agree on a text format (header, closing lines). These tests run the
real scheduler loop with ``tests/testkit/fake_agent.py`` through every way a run can end, and pin both sides: the text of the log (written before
the scheduler used the package, and unchanged since) and what ``RunLogReader`` makes of it.
"""

from __future__ import annotations

import os
import re
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest
import testkit
from testkit.health_world import Scheduler

from hirearchy.kernel import OrgPaths, stamp_of
from hirearchy.runs import RunOutcomes
from hirearchy.runs._reader import FsRunLogReader

from ._reach import reach

FAKE = str(testkit.FAKE_AGENT)
MISSING = "/nonexistent/hirearchy-binary"
HEADER = re.compile(
    r"\A# run of ceo, (?P<messages>\d+) message\(s\)\n# senders: (?P<senders>[^\n]*)\n# cwd: (?P<cwd>[^\n]+)\n"
    r"# cmd: (?P<cmd>[^\n]+) <prompt on stdin>\n# ---- prompt ----\n(?P<prompt>.*?)\n# ---- output ----\n",
    re.DOTALL,
)


def fake_runner(mode: str) -> Callable[[Any, str, str], tuple[list[str], Path, dict[str, str]]]:
    def build(org: Any, addr: str, prompt: str) -> tuple[list[str], Path, dict[str, str]]:
        env = {**os.environ, "ORG_ROOT": str(org.root), "ORG_AGENT": addr, "FAKE_MODE": mode}
        return [sys.executable, FAKE], org.dir(addr), env

    return build


def missing_runner(org: Any, addr: str, prompt: str) -> tuple[list[str], Path, dict[str, str]]:
    return [MISSING], org.dir(addr), dict(os.environ)


def org_with_ceo(tmp_path: Path, **config: object) -> Any:
    core = reach("core")
    org = core.Org.init(tmp_path / "org", "mission", {"poll_seconds": 0.05, **config})
    org.hire(core.ROOT, "ceo", "Chief executive", "Run the company.", can_hire=True, max_children=2)
    return org


def task(org: Any) -> None:
    org.delegate(reach("core").ROOT, "ceo", "Ship it", "Ship the thing", "It is shipped", budget=6)


def until(sched: Any, condition: Callable[[], bool], limit: float = 30.0) -> None:
    deadline = time.time() + limit
    while not condition():
        if time.time() > deadline:
            raise AssertionError("the scenario did not finish")
        sched.tick()
        time.sleep(0.02)


def drain(sched: Any) -> None:
    until(sched, lambda: not sched.tick() and not sched.runs)


@dataclass(frozen=True)
class Scenario:
    footer: str  # regular expression for the end of the log of the first run
    exit_code: int | None
    facts: set[str]  # keys that must be among the facts, besides the exit code and the seconds
    failed: bool
    senders: str = "root"


SCENARIOS = {
    "exit 0": Scenario(r"\n# exit 0 after \d+s\n\Z", 0, set(), False),
    "exit 1": Scenario(r"\n# exit 1 after \d+s\n\Z", 1, set(), True),
    "timeout": Scenario(r"\n# killed after 1s timeout\n\n# exit -9 after 1s\n\Z", -9, {"timed_out"}, True),
    "failed to start": Scenario(
        r"\n# failed to start: \[Errno 2\] No such file or directory: '" + re.escape(MISSING) + r"'\n\Z", None, {"failed_start"}, True
    ),
    "interrupted": Scenario(r"\n# interrupted by scheduler shutdown\n\Z", None, {"killed"}, True),
    "runtime only": Scenario(r"\n# exit 0 after \d+s\n\Z", 0, set(), False, senders="runtime"),
}


def produce(name: str, tmp_path: Path) -> tuple[Any, Path]:
    """Run the scheduler through scenario ``name``; the org and the log of the run of ``ceo`` that the scenario is about."""
    if name == "timeout":
        org = org_with_ceo(tmp_path, run_timeout=1)
    else:
        org = org_with_ceo(tmp_path)
    task(org)
    runner = {"exit 1": fake_runner("crash"), "timeout": fake_runner("hang"), "interrupted": fake_runner("hang"),
              "failed to start": missing_runner}.get(name, fake_runner("idle"))
    sched = Scheduler(org, runner, echo=lambda _: None)
    sched.acquire()
    try:
        logs = org.dir("ceo") / "runs"
        if name == "interrupted":
            until(sched, lambda: bool(sched.runs) and any("# ---- output ----" in p.read_text("utf-8") for p in logs.glob("*.log")))
        elif name == "timeout":
            until(sched, lambda: any("# exit" in p.read_text("utf-8") for p in logs.glob("*.log")))
        else:
            drain(sched)
            if name == "runtime only":  # the first run handled the task; the second one is woken by a note of the runtime alone
                org.notify("ceo", "reminder: Ship it", "Please look at your task.")
                drain(sched)
    finally:
        sched.release()
    return org, sorted(logs.glob("*.log"))[1 if name == "runtime only" else 0]


@pytest.mark.parametrize("name", list(SCENARIOS))
def test_the_log_of_the_scheduler_has_always_had_this_text(name: str, tmp_path: Path) -> None:
    _, log = produce(name, tmp_path)
    text = log.read_text(encoding="utf-8")
    head = HEADER.match(text)
    assert head is not None, text[:400]
    assert head["senders"] == SCENARIOS[name].senders and head["messages"] == "1"
    assert head["cwd"].endswith("/ceo")
    assert head["cmd"] == MISSING if name == "failed to start" else head["cmd"].endswith("fake_agent.py")
    assert re.search(SCENARIOS[name].footer, text), text[-300:]
    assert stamp_of(log.stem) is not None


@pytest.mark.parametrize("name", list(SCENARIOS))
def test_the_package_reads_what_the_scheduler_wrote(name: str, tmp_path: Path) -> None:
    scenario = SCENARIOS[name]
    org, log = produce(name, tmp_path)
    reader = FsRunLogReader(OrgPaths(org.root))
    facts = reader.facts(log)
    assert set(facts) == scenario.facts | ({"exit_code", "seconds"} if scenario.exit_code is not None else set())
    assert facts.get("exit_code") == scenario.exit_code
    outcomes = reader.outcomes("ceo")
    start = stamp_of(log.stem)
    assert (start in outcomes.failed) is scenario.failed
    assert (start in outcomes.runtime_only) is (scenario.senders == "runtime")
    assert reader.count("ceo") == len(list((org.dir("ceo") / "runs").glob("*.log")))
    assert isinstance(outcomes, RunOutcomes)
