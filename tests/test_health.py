import asyncio
import json
import os
from datetime import datetime, timedelta, timezone

import pytest

from orgmcp import core
from orgmcp.cli import main
from orgmcp.core import ROOT, Message, OrgError, join_frontmatter, split_frontmatter
from orgmcp.health import FLAGS, HEALTH_DEFAULTS, agent_health, org_health, render_text, thresholds
from orgmcp.server import build_server

T0 = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
ENG = "ceo/eng"


def at(seconds: float) -> datetime:
    return T0 + timedelta(seconds=seconds)


class Clock:
    """Replaces core.utcnow so message ids, `created` stamps and hire times are deterministic."""

    def __init__(self):
        self.t = T0

    def __call__(self):
        return self.t

    def at(self, seconds: float) -> None:
        self.t = at(seconds)


@pytest.fixture(autouse=True)
def clock(monkeypatch):
    c = Clock()
    monkeypatch.setattr(core, "utcnow", c)
    return c


def add_run(org, addr, start, end):
    """A run log named after its start with mtime = its end (seconds after T0)."""
    d = org.dir(addr) / "runs"
    d.mkdir(exist_ok=True)
    p = d / f"{at(start):%Y%m%dT%H%M%S%f}.log"
    p.touch()
    os.utime(p, (at(end).timestamp(), at(end).timestamp()))


def add_runs(org, addr, n, first=100):
    for i in range(n):
        add_run(org, addr, first + i * 100, first + i * 100 + 50)


def give(org, budget=5, to=ENG, **kw):
    """root assigns a task and the assignee reads it (no unread mail left)."""
    task = org.delegate(ROOT, to, "Job", "goal", "acceptance", budget=budget, **kw)
    org.begin_run(to)
    org.end_run(to, ok=True)
    return task


def health(org, now, addr=ENG, **limits):
    return agent_health(org, addr, at(now), {**HEALTH_DEFAULTS, **limits})


def call(server, tool, **args):
    result = asyncio.run(server.call_tool(tool, args))
    blocks = result[0] if isinstance(result, tuple) else result
    return "\n".join(getattr(b, "text", "") for b in blocks)


# --------------------------------------------------------------------- revises
def test_revises_is_stored_and_rendered(org):
    first = org.delegate(ROOT, "ceo", "Plan", "g", "a")
    second = org.delegate(ROOT, "ceo", "Plan v2", "g", "a", revises=first.id)
    assert second.revises == first.id
    loaded = Message.load(org.dir("ceo") / "inbox" / f"{second.id}.md")
    assert loaded.revises == first.id
    assert f"revises: {first.id}" in loaded.render()
    assert Message.load(org.dir("ceo") / "inbox" / f"{first.id}.md").revises is None


def test_revises_must_be_an_earlier_task_to_the_same_assignee(org):
    org.hire("ceo", "ops", "Ops", "Operate.")
    org.send(ROOT, "ceo", "budget", budget=20)
    for_eng = org.delegate("ceo", ENG, "Build", "g", "a", budget=1)
    with pytest.raises(OrgError, match="revises"):
        org.delegate("ceo", "ceo/ops", "Build", "g", "a", revises=for_eng.id)  # other assignee
    with pytest.raises(OrgError, match="revises"):
        org.delegate("ceo", ENG, "Build", "g", "a", revises="nope")  # unknown id
    with pytest.raises(OrgError, match="revises"):
        org.delegate(ROOT, "ceo", "Build", "g", "a", revises=for_eng.id)  # not sent by this delegator
    note = org.send("ceo", ENG, "just a note")
    with pytest.raises(OrgError, match="revises"):
        org.delegate("ceo", ENG, "Build", "g", "a", revises=note.id)  # not a task
    assert org.delegate("ceo", ENG, "Build again", "g", "a", revises=for_eng.id).revises == for_eng.id


def test_revises_through_the_mcp_tool_and_cli(org, capsys):
    first = org.delegate(ROOT, "ceo", "Plan", "g", "a")
    out = call(build_server(org, ROOT), "delegate", to="ceo", title="Plan 2", goal="g", acceptance="a",
               revises=first.id)
    assert "delegated" in out
    main(["--root", str(org.root), "task", "ceo", "--title", "Plan 3", "--goal", "g", "--acceptance", "a",
          "--revises", first.id])
    assert capsys.readouterr().out.startswith("task ")
    assert sum(1 for m in org.received("ceo") if m.revises == first.id) == 2
    with pytest.raises(SystemExit):
        main(["--root", str(org.root), "task", "ceo", "--title", "x", "--goal", "g", "--acceptance", "a",
              "--revises", "bogus"])
    assert "revises" in capsys.readouterr().err


# --------------------------------------------------------------------- metrics
def test_agent_metrics(org, clock):
    clock.at(0)
    t1 = org.delegate(ROOT, ENG, "One", "g", "a", budget=6)
    t2 = org.delegate(ROOT, ENG, "Two", "g", "a", budget=2)
    add_run(org, ENG, 60, 120)
    clock.at(90)
    org.report(ENG, t1.id, "done", "ok")  # sent inside run 1
    add_run(org, ENG, 200, 260)  # run 2 sends nothing
    clock.at(300)
    t3 = org.delegate(ROOT, ENG, "Two again", "g", "a", budget=3, revises=t2.id)
    add_run(org, ENG, 380, 420)
    clock.at(400)
    org.report(ENG, t2.id, "failed", "no")  # sent inside run 3

    h = health(org, 1000)
    assert (h.addr, h.depth, h.state) == (ENG, 2, "pending")
    assert (h.budget_received, h.runs_used, h.budget_left) == (11, 3, 8)
    assert (h.tasks_received, h.open_tasks, h.oldest_open_age) == (3, 1, 700)
    assert (h.done, h.failed, h.blocked) == (1, 1, 0)
    assert h.runs_per_task == 1.5
    assert h.rework == 1
    assert h.empty_runs == 1
    assert h.last_activity == at(420) and h.since_activity == 580
    assert t3.id in {t.id for t in org.open_tasks(ENG)}


def test_blocked_results_and_no_results(org, clock):
    t = give(org)
    h = health(org, 10)
    assert h.runs_per_task is None and h.done == h.failed == h.blocked == 0
    clock.at(5)
    org.report(ENG, t.id, "blocked", "waiting")
    assert health(org, 10).blocked == 1


def test_never_active_agent_has_no_activity(org):
    h = health(org, 50)
    assert h.last_activity is None and h.since_activity is None
    assert h.oldest_open_age is None and h.open_tasks == 0 and h.empty_runs == 0


def test_run_in_progress_is_not_empty(org):
    give(org)
    add_run(org, ENG, 100, 100)
    assert health(org, 500).empty_runs == 1
    org.delegate(ROOT, ENG, "More", "g", "a")
    org.begin_run(ENG)  # now running: its newest run is still going
    assert health(org, 500).empty_runs == 0


def test_agent_health_rejects_root(org):
    with pytest.raises(OrgError, match="root"):
        agent_health(org, ROOT, at(0))


# ----------------------------------------------------------------------- flags
def test_stuck(org):
    give(org)
    assert "stuck" not in health(org, 1800).flags  # not older than the threshold yet
    assert "stuck" in health(org, 1801).flags
    assert "30m" in health(org, 1801).flags["stuck"]


def test_not_stuck_while_running_unread_or_waiting(org, clock):
    org.send(ROOT, "ceo", "budget", budget=10)
    t = give(org, to="ceo")
    clock.at(1)
    org.delegate("ceo", ENG, "Sub", "g", "a", budget=3)  # ceo now waits on eng
    assert "stuck" not in health(org, 5000, "ceo").flags
    assert "stuck" not in health(org, 5000, ENG).flags  # eng has unread mail
    org.begin_run(ENG)
    assert "stuck" not in health(org, 5000, ENG).flags  # running
    org.end_run(ENG, ok=True)
    assert "stuck" in health(org, 5000, ENG).flags  # read, open, nobody working on it
    org.report("ceo", t.id, "done", "x")
    assert "stuck" not in health(org, 5000, "ceo").flags


def test_out_of_budget(org):
    t = give(org, budget=1)
    add_run(org, ENG, 10, 20)
    assert health(org, 30).budget_left == 0
    assert "out_of_budget" in health(org, 30).flags
    org.report(ENG, t.id, "done", "x")
    assert "out_of_budget" not in health(org, 30).flags  # nothing left to do
    org.delegate(ROOT, ENG, "Unread", "g", "a", budget=1)
    add_run(org, ENG, 40, 50)  # budget 0 again, with unread mail
    assert "out_of_budget" in health(org, 60).flags


def test_paused_reason_is_reported(org):
    org.pause(ENG, "3 consecutive failures")
    h = health(org, 10)
    assert h.state.startswith("paused") and h.flags["paused"] == "paused: 3 consecutive failures"


def test_expensive_runs_per_completed_task(org, clock):
    t = give(org)
    clock.at(10)
    org.report(ENG, t.id, "done", "x")
    add_runs(org, ENG, 5)
    assert "expensive" not in health(org, 1000).flags  # 5.0 runs per task is at the limit
    add_runs(org, ENG, 1, first=900)
    h = health(org, 1000)
    assert h.runs_per_task == 6 and "6.0 runs per completed task (max 5)" in h.flags["expensive"]


def test_expensive_runs_without_result_on_open_task(org):
    give(org)
    add_runs(org, ENG, 6)
    assert "expensive" not in health(org, 1000).flags
    add_runs(org, ENG, 1, first=900)
    assert "7 runs without a result" in health(org, 1000).flags["expensive"]


def test_runs_without_result_count_only_runs_since_the_last_result(org, clock):
    first = give(org)
    add_runs(org, ENG, 7)  # many runs before the result
    clock.at(800)
    org.report(ENG, first.id, "done", "x")
    give(org)
    add_runs(org, ENG, 2, first=900)
    assert "expensive" not in health(org, 2000, max_runs_per_task=100).flags


def test_low_quality_counts_failed_blocked_and_rework(org, clock):
    t1, t2, t3 = give(org), give(org), give(org)
    clock.at(5)
    org.report(ENG, t1.id, "failed", "x")
    org.report(ENG, t2.id, "done", "x")
    assert "low_quality" not in health(org, 10).flags  # 1 of 3
    org.report(ENG, t3.id, "blocked", "x")
    h = health(org, 10)
    assert h.flags["low_quality"] == "2 of 3 tasks failed, blocked or were sent back"
    # rework counts too: two done tasks, two of the four tasks are sent-back revisions
    other = "ceo/ops"
    org.hire("ceo", "ops", "Ops", "x")
    a = give(org, to=other)
    clock.at(6)
    org.report(other, a.id, "done", "x")
    give(org, to=other, revises=a.id)
    give(org, to=other, revises=a.id)
    assert agent_health(org, other, at(10)).rework == 2
    assert "low_quality" in agent_health(org, other, at(10)).flags


def test_low_quality_needs_a_minimum_sample(org, clock):
    t1, t2 = give(org), give(org)
    clock.at(5)
    org.report(ENG, t1.id, "failed", "x")
    org.report(ENG, t2.id, "failed", "x")
    assert "low_quality" not in health(org, 10).flags
    assert "low_quality" in health(org, 10, min_tasks_for_quality=2).flags


def test_wasteful(org, clock):
    add_runs(org, ENG, 3)
    assert "wasteful" not in health(org, 1000).flags  # below the minimum sample
    add_runs(org, ENG, 1, first=500)
    assert health(org, 1000).flags["wasteful"] == "4 of 4 runs sent no message"
    clock.at(150)
    org.send(ENG, "ceo", "hello")  # inside run 1 (100..150)
    clock.at(350)
    org.send(ENG, "ceo", "hello again")  # inside run 3 (300..350)
    h = health(org, 1000)
    assert h.empty_runs == 2 and "wasteful" not in h.flags  # 0.5 is at the limit


def test_idle(org):
    assert "idle" not in health(org, 86400).flags
    h = health(org, 86401)  # never did anything: measured from when it was hired
    assert "idle" in h.flags and "retire" in h.flags["idle"]


def test_idle_is_measured_from_the_last_activity(org):
    add_run(org, ENG, 80000, 80100)
    assert "idle" not in health(org, 90000).flags
    assert "idle" in health(org, 80100 + 86401).flags


def test_not_idle_with_open_tasks(org):
    give(org)
    flags = health(org, 200000).flags
    assert "idle" not in flags and "stuck" in flags


def test_thresholds_can_be_overridden_in_org_md(org):
    assert thresholds(org) == HEALTH_DEFAULTS
    meta, body = split_frontmatter((org.root / "ORG.md").read_text())
    (org.root / "ORG.md").write_text(join_frontmatter({**meta, "health": {"idle_after_seconds": 60}}, body))
    assert thresholds(org)["idle_after_seconds"] == 60
    assert thresholds(org)["stuck_after_seconds"] == HEALTH_DEFAULTS["stuck_after_seconds"]
    assert "idle" in agent_health(org, ENG, at(61)).flags  # picked up without passing limits
    (org.root / "ORG.md").write_text(join_frontmatter({**meta, "health": "nonsense"}, body))
    assert thresholds(org) == HEALTH_DEFAULTS


def test_every_flag_has_a_severity():
    assert set(FLAGS) == {"stuck", "out_of_budget", "paused", "low_quality", "expensive", "wasteful", "stranded_budget", "idle"}


# ---------------------------------------------------------- branches and report
@pytest.fixture
def troubled(org):
    """ceo is paused; eng has an old open task nobody works on."""
    give(org)
    org.pause("ceo", "manual")
    add_runs(org, "ceo", 2)
    add_runs(org, ENG, 3, first=200)
    return org


def test_branch_totals_and_worst_flag(troubled):
    report = org_health(troubled, now=at(5000))
    assert [a.addr for a in report.agents] == ["ceo", ENG]
    ceo, eng = report.branches["ceo"], report.branches[ENG]
    assert (ceo.agents, ceo.runs_used, ceo.open_tasks) == (2, 5, 1)
    assert ceo.worst_flag == "stuck"  # eng's flag outranks ceo's own `paused`
    assert (eng.agents, eng.runs_used, eng.worst_flag) == (1, 3, "stuck")
    assert report.branches[ROOT].runs_used == 5 and report.branches[ROOT].worst_flag == "stuck"
    assert [a.addr for a in report.flagged] == ["ceo", ENG]


def test_branch_without_flags_has_no_worst_flag(org):
    report = org_health(org, now=at(10))
    assert report.flagged == [] and report.branches["ceo"].worst_flag is None


def test_org_health_scopes_to_a_subtree(org):
    assert [a.addr for a in org_health(org, ENG, at(10)).agents] == [ENG]
    assert [a.addr for a in org_health(org, "ceo", at(10)).agents] == ["ceo", ENG]
    assert [a.addr for a in org_health(org, ROOT, at(10)).agents] == ["ceo", ENG]
    with pytest.raises(OrgError):
        org_health(org, "nobody", at(10))


def test_render_text(troubled):
    lines = render_text(org_health(troubled, now=at(5000))).splitlines()
    assert lines[0] == "2 agents, 2 flagged"
    assert lines[1].startswith("ceo paused(manual), ") and "!paused: paused: manual" in lines[1]
    assert "| branch: runs 5, open 1" in lines[1] and "worst stuck" in lines[1]
    assert lines[2].startswith("  eng idle, ")
    assert "open 1 (oldest 1h)" in lines[2] and "!stuck: open task is 1h old" in lines[2]
    assert "branch:" not in lines[2]


def test_render_text_for_a_clean_org(org):
    assert render_text(org_health(org, now=at(10))).splitlines()[0] == "2 agents, 0 flagged"
    assert render_text(org_health(org, ENG, at(10))).splitlines()[0] == "1 agent, 0 flagged"


def test_to_dict_is_json(troubled):
    data = json.loads(json.dumps(org_health(troubled, now=at(5000)).to_dict()))
    assert data["flagged"] == ["ceo", ENG]
    assert data["now"] == at(5000).isoformat()
    eng = data["agents"][1]
    assert eng["flags"]["stuck"] and eng["last_activity"] == at(450).isoformat()
    assert data["branches"]["ceo"]["worst_flag"] == "stuck"


def test_mcp_health_permissions(org):
    org.hire("ceo", "ops", "Ops", "Operate.")
    root, ceo, eng = (build_server(org, a) for a in (ROOT, "ceo", ENG))
    assert call(root, "health").splitlines()[0] == "3 agents, 0 flagged"  # whole org by default
    assert call(root, "health", agent=ENG).splitlines()[0] == "1 agent, 0 flagged"
    assert call(ceo, "health").splitlines()[0] == "3 agents, 0 flagged"  # own subtree by default
    assert call(ceo, "health", agent="ceo/ops").splitlines()[0] == "1 agent, 0 flagged"
    assert call(eng, "health").splitlines()[0] == "1 agent, 0 flagged"
    assert call(eng, "health", agent=ENG).splitlines()[0] == "1 agent, 0 flagged"
    for who, target in ((eng, "ceo"), (eng, "ceo/ops"), (ceo, ROOT)):
        with pytest.raises(Exception, match="own subtree"):
            call(who, "health", agent=target)
    with pytest.raises(Exception, match="no such agent"):
        call(root, "health", agent="nobody")
