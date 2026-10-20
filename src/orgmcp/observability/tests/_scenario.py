"""Organizations with a request in them, built by the legacy ``Org`` with the story and the writers of ``tests/testkit/obs_fixtures.py``.

The expected files in ``expected/`` were captured from the module ``observe.py`` (the code before the package existed) on exactly these
organizations, so the tests that compare them prove the move changed no key, no number and no character. ``orgmcp.core`` and ``obs_fixtures``
are reached by name: a feature's tests do not import the facade statically.
"""

from __future__ import annotations

import dataclasses
import importlib
import os
from collections.abc import Mapping
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import ModuleType
from typing import Any

from orgmcp.daemon import SchedulerState
from orgmcp.daemon.testing import FakeSchedulerStatus
from orgmcp.kernel import TokenSource
from orgmcp.kernel.testing import CounterTokens
from orgmcp.processes import OrphanJudge

T0 = datetime(2026, 10, 18, 10, 0, 0, tzinfo=timezone.utc)
ROOT = "root"


def stamp(offset_s: float) -> datetime:
    return T0 + timedelta(seconds=offset_s)


NOW = stamp(200)
SINCE = "2026-10-18T00:00:00Z"


def fixtures() -> ModuleType:
    """``tests/testkit/obs_fixtures.py``: the clock, the event-file writer and the story."""
    return importlib.import_module("testkit.obs_fixtures")


def install(process_overrides: Any) -> Any:
    """Give every runtime opened from now on (until the test ends) the controllable clock and ids that count (the ``process_overrides`` fixture);
    the returned clock is the one in force."""
    clock = fixtures().freeze(process_overrides)
    process_overrides({TokenSource: CounterTokens(start=1)})
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


# ------------------------------------------------------------------------------ the second half: now and check
#
# The organizations below are the ones the expected files ``now_*``, ``check_*`` and ``text_*`` were captured on from ``observe.py`` (the module before
# C-obs-2), the scheduler being what the scenario says (``STATES``) and the judge of a recorded process what it says (``judge``).

STOPPED = ("stopped", None, None, "")
RUNNING = ("running", 7000, "2026-10-18 10:00:00Z", "")
RUNNING_DAEMON = ("running", 7100, "2026-10-18 10:01:40Z", "")
UNVERIFIED = ("unverified", 4242, "2026-10-18 10:00:00Z", "its command line is 'vim'")


def old(path: Path, when: float = 100) -> None:
    """The file was last written ``when`` seconds after the origin of the clock, whatever the clock of the machine says."""
    t = stamp(when).timestamp()
    os.utime(path, (t, t))


def settle(org: Any) -> None:
    """Every message file is old (written at ``stamp(100)``): no copy is 'in delivery', whatever the machine's clock says."""
    for box in ("inbox", "inflight", "read", "sent"):
        for path in org.root.rglob(f"{box}/*.md"):
            old(path)


def write(org: Any, rel: str, meta: dict[str, Any], body: str = "b") -> Path:
    """A message file by hand (front matter and body) at ``rel``, old."""
    core: ModuleType = importlib.import_module("orgmcp.core")
    path: Path = org.root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(core.join_frontmatter(meta, body), encoding="utf-8")
    old(path)
    return path


def idle(built: Any) -> None:
    """Mail for ``ceo`` that nobody has started on, and a note that waits for root."""
    org, clock = built.org, built.clock
    clock.at(160)
    org.send(ROOT, "ceo", "Please look at the memo", title="Memo")
    clock.at(170)
    org.send("ceo", ROOT, "I need the logo\nand the colours", title="Logo")


def busy(built: Any, parallel: int = 3) -> None:
    """A run of ``ceo`` in flight (recorded, with its log), mail that came in during it, agents that are ready, out of budget and paused, a refused call."""
    org, clock, log = built.org, built.clock, built.log
    log.emit("scheduler.heartbeat", stamp(190), proc="scheduler", pid=7000, running=["ceo"], runnable=1, waiting_on_you=1)
    cfg = (org.root / "ORG.md").read_text().replace("max_parallel: 3", f"max_parallel: {parallel}")
    (org.root / "ORG.md").write_text(cfg)
    clock.at(180)
    org.delegate(ROOT, "ceo", "Another", "g", "a", budget=2)
    org.begin_run("ceo")
    path = org.start_run_log("ceo")
    org.save_ledger("running", {"ceo": {"pgid": 123, "lstart": "x", "started": stamp(181).timestamp(), "scheduler": 7000,
                                        "log": str(path.relative_to(org.root))}})
    log.tool(stamp(195), "ceo", "send", ok=False, error="ceo cannot message nobody", run=f"ceo@{path.stem}")
    log.tool(stamp(-2000), "ceo", "send", ok=False, error="an old refusal")  # outside the 15 minutes
    clock.at(185)
    org.send(ROOT, "ceo", "one more thing", title="More")  # arrived during the run
    org.hire(ROOT, "ops", "Ops", "Ops.")
    org.delegate(ROOT, "ops", "O", "g", "a", budget=3)
    org.hire(ROOT, "poor", "Poor", "Poor.")
    org.send(ROOT, "poor", "hello")  # no budget
    org.pause("ceo/eng", "failures")
    org.send(ROOT, "ceo/eng", "are you there")
    clock.at(190)
    org.send("ceo", ROOT, "Blocked on the logo", title="Logo")
    built.busy_run = f"ceo@{path.stem}"


def retired(built: Any) -> None:
    """Budget that went to retired agents, below ceo and below root (what a check of the arithmetic must count)."""
    org, clock = built.org, built.clock
    clock.at(150)
    org.hire("ceo", "qa", "QA", "Test.")
    org.send("ceo", "ceo/qa", "standby", budget=2, wake=False)
    org.send(ROOT, "ceo", "more runs", budget=3)
    org.reclaim("ceo", "qa", 1)
    org.retire("ceo", "qa", "done")
    org.hire(ROOT, "ops", "Ops", "Ops.")
    org.send(ROOT, "ops", "go", budget=5)
    org.begin_run("ops")
    org.start_run_log("ops")
    org.end_run("ops", True)
    org.retire(ROOT, "ops", "gone")


def corrupt(built: Any) -> None:
    """Everything a check looks for, once: a file named after another id, a copy in the wrong box, an id twice, a sender copy with no other copy, a file that
    does not parse, a budget off by 4, a batch inflight with no run, a run with no end, a log with no start, a gap in the lines, a stale pid file."""
    org, clock, log = built.org, built.clock, built.log
    settle(org)
    note = {"from": ROOT, "to": "ceo", "type": "note", "title": "n"}
    write(org, "ceo/read/renamed.md", {**note, "id": "20261018T100001000000-root-aaaa"})
    write(org, "ceo/eng/inbox/20261018T100002000000-root-bbbb.md", {**note, "id": "20261018T100002000000-root-bbbb"})
    for box in ("inbox", "read"):
        write(org, f"ceo/{box}/20261018T100003000000-root-cccc.md", {**note, "id": "20261018T100003000000-root-cccc"})
    write(org, "ceo/sent/20261018T100004000000-ceo-dddd.md",
          {"id": "20261018T100004000000-ceo-dddd", "from": "ceo", "to": "ceo/eng", "type": "note", "budget": 2})
    (org.root / "ceo/read/broken.md").write_text("no frontmatter at all\n")
    core: ModuleType = importlib.import_module("orgmcp.core")
    path = next((org.dir("ceo/eng") / "read").glob("*.md"))
    meta, body = core.split_frontmatter(path.read_text())
    meta["budget"] = int(meta.get("budget", 0)) + 4
    path.write_text(core.join_frontmatter(meta, body))
    old(path)
    clock.at(190)
    org.send(ROOT, "ceo/eng", "work")
    org.begin_run("ceo/eng")  # a batch taken, then the scheduler died
    for inflight in (org.dir("ceo/eng") / "inflight").glob("*.md"):
        old(inflight, -600)
    org.start_run_log("ceo/eng")  # a run log with no run.start
    log.emit("run.start", stamp(150), proc="scheduler", pid=7000, run="ceo@20261018T100230000000", agent="ceo", batch=[], traces=[], pgid=1)
    log.emit("tool.call", stamp(3), actor="ceo", tool="read", ok=True, ms=1, skip_seq=2)  # two lines lost
    (org.root / ".runtime").mkdir(exist_ok=True)
    (org.root / ".runtime" / "scheduler.pid").write_text("999999")


def nothing(built: Any) -> None:
    """The extended story as it is."""


# name -> (what is done to the extended story, the scheduler, the verdict of the judge on a recorded process)
SCENARIOS: dict[str, tuple[Any, tuple[str, int | None, str | None, str], str]] = {
    "stopped": (idle, STOPPED, "gone"),
    "ready": (idle, RUNNING_DAEMON, "gone"),
    "unverified": (idle, UNVERIFIED, "gone"),
    "busy": (busy, RUNNING, "ours"),
    "busy_full": (lambda built: busy(built, 1), RUNNING, "ours"),
    "story": (nothing, STOPPED, "gone"),
    "retired": (retired, STOPPED, "gone"),
    "corrupt": (corrupt, STOPPED, "gone"),
    "corrupt_unverified": (corrupt, UNVERIFIED, "gone"),
}


class VerdictJudge(OrphanJudge):
    """The verdict on every recorded process is the same: ``ours``, ``doubt``, ``gone`` or ``foreign``."""

    def __init__(self, verdict: str) -> None:
        self.verdict = verdict

    def judge(self, record: Mapping[str, object]) -> str:
        return self.verdict


def follow_ports(org: Any, state: tuple[str, int | None, str | None, str], verdict: str) -> Any:
    """The runtime of ``org`` with the scheduler and the judge the scenario says (the legacy functions read the runtime of the ``Org``)."""
    org.runtime = dataclasses.replace(org.runtime, scheduler_status=FakeSchedulerStatus(SchedulerState(*state)), orphan_judge=VerdictJudge(verdict))
    return org.runtime
