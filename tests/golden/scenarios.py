"""Deterministic organizations the golden tests share. Every step moves the fixed clock so message ids sort as they happened."""

from __future__ import annotations

import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

from hirearchy.core import ROOT, Org

BRIEF = dict(
    description="A one-page brief on the past week's news about a topic.",
    inputs=[
        {"name": "topic", "description": "what the brief is about", "required": True},
        {"name": "week", "description": "ISO week; default the current one", "required": False},
    ],
    acceptance=["At most 600 words", "Every factual claim has a source URL"],
    deliverable={"description": "one markdown file", "format": "markdown", "max_words": 600},
    budget=10,
)

PLAYBOOK = """\
# Weekly brief

1. Ask the researcher for sources on the topic.
2. Have the writer draft at most 600 words.
3. Have the fact-checker verify every claim before you report.
"""


def company(tmp_path: Path, clock, *, config: dict | None = None) -> Org:
    """root -> ceo (manager, can hire, two reports max) -> eng, qa (workers)."""
    org = Org.init(tmp_path / "org", "Golden mission: ship the thing.", {"poll_seconds": 0.05, **(config or {})})
    clock.tick()
    org.hire(ROOT, "ceo", "Chief executive", "Run the company.", can_hire=True, max_children=2)
    clock.tick()
    org.hire("ceo", "eng", "Engineer", "Build things.")
    clock.tick()
    org.hire("ceo", "qa", "Quality assurance", "Check things.")
    clock.tick()
    return org


def dirs(tmp_path: Path) -> tuple[Path, Path]:
    ws, inputs = tmp_path / "ws", tmp_path / "in"
    ws.mkdir()
    inputs.mkdir()
    return ws, inputs


def run(org: Org, addr: str, clock):
    """Start a run for ``addr`` like the scheduler: its inbox becomes the batch."""
    batch = org.begin_run(addr)
    clock.tick()
    return batch


def deliver_service(org: Org, owner: str, task, clock, *, status="done", lessons="Worked; no change needed.", summary="Delivered."):
    """The owner handles ``task`` in one run and reports on it."""
    org.begin_run(owner)
    org.start_run_log(owner)
    clock.tick()
    msg = org.report(owner, task.id, status, summary, lessons=lessons)
    org.end_run(owner, ok=True)
    clock.tick()
    return msg


def write_artifact(org: Org, actor: str, path: str, content: str, clock) -> None:
    """``org.write`` plus a file mtime on the fixed clock: reports show "modified HH:MM:SS" of every artifact."""
    target = org.write(actor, path, content)
    stamp = clock.now.timestamp()
    os.utime(target, (stamp, stamp))


def busy_org(tmp_path: Path, clock) -> Org:
    """A mid-flight organization with files AND events: an open request, a crashed agent, a finished task awaiting root,
    a refused tool call. Built through the public API plus hand-written scheduler/MCP events (``obs_fixtures.EventLog``),
    all on the fixed clock. Event emission is then switched off in ORG.md, so reading commands add no ``cli.command`` events.
    """
    from testkit.obs_fixtures import EventLog

    org = company(tmp_path, clock)
    log = EventLog(org)
    org.define_service(ROOT, "ceo", "weekly-brief", playbook=PLAYBOOK, **BRIEF)
    org.hire(ROOT, "ops", "Operations", "Keep the lights on.")
    clock.tick()

    def work(addr: str, seconds: float, *, ok: bool = True, error: str | None = None, tools=()):
        batch = org.begin_run(addr)
        stem = f"{clock.now:%Y%m%dT%H%M%S%f}"
        start = clock.now
        org.start_run_log(addr)
        traces = sorted({m.trace for m in batch if m.trace})
        for i, (tool, tool_ok) in enumerate(tools):
            log.tool(start + timedelta(seconds=1 + i), addr, tool, ok=tool_ok, ms=7 + i,
                     run=f"{addr}@{stem}", trace=traces[0] if traces else None,
                     error=None if tool_ok else "status must be one of ('done', 'failed', 'blocked')")
        clock.tick(seconds)
        stamp = clock.now.timestamp()
        os.utime(org.dir(addr) / "runs" / f"{stem}.log", (stamp, stamp))  # a run ends when its log was last written
        log.run(addr, stem, start, seconds, [m.id for m in batch], traces, ok=ok, error=error)
        return batch

    plan = org.delegate(ROOT, "ceo", "Plan the launch", "Make a launch plan.", "plan.md exists\nlaunch date named", [], 8)
    clock.tick()
    ops = org.delegate(ROOT, "ops", "Rotate the logs", "Rotate the logs.", "logs rotated", [], 2)
    clock.tick()

    work("ceo", 30, tools=[("whoami", True), ("delegate", True), ("delegate", True)])
    org.delegate("ceo", "ceo/eng", "Draft the plan", "Draft plan.md.", "plan.md exists", [], 3)
    clock.tick()
    org.delegate("ceo", "ceo/qa", "Review the plan", "Review plan.md for gaps.", "gaps listed", [], 2)
    clock.tick()
    org.end_run("ceo", ok=True)

    work("ceo/eng", 45, tools=[("report", False), ("write", True), ("report", True)])
    eng_task = next(m for m in org.received("ceo/eng") if m.type == "task")
    write_artifact(org, "ceo/eng", "ceo/eng/work/plan.md", "# Plan\nLaunch on Friday.\n", clock)
    org.report("ceo/eng", eng_task.id, "done", "Plan drafted.", ["ceo/eng/work/plan.md"])
    org.end_run("ceo/eng", ok=True)
    clock.tick()

    work("ceo/qa", 12, ok=False, error="exit code 1")
    org.end_run("ceo/qa", ok=False)  # the batch goes back to the inbox: retried later
    org.record_failure("ceo/qa")
    clock.tick()

    work("ops", 20, tools=[("whoami", True), ("report", True)])
    org.report("ops", ops.id, "done", "Logs rotated.")
    org.end_run("ops", ok=True)
    clock.tick()

    org.request(ROOT, "weekly-brief", {"topic": "ai chips"}, title="Brief on AI chips")
    clock.tick(300)
    stamp_mtimes(org, clock)
    cfg = (org.root / "ORG.md").read_text(encoding="utf-8")
    (org.root / "ORG.md").write_text(cfg.replace("events: true", "events: false"), encoding="utf-8")
    assert plan.id
    return org


STEM = re.compile(r"(\d{8}T\d{12})")


def stamp_mtimes(org: Org, clock) -> None:
    """Give every file of the org a fixed mtime (the commands read them: "last activity", run ends, hire times).
    Messages and run logs: the time in their name; everything else: the clock now. Event files keep what EventLog set."""
    now = clock.now.timestamp()
    for p in sorted(org.root.rglob("*")):
        rel = p.relative_to(org.root).parts
        if not p.is_file() or rel[0] in (".git", ".runtime") or p.name.startswith(".tmp-"):
            continue
        m = STEM.match(p.stem)
        t = datetime.strptime(m.group(1), "%Y%m%dT%H%M%S%f").replace(tzinfo=timezone.utc).timestamp() if m else now
        if p.parent.name == "runs":
            continue  # already set to the end of the run
        os.utime(p, (t, t))
