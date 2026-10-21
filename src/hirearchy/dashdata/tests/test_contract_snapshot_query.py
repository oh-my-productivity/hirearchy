"""Contract of ``SnapshotQuery``: the organization now, one state per agent, root first and then depth-first. Over the strict ports and over the dashboard's."""

from __future__ import annotations

from pathlib import Path

import pytest

from hirearchy.daemon import SchedulerState
from hirearchy.dashdata import Snapshot, SnapshotQuery
from hirearchy.dashdata.testing import IMPLEMENTATIONS, DashWorld
from hirearchy.kernel import ROOT

from ._support import make_world, running_scheduler, stamp, team


@pytest.fixture(params=IMPLEMENTATIONS[SnapshotQuery], ids=lambda factory: factory.__name__)
def w(request: pytest.FixtureRequest, tmp_path: Path) -> DashWorld:
    made = make_world(request, tmp_path)
    assert isinstance(made.snapshots, SnapshotQuery)
    return made


def words(snap: Snapshot) -> dict[str, tuple[str, str]]:
    return {a: (r.kind, r.word) for a, r in snap.agents.items() if a != ROOT}


def test_an_organization_without_agents_is_root_alone(w: DashWorld) -> None:
    snap = w.snapshots.snapshot()
    assert snap.order == [ROOT] and list(snap.agents) == [ROOT] and snap.agents[ROOT].kind == "you"
    assert (snap.running, snap.queued, snap.needs_you, snap.errors_15m, snap.retired, snap.bad_files) == (0, 0, [], 0, 0, {})
    assert snap.scheduler.text == "scheduler stopped" and snap.at == stamp(200) and snap.org_name == w.root.name


def test_root_comes_first_and_the_tree_goes_depth_first(w: DashWorld) -> None:
    team(w)
    snap = w.snapshots.snapshot()
    assert snap.order == [ROOT, "ceo", "ceo/analyst", "ceo/writer", "ops"]
    assert snap.agents["ceo"].children == ["ceo/analyst", "ceo/writer"] and snap.agents["ceo/analyst"].depth == 2
    assert snap.agents["ceo/analyst"].parent == "ceo" and snap.agents["ceo"].parent == ROOT


def test_an_agent_without_work_is_idle_and_one_with_a_task_is_working(w: DashWorld) -> None:
    team(w)
    w.obs.send("root", "ceo/writer", "task", 10, title="Write it", budget=2, box="read")
    assert words(w.snapshots.snapshot())["ceo/writer"] == ("working", "working on 1 task(s)")
    assert words(w.snapshots.snapshot())["ops"] == ("idle", "idle")


def test_an_agent_that_delegated_is_waiting_on_its_reports(w: DashWorld) -> None:
    team(w)
    w.obs.send("ceo", "ceo/analyst", "task", 10, title="Analyse", budget=2, box="read")
    assert words(w.snapshots.snapshot())["ceo"] == ("waiting", "waiting on 1 report(s)")


def test_mail_waits_for_a_scheduler_that_is_not_running(w: DashWorld) -> None:
    team(w)
    w.obs.send("root", "ops", "note", 10, title="Hello")
    kind, word = words(w.snapshots.snapshot())["ops"]
    assert (kind, word) == ("queued", "queued: scheduler is not running, 1 unread")


def test_mail_waits_for_a_free_slot_when_all_slots_are_busy(w: DashWorld) -> None:
    team(w)
    running_scheduler(w, max_parallel=1)
    w.obs.send("root", "ceo", "task", 10, title="Busy", budget=1)
    w.obs.begin_run("ceo")
    w.obs.send("root", "ops", "note", 20, title="Hello")
    snap = w.snapshots.snapshot()
    assert snap.agents["ops"].main == "queued: max_parallel (1) runs are busy" and snap.running == 1 and snap.queued == 1
    assert snap.agents["ceo"].kind == "running"


def test_mail_starts_on_the_next_tick_when_a_slot_is_free(w: DashWorld) -> None:
    team(w)
    running_scheduler(w, max_parallel=2)
    w.obs.send("root", "ops", "note", 10, title="Hello")
    assert words(w.snapshots.snapshot())["ops"] == ("queued", "queued: starts on the next tick, 1 unread")


def test_a_running_agent_says_for_how_long_and_what_waits_behind_the_run(w: DashWorld) -> None:
    team(w)
    running_scheduler(w)
    w.obs.send("root", "ceo", "task", 10, title="Busy", budget=1)
    w.obs.begin_run("ceo")
    w.obs.running("ceo", w.obs.run_log("ceo", 0))  # the registry says the run started at t=0; the dashboard shows t=200
    w.obs.send("root", "ceo", "note", 150, title="While you run")
    row = w.snapshots.snapshot().agents["ceo"]
    assert (row.kind, row.word, row.queued_behind) == ("running", "running 3m20s, +1 unread", 1) and row.elapsed_s == 200.0


def test_a_running_agent_is_marked_when_there_is_no_scheduler(w: DashWorld) -> None:
    team(w)
    w.obs.send("root", "ceo", "task", 10, title="Busy", budget=1)
    w.obs.begin_run("ceo")
    assert "(scheduler not running)" in w.snapshots.snapshot().agents["ceo"].word


def test_a_paused_agent_is_paused_whatever_else_is_true(w: DashWorld) -> None:
    team(w)
    w.obs.send("root", "ops", "note", 10, title="Hello")
    w.obs.pause("ops", "broken")
    kind, word = words(w.snapshots.snapshot())["ops"]
    assert (kind, word) == ("paused", "paused: broken, 1 unread")
    assert w.snapshots.snapshot().queued == 0


def test_an_agent_without_runs_left_is_out_of_budget(w: DashWorld) -> None:
    team(w)
    w.obs.budgets.held["ops"] = 0
    w.obs.send("root", "ops", "note", 10, title="Hello")
    assert words(w.snapshots.snapshot())["ops"] == ("budget", "out of budget, 1 unread")


def test_what_waits_for_root_is_listed(w: DashWorld) -> None:
    w.obs.waiting.entries.append(("m1", "Needs you: note from ceo"))
    snap = w.snapshots.snapshot()
    assert snap.needs_you == [("m1", "Needs you: note from ceo")] and "waiting on you 1" in snap.counts_text


def test_retired_agents_are_counted(w: DashWorld) -> None:
    (w.root / ".retired" / "old-ceo").mkdir(parents=True)
    (w.root / ".retired" / "a-file").write_text("x", encoding="utf-8")
    assert w.snapshots.snapshot().retired == 1


def test_errors_of_the_last_15_minutes_are_counted_from_the_event_log(w: DashWorld) -> None:
    w.obs.tool(150, "ceo", "delegate", ok=False, error="not enough budget")
    w.obs.tool(190, "ceo", "inbox")
    w.obs.tool(-800, "ceo", "write", ok=False, error="too old")
    snap = w.snapshots.snapshot()
    assert snap.errors_15m == 1 and snap.events_seen and snap.last_event == stamp(190)


def test_a_log_without_events_is_not_an_error(w: DashWorld) -> None:
    snap = w.snapshots.snapshot()
    assert not snap.events_seen and snap.last_event is None and snap.errors_15m == 0


def test_the_scheduler_is_told_from_its_event_file(w: DashWorld) -> None:
    running_scheduler(w)
    view = w.snapshots.snapshot().scheduler
    assert (view.state, view.pid, view.mode) == ("running", 7000, "until_done")
    assert view.uptime_s == 200.0 and view.heartbeat_age_s == 3.0
    assert view.text == "scheduler running pid 7000 (until_done, up 3m20s, heartbeat 3.0s ago)"


def test_a_scheduler_that_is_not_trusted_is_not_running(w: DashWorld) -> None:
    team(w)
    w.obs.scheduler.current = SchedulerState("unverified", 5, "x", "its command line is 'vim'")
    w.obs.send("root", "ops", "note", 10, title="Hello")
    snap = w.snapshots.snapshot()
    assert snap.scheduler.text == "scheduler unverified (pid 5: its command line is 'vim')"
    assert snap.agents["ops"].reason == "scheduler is not running"


def test_the_last_exit_of_a_scheduler_is_told_when_none_is_running(w: DashWorld) -> None:
    w.obs.marker.write("finished: no open tasks")
    assert w.snapshots.snapshot().scheduler.text == "scheduler stopped (finished: no open tasks)"


def test_the_snapshot_changes_its_signature_when_a_mailbox_changes(w: DashWorld) -> None:
    team(w)
    before = w.snapshots.snapshot().sig
    w.obs.send("root", "ops", "note", 10, title="Hello")
    w.state.refresh()
    assert w.snapshots.snapshot().sig != before


def test_the_snapshot_is_remembered_and_timed(w: DashWorld) -> None:
    snap = w.snapshots.snapshot()
    assert w.state.snap is snap and snap.ms >= 0 and w.state.feed is not None


def test_new_mail_is_seen_at_once(w: DashWorld) -> None:
    team(w)
    assert w.snapshots.snapshot().agents["ops"].unread == 0
    w.obs.send("root", "ops", "note", 10, title="Hello")
    assert w.snapshots.snapshot().agents["ops"].unread == 1
    w.obs.send("root", "ops", "note", 11, title="Again")
    assert w.snapshots.snapshot().agents["ops"].unread == 2


def test_a_new_agent_is_seen_at_once(w: DashWorld) -> None:
    team(w)
    w.snapshots.snapshot()
    w.obs.agent("research")
    assert "research" in w.snapshots.snapshot().agents
