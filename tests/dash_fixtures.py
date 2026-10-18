"""Organizations for the dashboard tests and screenshots: a populated demo org that shows every agent state, and a
generated big org for the refresh-time measurement.

Both are built with the real ``Org`` API under a controllable clock (``obs_fixtures.Clock``), so ids, run log names and
event timestamps are consistent with each other; the dashboard is then given ``now = DEMO_NOW`` so elapsed times are
stable. Run logs get the mtime they would have had.
"""

from __future__ import annotations

import json
import os
from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace

from obs_fixtures import T0, Clock, EventLog, stamp

from orgmcp.core import ROOT, Message, Org, atomic_write

DEMO_NOW = T0 + timedelta(seconds=400)

BRIEF = dict(
    description="A one-page market brief on a topic.",
    inputs=[{"name": "topic", "description": "what the brief is about", "required": True}],
    acceptance=["At most 600 words", "Every claim has a source URL"],
    deliverable={"description": "one markdown file", "format": "markdown", "max_words": 600},
    budget=6,
    playbook="# Playbook\nStart from the sources the client named.\nKeep it under 600 words.\n",
)


class DeferredLog(EventLog):
    """An EventLog that writes in time order when flushed (the real runtime appends chronologically)."""

    def __init__(self, org: Org):
        super().__init__(org)
        self.pending: list = []

    def emit(self, kind, ts, **kw):  # noqa: D102
        self.pending.append((ts, kind, kw))
        return {}

    def flush(self) -> None:
        for ts, kind, kw in sorted(self.pending, key=lambda x: x[0]):
            EventLog.emit(self, kind, ts, **kw)
        self.pending = []


def set_mtime(path: Path, when) -> None:
    os.utime(path, (when.timestamp(), when.timestamp()))


def end_run(org: Org, addr: str, log: Path, clock: Clock, seconds: float, ok: bool = True, text: str = "") -> None:
    """Finish a run the way the scheduler does: batch to read (or back to the inbox), an exit line in the log."""
    org.end_run(addr, ok)
    with open(log, "a", encoding="utf-8") as f:
        f.write(text + (f"\n# exit {0 if ok else 1} after {int(seconds)}s\n"))
    set_mtime(log, clock.t)


def start_run(org: Org, addr: str, clock: Clock, senders: str = "root") -> tuple[list[Message], Path]:
    batch = org.begin_run(addr)
    log = org.start_run_log(addr)
    log.write_text(f"# run of {addr}, {len(batch)} message(s)\n# senders: {senders}\n# cwd: {org.dir(addr)}\n"
                   "# cmd: kiro-cli chat --no-interactive <prompt on stdin>\n# ---- prompt ----\n(prompt)\n# ---- output ----\n",
                   encoding="utf-8")
    return batch, log


def demo_org(base: Path, clock: Clock | None = None) -> SimpleNamespace:
    """A populated organization 'acme' at ``DEMO_NOW`` showing every state:

    ceo running (1m12s) · research running (service request, 2m05s) · ceo/analyst queued (max_parallel busy) ·
    ceo/writer working on a task · ops waiting on a report · ops/deploy queued (paused) · ops/audit paused · research/crawler out of budget ·
    archivist idle. Root has one item that needs it and a finished request; the service ``market-brief`` of
    ``research`` has two finished cases (one rejected then accepted) and one open.
    """
    clock = clock or Clock()
    import orgmcp.core as core
    import orgmcp.services as svc

    counter = iter(range(1 << 30))

    def token_hex(nbytes: int = 32) -> str:  # 0000, 0001, ...: never 1xxx, so no id contains e.g. 't-1' ('roo|t-1|657')
        return f"{next(counter):0{2 * nbytes}x}"

    real, real_svc, real_secrets = core.utcnow, svc.utcnow, core.secrets
    core.utcnow = svc.utcnow = clock
    core.secrets = SimpleNamespace(token_hex=token_hex)  # message ids end in random hex; the demo must be the same every time
    try:
        return _build_demo(base, clock)
    finally:
        core.utcnow, svc.utcnow, core.secrets = real, real_svc, real_secrets


def _build_demo(base: Path, clock: Clock) -> SimpleNamespace:
    org = Org.init(base / "acme", "Acme market research.", {"poll_seconds": 0.05, "max_parallel": 2, "events": False})
    org.hire(ROOT, "ceo", "Chief executive", "Run the report pipeline.", can_hire=True, max_children=3)
    org.hire("ceo", "analyst", "Competitor analyst", "Collect competitor data.", model="claude-opus-5.5")
    org.hire("ceo", "writer", "Report writer", "Write the quarterly report.")
    org.hire(ROOT, "ops", "Operations lead", "Keep the keys rotated.", can_hire=True, max_children=2)
    org.hire("ops", "deploy", "Deploy engineer", "Deploy the rotated keys.")
    org.hire("ops", "audit", "Auditor", "Audit key usage.")
    org.hire(ROOT, "research", "Research lead", "Deliver market briefs.", can_hire=True, max_children=2)
    org.hire("research", "crawler", "Web crawler", "Crawl sources.")
    org.hire(ROOT, "archivist", "Archivist", "Keep the archive tidy.")
    log = DeferredLog(org)
    ns = SimpleNamespace(org=org, clock=clock, events=log, now=DEMO_NOW)

    # ---- archivist: a finished request (done), old enough to show "last activity"
    clock.at(1)
    done_task = org.delegate(ROOT, "archivist", "Archive old reports", "Move last year's reports.", "Archive folder exists", budget=3)
    clock.at(5)
    _, lg = start_run(org, "archivist", clock)
    clock.at(20)
    org.write("archivist", "archivist/work/archive.md", "archived 14 reports")
    org.report("archivist", done_task.id, "done", "Archived 14 reports.", ["archivist/work/archive.md"])
    clock.at(22)
    end_run(org, "archivist", lg, clock, 17)
    ns.done_task = done_task

    # ---- the quarterly report: ceo delegates to analyst (queued) and writer (working)
    clock.at(30)
    report_task = org.delegate(ROOT, "ceo", "Quarterly market report", "Write the Q3 market report.",
                               "Covers 5 competitors\nEvery claim sourced", budget=12)
    clock.at(40)
    _, lg = start_run(org, "ceo", clock)
    clock.at(60)
    org.delegate("ceo", "ceo/analyst", "Collect competitor data", "Collect data on 5 competitors.", "A table of 5 rows", budget=4)
    sub_writer = org.delegate("ceo", "ceo/writer", "Draft the report", "Draft from the data.", "A 3-page draft", budget=3)
    clock.at(75)
    end_run(org, "ceo", lg, clock, 35)
    clock.at(80)
    org.begin_run("ceo/writer")  # the writer read its task and is not running now
    org.start_run_log("ceo/writer")
    org.end_run("ceo/writer", True)
    ns.report_task, ns.sub_writer = report_task, sub_writer
    # ---- ops: waiting on a report; deploy is paused; ops asks root for a decision
    clock.at(100)
    ops_task = org.delegate(ROOT, "ops", "Rotate API keys", "Rotate all keys.", "No key older than 90 days", budget=6)
    clock.at(110)
    _, lg = start_run(org, "ops", clock)
    clock.at(120)
    org.delegate("ops", "ops/deploy", "Deploy rotated keys", "Deploy.", "All services use the new keys", budget=2)
    org.send("ops", ROOT, "The key rotation needs a maintenance window. May I take the API down on Saturday 02:00?",
             title="Need approval for downtime")
    clock.at(130)
    end_run(org, "ops", lg, clock, 20)
    clock.at(140)
    _, lg = start_run(org, "ops/deploy", clock, "ops")
    clock.at(150)
    end_run(org, "ops/deploy", lg, clock, 10, ok=False, text="error: deploy tool crashed")
    org.pause("ops/deploy", "2 consecutive failed runs", by="runtime")
    org.clear_failures("ops/deploy")
    log.run("ops/deploy", lg.stem, stamp(140), 10, [], [ops_task.id], ok=False, error="exit code 1")
    org.pause("ops/audit", "paused by the user: audit window closed", by=ROOT)
    ns.ops_task = ops_task

    # ---- research: a service request (running, 2m05s) and a crawler that used up its budget
    clock.at(150)
    ns.contract = org.define_service(ROOT, "research", "market-brief", **BRIEF)
    clock.at(160)
    c1 = org.request(ROOT, "market-brief", {"topic": "EV chargers"}, title="Brief: EV chargers")
    clock.at(165)
    _, lg = start_run(org, "research", clock)
    clock.at(180)
    org.write("research", "research/work/ev.md", "brief")
    org.report("research", c1.id, "done", "Brief delivered.", ["research/work/ev.md"], lessons="Client wants short briefs.")
    clock.at(185)
    end_run(org, "research", lg, clock, 20)
    clock.at(190)
    org.feedback(ROOT, c1.id, "reject", "Too long and no sources.")
    clock.at(195)
    c1b = org.delegate(ROOT, "research", "Brief: EV chargers (shorter)", "Shorter please.", "Under 400 words", budget=4, revises=c1.id)
    clock.at(200)
    _, lg = start_run(org, "research", clock)
    clock.at(215)
    org.write("research", "research/work/ev2.md", "short brief")
    org.report("research", c1b.id, "done", "Short brief delivered.", ["research/work/ev2.md"],
               lessons="Under 400 words works; the client rejected the long one.")
    clock.at(218)
    end_run(org, "research", lg, clock, 18)
    clock.at(220)
    org.feedback(ROOT, c1b.id, "accept", "This is right.")
    clock.at(250)
    c2 = org.request(ROOT, "market-brief", {"topic": "Heat pumps"}, title="Brief: heat pumps")
    clock.at(262)
    org.delegate("research", "research/crawler", "Crawl heat pump sources", "Crawl.", "10 URLs", budget=1)
    clock.at(263)
    _, lg = start_run(org, "research/crawler", clock, "research")
    clock.at(270)
    end_run(org, "research/crawler", lg, clock, 7)  # used its only run, task still open: out of budget
    clock.at(275)
    batch, lg = start_run(org, "research", clock)
    lg.write_text(lg.read_text() + "Crawler finished one pass without a result.\nWaiting for sources...\n", encoding="utf-8")
    set_mtime(lg, stamp(395))
    ns.research_log = lg
    _running(org, "research", lg, started=DEMO_NOW.timestamp() - 125)
    log.emit("run.start", stamp(275), proc="scheduler", pid=7000, actor="runtime", run=f"research@{lg.stem}", agent="research",
             batch=[m.id for m in batch], traces=[c2.id], pgid=1, model=None, budget_before=3)
    ns.c1, ns.c2 = c1, c2

    # ceo is running again (a note from root arrived): 1m12s before DEMO_NOW
    clock.at(300)
    org.send(ROOT, "ceo", "Please also cover the Asian market.", title="Scope change")
    clock.at(327)
    batch, lg = start_run(org, "ceo", clock)
    lg.write_text(lg.read_text() + "I will read the scope change first.\n[tool] inbox ok\n[tool] read ceo/MEMORY.md ok\n"
                  "Delegating the extra scope to the analyst...\n", encoding="utf-8")
    set_mtime(lg, stamp(395))
    ns.ceo_log = lg
    _running(org, "ceo", lg, started=DEMO_NOW.timestamp() - 72)
    log.emit("run.start", stamp(327), proc="scheduler", pid=7000, actor="runtime", run=f"ceo@{lg.stem}", agent="ceo",
             batch=[m.id for m in batch], traces=[report_task.id], pgid=1, model=None, budget_before=9)
    ns.ceo_batch = batch

    # ---- events: tool calls (one refusal within the last 15 minutes), scheduler
    log.emit("scheduler.start", stamp(0), proc="scheduler", pid=7000, mode="until_done", max_runs=None, max_parallel=2, version="0.1.0")
    log.emit("scheduler.heartbeat", stamp(397), proc="scheduler", pid=7000, actor="runtime", running=[f"ceo@{ns.ceo_log.stem}"],
             runnable=1, waiting_on_you=1)
    log.tool(stamp(330), "ceo", "inbox", run=f"ceo@{ns.ceo_log.stem}", trace=report_task.id)
    log.tool(stamp(340), "ceo", "delegate", ok=False, run=f"ceo@{ns.ceo_log.stem}", trace=report_task.id,
             error="not enough budget: you have 5 run(s) and must keep 2 in reserve", args={"to": "ceo/analyst", "budget": 9})
    log.tool(stamp(350), "ceo", "read", run=f"ceo@{ns.ceo_log.stem}", trace=report_task.id, args={"path": "ceo/MEMORY.md"})
    log.tool(stamp(380), "research", "read", run=f"research@{ns.research_log.stem}", trace=c2.id, args={"path": "research/services/market-brief/PLAYBOOK.md"})
    # a request trace: root's own tool call
    log.tool(stamp(30.0005), ROOT, "delegate", trace=report_task.id, proc="cli", pid=5100, args={"to": "ceo", "title": "Quarterly market report", "budget": 12})

    log.flush()
    return ns


def _running(org: Org, addr: str, log: Path, started: float) -> None:
    """Add ``addr`` to .runtime/running.json the way the scheduler records a run in flight."""
    rec = org.ledger("running")
    rec[addr] = {"pgid": 999_999, "lstart": "x", "started": started, "scheduler": 7000, "log": str(log.relative_to(org.root))}
    org.save_ledger("running", rec)


# ------------------------------------------------------------------------------------------------ a big org


def big_org(base: Path, agents: int = 50, messages: int = 2000) -> Org:
    """``agents`` agents in a tree (5 top-level managers, the rest below them) and about ``messages`` messages
    (each stored twice, as the runtime does): tasks, results and notes, some unread, some running, a few run logs each.
    Built from files directly (fast)."""
    org = Org.init(base / "big", "Big org.", {"poll_seconds": 0.05, "max_parallel": 4})
    tops = [f"lead{i}" for i in range(5)]
    for t in tops:
        org.hire(ROOT, t, "Lead", "Lead.", can_hire=True, max_children=20)
    addrs = list(tops)
    n = 0
    while len(addrs) < agents:
        parent = tops[n % len(tops)]
        name = f"w{n}"
        org.hire(parent, name, "Worker", "Work.")
        addrs.append(f"{parent}/{name}")
        n += 1
    workers = [a for a in addrs if "/" in a]
    t = T0 + timedelta(seconds=1)
    for i in range(messages):
        w = workers[i % len(workers)]
        lead = w.split("/")[0]
        t += timedelta(milliseconds=7)
        kind = i % 4
        if kind == 0:
            m = Message(sender=lead, to=w, type="task", title=f"Task {i}", body="## Goal\nDo it.\n\n## Acceptance criteria\nDone.", budget=2)
            sender, to = lead, w
        elif kind == 1:
            m = Message(sender=w, to=lead, type="result", title=f"Task {i - 1}", body="## Summary\nDone.", status="done", reply_to=f"x{i}")
            sender, to = w, lead
        elif kind == 2:
            m = Message(sender=lead, to=w, type="note", title="fyi", body="A note.")
            sender, to = lead, w
        else:
            m = Message(sender=ROOT, to=lead, type="note", title="grant", body="more runs", budget=1)
            sender, to = ROOT, lead
        m.id = f"{t:%Y%m%dT%H%M%S%f}-{sender.replace('/', '.')}-{i:04x}"
        m.created = t.isoformat()
        text = m.to_text()
        box_in = "inbox" if i % 17 == 0 else "read"
        for who, box in ((sender, "sent"), (to, box_in)):
            d = org.dir(who) / box
            d.mkdir(exist_ok=True)
            atomic_write(d / f"{m.id}.md", text)
    for w in workers[: len(workers) // 2]:
        d = org.dir(w) / "runs"
        d.mkdir(exist_ok=True)
        for k in range(3):
            (d / f"{(T0 + timedelta(seconds=10 * k)):%Y%m%dT%H%M%S%f}.log").write_text("# exit 0 after 5s\n")
    for w in workers[:2]:  # two running
        org.begin_run(w)
    return org


def write_running_json(org: Org, addr: str, seconds_ago: float = 72.0, import_time=None) -> Path:
    import time

    logs = sorted((org.dir(addr) / "runs").glob("*.log"))
    log = logs[-1] if logs else org.start_run_log(addr)
    org.save_ledger("running", {**org.ledger("running"), addr: {
        "pgid": 999_999, "lstart": "x", "started": (import_time or time.time()) - seconds_ago, "scheduler": 7000,
        "log": str(log.relative_to(org.root))}})
    return log
