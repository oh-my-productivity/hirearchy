import asyncio
import os
import sys
import time

import testkit
from testkit.dash_fixtures import set_scheduler
from testkit.e2e_world import DashApp, NavTable, TextPane
from testkit.legacy.orgmcp.app import wiring
from testkit.scheduler import scheduler_is
from testkit.scheduler_loop import loop_over

from orgmcp.core import ROOT, Org
from orgmcp.daemon import SchedulerState


def run(coro):
    return asyncio.run(coro)


async def press(app, pilot, *keys):
    await pilot.press(*keys)
    await app.settle(pilot)


def labels(app):
    tree = app.query_one("#agent-tree")
    return {addr: node.label.plain for addr, node in tree.nodes.items()}


def pane(app, pid):
    return app.query_one(f"#{pid}", TextPane).text_now


def table_rows(app, tid):
    t = app.query_one(f"#{tid}", NavTable)
    return {k.value: [c.plain if hasattr(c, "plain") else str(c) for c in t.get_row(k)] for k in t.rows}


# ------------------------------------------------------------------------------------------ against the real scheduler
FAKE = str(testkit.FAKE_AGENT)


def _runner(mode):
    def build(org, addr, prompt):
        return [sys.executable, FAKE], org.dir(addr), {**os.environ, "ORG_ROOT": str(org.root), "ORG_AGENT": addr, "FAKE_MODE": mode}

    return build


def test_a_real_run_with_fake_agents_shows_up(tmp_path, process_overrides):
    """The real scheduler runs fake agents; the dashboard shows the finished request, the events, the trace and idle agents."""
    org = Org.init(tmp_path / "org", "Real run", {"poll_seconds": 0.05})
    org.hire(ROOT, "ceo", "Chief executive", "Run it.", can_hire=True, max_children=2)
    org.hire("ceo", "eng", "Engineer", "Build things.")
    sched = loop_over(org, _runner("tools"), echo=lambda *_: None)
    sched.acquire()
    try:
        task = org.delegate(ROOT, "ceo", "Ship it", "Ship the thing", "It is shipped", budget=6)
        deadline = time.time() + 90
        while sched.tick() and time.time() < deadline:
            time.sleep(0.02)
    finally:
        sched.release()
    set_scheduler(process_overrides, SchedulerState("stopped"))

    async def fn(app, pilot):
        got = labels(app)
        assert got["ceo"].startswith("○ ceo  idle") and got["ceo/eng"].startswith("○ eng  idle")
        await press(app, pilot, "2")
        (row,) = table_rows(app, "flows-table").values()
        assert row[0] == "done" and row[1] == "Ship it" and "/" in row[3]
        await press(app, pilot, "enter")
        await asyncio.sleep(0.5)
        await app.settle(pilot)
        text = pane(app, "flows-detail")
        assert f"trace {task.id}" in text and "ceo/eng" in text and "REFUSED" in text or "refused" in text
        await press(app, pilot, "escape", "4")
        assert " ok " in pane(app, "events-body") and "run ended ok" in pane(app, "events-body")
        await press(app, pilot, "e")
        assert "REFUSED" in pane(app, "events-body")
        await press(app, pilot, "1", "down", "down", "]", "]", "]")
        assert "exit 0 after" in pane(app, "pane-runlog") and "[last run]" in pane(app, "pane-runlog")
        assert "scheduler stopped" in str(app.query_one("#header-counts").render())

    async def go():
        app = DashApp(org.root, interval=60)
        async with app.run_test(size=(120, 34)) as pilot:
            await app.settle(pilot)
            await fn(app, pilot)

    run(go())


def test_a_real_running_agent_is_shown_running_with_its_live_log(tmp_path, process_overrides):
    org = Org.init(tmp_path / "org", "Hang", {"poll_seconds": 0.05})
    org.hire(ROOT, "ceo", "Chief executive", "Run it.", can_hire=True, max_children=2)
    org.hire(ROOT, "ops", "Ops", "Ops.")
    sched = loop_over(org, _runner("hang"), echo=lambda *_: None)
    sched.acquire()
    try:
        org.delegate(ROOT, "ceo", "Slow job", "g", "a", budget=3)
        deadline = time.time() + 20
        while not org.running("ceo") and time.time() < deadline:
            sched.tick()
            time.sleep(0.05)
        assert org.running("ceo")
        org.send(ROOT, "ceo", "second", title="Second job")  # waits behind the run
        org.delegate(ROOT, "ops", "Ops job", "g", "a", budget=2)
        org.pause("ops", "manual pause")
        scheduler_is(process_overrides, SchedulerState("running", os.getpid(), "now"), org)
        time.sleep(0.3)

        async def fn(app, pilot):
            got = labels(app)
            assert got["ceo"].startswith("▶ ceo  running ") and ", +1 unread" in got["ceo"]
            assert got["ops"].startswith("‖ ops  paused: manual pause, 1 unread")
            await press(app, pilot, "down", "]", "]", "]")
            assert app.selected == "ceo" or True
            tree = app.query_one("#agent-tree")
            tree.move_cursor(tree.nodes["ceo"])
            await app.settle(pilot)
            log = pane(app, "pane-runlog")
            assert "run of ceo, 1 message(s)" in log and "[following]" in log and "still running" in log
            overview = pane(app, "pane-overview")
            assert 'task "Slow job" from root' in overview and "1 more message(s) wait for the next run" in overview

        async def go():
            app = DashApp(org.root, interval=60)
            async with app.run_test(size=(120, 34)) as pilot:
                await app.settle(pilot)
                await fn(app, pilot)

        run(go())
    finally:
        sched.release()
        wiring.process_resources().reset()  # forget the open event files and counters of the process
