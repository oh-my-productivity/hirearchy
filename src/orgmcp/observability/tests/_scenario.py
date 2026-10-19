"""Organizations with a request in them, built by the legacy ``Org`` with the story and the writers of ``tests/obs_fixtures.py``.

The expected files in ``expected/`` were captured from the module ``observe.py`` (the code before the package existed) on exactly these
organizations, so the tests that compare them prove the move changed no key, no number and no character. ``orgmcp.core`` and ``obs_fixtures``
are reached by name: a feature's tests do not import the facade statically.
"""

from __future__ import annotations

import importlib
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import ModuleType
from typing import Any

T0 = datetime(2026, 10, 18, 10, 0, 0, tzinfo=timezone.utc)
ROOT = "root"


def stamp(offset_s: float) -> datetime:
    return T0 + timedelta(seconds=offset_s)


NOW = stamp(200)
SINCE = "2026-10-18T00:00:00Z"


class CountingSecrets:
    """``secrets.token_hex`` as a counter, so that the ids of the messages are the same in every run."""

    def __init__(self) -> None:
        self.n = 0

    def token_hex(self, nbytes: int = 32) -> str:
        self.n += 1
        return f"{self.n:0{2 * nbytes}x}"


def fixtures() -> ModuleType:
    """``tests/obs_fixtures.py``: the clock, the event-file writer and the story."""
    return importlib.import_module("obs_fixtures")


def install(monkeypatch: Any) -> Any:
    """Patch the patch points of ``core`` (the clock and the id randomness); the returned clock is the one in force."""
    core: ModuleType = importlib.import_module("orgmcp.core")
    clock = fixtures().freeze(monkeypatch)
    monkeypatch.setattr(core, "secrets", CountingSecrets())
    return clock


def make_org(tmp_path: Path) -> Any:
    """root -> ceo -> eng, with emission off: the events of a test are the ones the test writes."""
    core: ModuleType = importlib.import_module("orgmcp.core")
    org = core.Org.init(tmp_path / "org", "Test mission", {"poll_seconds": 0.05, "events": False})
    org.hire(ROOT, "ceo", "Chief executive", "Run the company.", can_hire=True, max_children=2)
    org.hire("ceo", "eng", "Engineer", "Build things.")
    return org


def story(tmp_path: Path, clock: Any, *, events: bool = True, record: bool = True) -> Any:
    """The finished request of ``obs_fixtures.Story`` (three runs, a refusal, a delegation) on a fresh organization."""
    return fixtures().Story(make_org(tmp_path), clock, events=events, record=record)


def extend(built: Any) -> None:
    """More than the story has: a rework of the task (the totals list both tasks), a task of a service, a run that only the events know
    (its agent was retired), the lifecycle events that explain waits, scheduler faults and two refusals of one reason."""
    kernel: ModuleType = importlib.import_module("orgmcp.kernel")
    org, clock, log = built.org, built.clock, built.log
    clock.at(140)
    again = org.delegate(ROOT, "ceo", "Ship it again", "Ship the other thing", "It is shipped", budget=3, revises=built.task.id)
    clock.at(142)
    batch = [m.id for m in org.begin_run("ceo")]
    log1 = org.start_run_log("ceo")
    clock.at(150)
    org.deliver(kernel.Message(sender=ROOT, to="ceo", type="task", title="Memo", body="Write it.", service="memo", budget=2))
    clock.at(155)
    org.end_run("ceo", True)
    log1.write_text("# exit 0 after 13s\n")
    rid = f"ceo@{log1.stem}"
    log.emit("run.start", stamp(142.005), proc="scheduler", pid=7000, run=rid, agent="ceo", batch=batch, traces=[again.id, built.task.id],
             pgid=1, model=None, budget_before=4)
    log.emit("run.end", stamp(155), proc="scheduler", pid=7000, run=rid, agent="ceo", ok=True, exit_code=0, duration_ms=13000, timed_out=False,
             killed=False, budget_after=3, error=None)
    log.tool(stamp(145), "ceo", "report", run=rid, trace=again.id, args={"task_id": again.id, "status": "done"})
    log.tool(stamp(146), "ceo", "delegate", ok=False, ms=2, run=rid, trace=again.id,
             error="not enough budget: you have 9 run(s) and must keep 2 in reserve", args={"to": "ceo/eng", "budget": 9, "service": "memo"})
    log.run("gone/agent", "20261018T100100000000", stamp(60), 12, ["20261018T100000000000-root-ab12"], [built.task.id], pid=1)
    log.emit("agent.pause", stamp(30), proc="scheduler", pid=7000, agent="ceo/eng", reason="failures", trace=built.task.id)
    log.emit("agent.failure", stamp(31), proc="scheduler", pid=7000, agent="ceo/eng", count=3)
    log.emit("stall.nudge", stamp(60), proc="scheduler", pid=7000, task=built.task.id, to="ceo", step=0)
    log.emit("run.orphan", stamp(100), proc="scheduler", pid=7000, run="ceo/eng@20261018T100500000000", agent="ceo/eng", action="killed",
             detail="no process")
    log.emit("scheduler.error", stamp(5), proc="scheduler", pid=7000, phase="stall check", error="boom")
    log.emit("scheduler.start", stamp(100), proc="scheduler", pid=7100, mode="daemon")
    log.tool(stamp(12), "ceo", "delegate", ok=False, ms=4, error="not enough budget: you have 7 run(s) and must keep 3 in reserve",
             args={"to": "ceo/eng", "budget": 9, "service": "memo"})
    log.tool(stamp(13), "ceo/eng", "write", ok=False, ms=1, error="ceo/eng cannot write ceo/work/x.md", args={"path": "ceo/work/x.md"})
    built.again, built.memo_run = again, rid
