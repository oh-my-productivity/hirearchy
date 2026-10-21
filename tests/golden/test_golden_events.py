"""Golden: the shape of every event line (keys in order, value types) from a REAL scheduler run with the fake agent.

Values (ids, times, pids, durations) are not compared, only which keys each kind carries and what type they hold.
This test runs real subprocesses, so it does not use the fixed clock (a task created "in the past" would look stalled).
"""

import json
import os
import signal
import sys
import time
from collections import defaultdict

import pytest
import testkit
from golden_support import check
from testkit.health_world import Scheduler

from hirearchy import main
from hirearchy.app import wiring
from hirearchy.core import ROOT, Org
from hirearchy.eventlog import PROCS

FAKE = str(testkit.FAKE_AGENT)


@pytest.fixture(autouse=True)
def clock():  # the real clock: overrides the golden suite's fixed one
    return None


def runner(once: dict[str, str]):
    """The fake agent in ``tools`` mode (it calls the hirearchy MCP tools in-process); ``once[agent]``: the mode of its next run only."""

    def build(org, addr, prompt):
        mode = once.pop(addr, "tools")
        return [sys.executable, FAKE], org.dir(addr), {**os.environ, "ORG_ROOT": str(org.root), "ORG_AGENT": addr, "FAKE_MODE": mode}

    return build


def raw_events(org: Org) -> list[dict]:
    out = []
    for f in sorted((org.root / ".runtime" / "events").glob("*/*.jsonl")):
        out += [json.loads(line) for line in f.read_text(encoding="utf-8").splitlines()]
    return sorted(out, key=lambda e: e["ts"])


def shapes(events: list[dict]) -> str:
    keys: dict[str, dict[str, set[str]]] = defaultdict(dict)  # kind -> key -> types (insertion order = first seen)
    seen: dict[str, int] = defaultdict(int)
    present: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for ev in events:
        kind = ev["kind"]
        seen[kind] += 1
        for key, value in ev.items():
            keys[kind].setdefault(key, set()).add(type(value).__name__)
            present[kind][key] += 1
    lines = []
    for kind in sorted(keys):
        lines.append(f"{kind}:")
        for key, types in keys[kind].items():
            always = present[kind][key] == seen[kind]
            lines.append(f"  {key}: {'|'.join(sorted(types))}{'' if always else '  (not in every event)'}")
    return "\n".join(lines) + "\n"


def test_event_line_shapes_from_a_fake_agent_scheduler_run(tmp_path, monkeypatch):
    import datetime

    import hirearchy.core

    assert hirearchy.core.datetime is datetime.datetime, "this test needs the real clock"
    monkeypatch.delenv("ORG_ROOT", raising=False)
    org = Org.init(tmp_path / "org", "Shapes", {"poll_seconds": 0.05})
    org.hire(ROOT, "ceo", "Chief executive", "Run the company.", can_hire=True, max_children=2)
    org.hire("ceo", "eng", "Engineer", "Build things.")
    org.define_service(ROOT, "ceo", "brief", description="A brief.", inputs=[{"name": "topic", "description": "t", "required": True}],
                       acceptance=["short"], deliverable={"description": "a file", "format": "markdown"}, budget=8)
    org.define_service(ROOT, "ceo", "brief", add_acceptance=["At most 300 words"])  # the user's amendment: service.define with amendment true
    org.revise_playbook("ceo", "brief", "# Playbook\n1. Do it well.\n", "learned something", [])  # the first version, which needs no evidence
    org.delegate(ROOT, "ceo", "Build it", "Build the thing.", "it exists", [], 8)
    org.pause("ceo/eng", "golden: paused once")
    org.resume("ceo/eng", "golden: resumed")
    org.hire("ceo", "tmp", "Temporary", "Soon retired.")
    org.retire_team("ceo", "tmp", "golden: not needed")
    org.retire_service(ROOT, "ceo", "brief", "golden: not needed")
    main(["--root", str(org.root), "status"])  # cli.command

    previous = signal.getsignal(signal.SIGTERM)
    try:
        Scheduler(org, runner({"ceo/eng": "crash"}), echo=lambda _: None).serve(until_done=True)
    finally:
        signal.signal(signal.SIGTERM, previous)
    wiring.process_resources().reset()

    events = raw_events(org)
    kinds = {e["kind"] for e in events}
    assert {"run.start", "run.end", "tool.call", "msg.deliver", "scheduler.start", "scheduler.exit", "agent.failure",
            "agent.hire", "agent.retire", "agent.pause", "agent.resume", "service.define", "service.revise", "service.retire",
            "cli.command"} <= kinds
    check("events/line_shapes.txt", shapes(events))
    assert all(e["v"] == 1 and e["proc"] in PROCS for e in events)
