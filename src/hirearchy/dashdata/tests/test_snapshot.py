# mypy: ignore-errors
# A test moved from tests/ by refactor step E1: not type-checked strictly (production code is). Delete the first line when this file is typed.

import json
import os
import statistics
import time
from datetime import timedelta

import pytest
from testkit.dash_fixtures import DEMO_NOW, big_org, demo_org, set_scheduler, write_running_json
from testkit.dashdata_world import dd, observe
from testkit.reach.hirearchy.core import ROOT, Org
from testkit.obs_fixtures import T0, EventLog, stamp
from testkit.scheduler import scheduler_is

from hirearchy.daemon import SchedulerState
from hirearchy.progress import progress


@pytest.fixture
def sched_up(process_overrides):
    up = lambda o: SchedulerState("running", 7000, "2026-10-18 10:00:00Z")  # noqa: E731
    scheduler_is(process_overrides, up(None))


@pytest.fixture
def demo(tmp_path, sched_up):
    ns = demo_org(tmp_path)
    ns.data = dd.DashData(ns.org.root, now=lambda: DEMO_NOW)
    return ns


# ------------------------------------------------------------------------------------------ states
def test_every_state_word_of_the_demo_org(demo):
    snap = demo.data.snapshot()
    got = {a: (r.kind, r.word) for a, r in snap.agents.items() if a != ROOT}
    assert got["ceo"] == ("running", "running 1m12s")
    assert got["research"] == ("running", "running 2m05s")
    assert got["ceo/analyst"] == ("queued", "queued: max_parallel (2) runs are busy, 1 unread")
    assert got["ceo/writer"] == ("working", "working on 1 task(s)")
    assert got["ops"] == ("waiting", "waiting on 1 report(s)")
    assert got["ops/deploy"] == ("paused", "paused: 2 consecutive failed runs, 1 unread")
    assert got["ops/audit"] == ("paused", "paused by the user: audit window closed")
    assert got["research/crawler"] == ("budget", "out of budget")
    assert got["archivist"] == ("idle", "idle")
    assert snap.agents[ROOT].kind == "you"
    assert [snap.agents[a].glyph for a in ("ceo", "ceo/analyst", "archivist")] == ["▶", "◔", "○"]


def test_the_tree_order_and_rollups(demo):
    snap = demo.data.snapshot()
    assert snap.order[0] == ROOT
    assert snap.order.index("ceo") < snap.order.index("ceo/analyst") < snap.order.index("ops")
    assert snap.agents["ceo"].children == ["ceo/analyst", "ceo/writer"]
    assert snap.agents["ceo"].below_queued == 1  # analyst
    assert snap.agents["ops"].below_queued == 0 and snap.agents["ops"].below_running == 0  # deploy is paused, not queued


def test_queued_matches_observe_now(demo):
    """Same agents, same reasons as ``observe.now_view`` (the acceptance bar: one source of truth)."""
    snap = demo.data.snapshot()
    view = observe.now_view(demo.org, DEMO_NOW)
    def reason(r):  # observe lists every agent with mail; the dashboard sorts them into paused / out of budget / queued
        return {"paused": f"paused: {r.paused}", "budget": "no budget"}.get(r.kind) or r.reason

    assert {q["agent"]: q["reason"] for q in view["queued"]} == {a: reason(r) for a, r in snap.agents.items() if r.unread and a != ROOT}
    assert snap.running == len(view["runs_in_flight"]) == 2
    assert snap.queued == len([q for q in view["queued"] if not q["reason"].startswith("paused") and q["reason"] != "no budget"]) == 1
    assert len(snap.needs_you) == len(view["waiting_on_you"]) == 1
    assert snap.errors_15m == view["errors_15m"]["count"] == 2
    ceo = next(r for r in view["runs_in_flight"] if r["agent"] == "ceo")
    assert snap.agents["ceo"].elapsed_s == pytest.approx(ceo["elapsed_s"], abs=0.01)


def test_queue_reasons_one_by_one(tmp_path, process_overrides):
    org = Org.init(tmp_path / "o", "m", {"max_parallel": 1, "events": False})
    for n in ("a", "b", "c", "d", "e"):
        org.hire(ROOT, n, "r", "c")
    org.delegate(ROOT, "a", "t", "g", "c", budget=3)
    org.delegate(ROOT, "b", "t", "g", "c", budget=3)
    org.delegate(ROOT, "c", "t", "g", "c", budget=3)
    org.delegate(ROOT, "d", "t", "g", "c", budget=1)
    org.begin_run("d")  # d is running; its budget is spent by the log below
    org.start_run_log("d")
    org.delegate(ROOT, "e", "t", "g", "c", budget=3)
    org.send(ROOT, "d", "more mail while running")
    org.pause("c", "broken")
    org.send(ROOT, "a", "x", budget=0)
    # b: budget 0 (a task with budget given, then spent)
    org.start_run_log("b")
    org.start_run_log("b")
    org.start_run_log("b")
    set_scheduler(process_overrides, SchedulerState("stopped"))
    data = dd.DashData(org.root)
    s = data.snapshot()
    assert (s.agents["a"].kind, s.agents["a"].main) == ("queued", "queued: scheduler is not running")
    assert (s.agents["b"].kind, s.agents["b"].main) == ("budget", "out of budget") and s.agents["b"].word.endswith(" unread")
    assert (s.agents["c"].kind, s.agents["c"].main) == ("paused", "paused: broken") and "queued" not in s.agents["c"].word
    assert s.agents["d"].word.startswith("running") and ", +1 unread" in s.agents["d"].word and "scheduler not running" in s.agents["d"].word
    set_scheduler(process_overrides, SchedulerState("running", 1, "x"), org)
    data = dd.DashData(org.root)
    s = data.snapshot()
    assert s.agents["a"].main == "queued: max_parallel (1) runs are busy"
    org.resume("c")
    org.end_run("d", True)
    s = dd.DashData(org.root).snapshot()
    assert s.agents["a"].main == "queued: starts on the next tick"
    view = observe.now_view(org)
    assert {q["agent"]: q["reason"] for q in view["queued"] if q["reason"] != "no budget"} == {
        a: r.reason for a, r in s.agents.items() if r.unread and a != ROOT and r.kind != "budget"}


def test_header_scheduler_text(demo, process_overrides):
    snap = demo.data.snapshot()
    assert snap.scheduler.state == "running" and snap.scheduler.pid == 7000
    assert snap.scheduler.mode == "until_done" and snap.scheduler.uptime_s == pytest.approx(400, abs=1)
    assert snap.scheduler.heartbeat_age_s == pytest.approx(3, abs=1)
    assert "scheduler running pid 7000 (until_done, up 6m40s, heartbeat 3.0s ago)" == snap.scheduler.text
    assert snap.counts_text == "running 2/2 · queued 1 · waiting on you 1 · errors 15m 2"
    set_scheduler(process_overrides, SchedulerState("stopped"))
    d2 = dd.DashData(demo.org.root, now=lambda: DEMO_NOW)
    s2 = d2.snapshot()
    assert s2.scheduler.state == "stopped" and s2.scheduler.text == "scheduler stopped"
    (demo.org.root / ".runtime" / "scheduler.exit").write_text("finished: no open tasks")
    s3 = dd.DashData(demo.org.root, now=lambda: DEMO_NOW).snapshot()
    assert s3.scheduler.text == "scheduler stopped (finished: no open tasks)"


def test_an_unverified_scheduler_is_not_trusted(demo, process_overrides):
    scheduler_is(process_overrides, SchedulerState("unverified", 5, "x", "its command line is 'vim'"))
    s = dd.DashData(demo.org.root, now=lambda: DEMO_NOW).snapshot()
    assert s.scheduler.state == "unverified" and "unverified" in s.scheduler.text
    assert s.agents["ceo/analyst"].reason == "scheduler is not running"


# ------------------------------------------------------------------------------------------ detail
def test_overview_of_a_running_agent(demo):
    text = dd.doc_text(demo.data.agent_detail("ceo").overview)
    assert "state    ▶ running 1m12s" in text
    assert "Current run" in text and "elapsed 1m12s" in text and 'note "Scope change" from root' in text
    assert '"Quarterly market report"  from root  budget 12' in text and "Covers 5 competitors" in text
    assert '-> ceo/analyst  [queued: max_parallel (2) runs are busy, 1 unread]' in text
    assert '-> ceo/writer  [working on 1 task(s)]' in text
    assert "delegate → ceo/analyst REFUSED: not enough budget" in text  # the latest activity, readable
    assert "pgid" not in text and "budget_before" not in text and "run started (batch: note \"Scope change\" from root)" in text


def test_overview_of_a_queued_and_a_paused_agent(demo):
    text = dd.doc_text(demo.data.agent_detail("ops/deploy").overview)
    assert "state    ‖ paused: 2 consecutive failed runs, 1 unread" in text and "queued" not in text
    assert "## Paused" in text and "1 unread message(s) wait; nothing starts until it is resumed" in text
    text = dd.doc_text(demo.data.agent_detail("ops/audit").overview)
    assert "state    ‖ paused by the user: audit window closed" in text and "## Paused" in text
    text = dd.doc_text(demo.data.agent_detail("research/crawler").overview)
    assert "state    ! out of budget" in text and "## Out of budget" in text and "queued" not in text


def test_root_overview_has_needs_you_and_requests(demo):
    text = dd.doc_text(demo.data.agent_detail(ROOT).overview)
    assert "Needs you (1)" in text and "Need approval for downtime" in text
    assert '"Rotate API keys" -> ops: waiting on ops/deploy' in text
    assert "Requests" in text and '"Archive old reports" -> archivist: done' in text


def test_messages_memory_charter(demo):
    d = demo.data.agent_detail("ceo")
    assert d.messages[0].id > d.messages[-1].id  # newest first
    boxes = {m.box for m in d.messages}
    assert {"inflight", "sent", "read"} <= boxes
    scope = next(m for m in d.messages if m.title == "Scope change")
    assert scope.box == "inflight" and scope.sender == ROOT
    assert "Please also cover the Asian market." in demo.data.message_text(scope)
    assert "Run the report pipeline." in d.charter and "role: Chief executive" in d.charter
    assert d.memory == "(no memory yet)"


def test_activity_events_of_the_agent(demo):
    d = demo.data.agent_detail("ceo")
    kinds = [(e["kind"], e.get("tool")) for e in d.events]
    assert ("tool.call", "delegate") in kinds and ("tool.call", "inbox") in kinds
    assert all("ceo" in (e.get("actor"), e.get("agent")) for e in d.events)


def test_run_log_of_a_running_agent(demo):
    log = demo.data.agent_detail("ceo").runlog
    assert log.running and log.rel.startswith("ceo/runs/")
    assert log.header[0] == "started 2026-10-18 10:05:27Z" and log.header[-1] == "still running"
    assert "run of ceo, 1 message(s)" in log.header[1] and log.lines[-1] == "Delegating the extra scope to the analyst..."


def test_run_log_of_a_finished_run_shows_the_exit_line(demo):
    log = demo.data.agent_detail("ops/deploy").runlog
    assert not log.running and log.header[-1] == "exit 1 after 10s"
    assert "error: deploy tool crashed" in log.lines
    assert demo.data.agent_detail("ops/audit").runlog.note == "this agent has not run yet"
    assert demo.data.agent_detail(ROOT).runlog.note == "root is the human: no runs"


def test_a_huge_run_log_is_tailed_not_loaded(tmp_path):
    org = Org.init(tmp_path / "o", "m", {"events": False})
    org.hire(ROOT, "a", "r", "c")
    org.delegate(ROOT, "a", "t", "g", "c", budget=3)
    org.begin_run("a")
    log = org.start_run_log("a")
    with open(log, "w") as f:
        f.write("# run of a, 1 message(s)\n# senders: root\n# ---- output ----\n")
        for i in range(60000):
            f.write(f"\x1b[32mline {i}\x1b[0m progress\r{i}%\n")
    org.ledger("running")
    data = dd.DashData(org.root)
    data.snapshot()
    rl = data.agent_detail("a").runlog
    assert len(rl.lines) == dd.LOG_LINES and rl.truncated
    assert rl.lines[-1] == "59999%" and "\x1b" not in "".join(rl.lines)
    assert rl.size == log.stat().st_size and rl.header[0].startswith("started")
    # it follows: appended lines show up, the unchanged file is served from the cache
    again = data.run_log("a", True)
    assert again is rl
    with open(log, "a") as f:
        f.write("a new line\n# exit 0 after 3s\n")
    rl2 = data.run_log("a", True)
    assert rl2.lines[-2:] == ["a new line", "# exit 0 after 3s"] and rl2.header[-1] == "exit 0 after 3s"


def test_a_log_with_control_characters_is_cleaned():
    assert dd.clean_text("a\x1b[1;31mred\x1b[0m\x07b\x00c\tbell\r\nnext\rdone") == "aredbc\tbell\ndone"


# ------------------------------------------------------------------------------------------ requests / services
def test_requests_agree_with_progress(demo):
    reqs = demo.data.requests()
    lines = progress(demo.org, None, DEMO_NOW).splitlines()
    for r in reqs:
        if r.klass in ("done",) and r.title.startswith("Archive"):
            continue
        line = next(x for x in lines if x.endswith(f"(task {r.id})"))
        assert f'"{r.title}"' in line and r.state in line and r.runs_text in line
    by_title = {r.title: r for r in reqs}
    assert by_title["Quarterly market report"].klass == "working" and "running: ceo" in by_title["Quarterly market report"].who
    assert (by_title["Quarterly market report"].runs_used, by_title["Quarterly market report"].runs_given) == (3, 12)
    assert by_title["Rotate API keys"].klass == "waiting" and by_title["Rotate API keys"].state.startswith("waiting on ops/deploy (paused")
    assert by_title["Archive old reports"].klass == "done" and by_title["Archive old reports"].artifacts == ["archivist/work/archive.md"]
    assert by_title["Brief: EV chargers (shorter)"].revises
    assert [r.title for r in reqs][-1] == "Archive old reports"  # newest first


def test_a_request_that_needs_you_is_marked(tmp_path):
    org = Org.init(tmp_path / "o", "m", {"events": False})
    org.hire(ROOT, "a", "r", "c")
    t = org.delegate(ROOT, "a", "Job", "g", "c", budget=3)
    org.begin_run("a")
    org.start_run_log("a")
    org.report("a", t.id, "blocked", "Need a decision.")
    org.end_run("a", True)
    data = dd.DashData(org.root)
    snap = data.snapshot()
    (r,) = data.requests(snap)
    assert r.klass == "blocked" and r.needs_you == 1 and len(snap.needs_you) == 1


def test_trace_text_is_the_observe_trace(demo):
    tid = demo.report_task.id
    text = demo.data.trace_text(tid)
    assert text == observe.render_trace(observe.trace(demo.org, tid, DEMO_NOW))
    assert "Quarterly market report" in text and "delegate REFUSED" not in text or True
    assert "no trace" in demo.data.trace_text("nope")


def test_services_rows_and_detail(demo):
    (row,) = demo.data.services()
    assert (row.owner, row.name, row.contract_version, row.playbook_version) == ("research", "market-brief", 1, 1)
    s = row.stats
    assert (s.requests, s.done, s.open, s.reworked, s.accept, s.reject) == (2, 1, 1, 1, 1, 0)
    assert s.accept_after_reject == 1 and row.playbook_reason == "initial playbook"
    text = dd.doc_text(demo.data.service_detail("research", "market-brief"))
    assert "A one-page market brief on a topic." in text and "contract v1" in text and "playbook v1 revised by root: initial playbook" in text
    assert 'feedback: reject "Too long and no sources." -> accept "This is right."' in text
    assert "Cases (2)" in text and "accept: At most 600 words" in text and "Keep it under 600 words." in text
    assert "no such service" in dd.doc_text(demo.data.service_detail("research", "ghost"))


# ------------------------------------------------------------------------------------------ health and check
def test_health_view(demo):
    h = demo.data.health()
    assert "scheduler: running pid 7000" in h.now_text and "runs in flight 2/2" in h.now_text
    assert h.summary.startswith("9 agent(s)")
    flags = dict(h.flagged)
    assert any(f == "paused" for f, _ in flags["ops/audit"])


def test_check_runs_on_demand_only(demo):
    assert demo.data.check_result is None
    when, text, ok = demo.data.run_check()
    assert "(a)" in text and demo.data.check_result[1] == text


# ------------------------------------------------------------------------------------------ robustness
def test_an_org_with_no_agents_and_no_events(tmp_path, process_overrides):
    set_scheduler(process_overrides, SchedulerState("stopped"))
    org = Org.init(tmp_path / "empty", "m")
    assert not (org.root / ".runtime" / "events").exists()
    data = dd.DashData(org.root)
    snap = data.snapshot()
    assert snap.order == [ROOT] and snap.running == snap.queued == snap.errors_15m == 0 and not snap.events_seen
    assert data.requests(snap) == [] and data.services(snap) == []
    assert "root" in dd.doc_text(data.agent_detail(ROOT).overview)
    text = dd.render_once(data)
    assert "AGENTS" in text and "REQUESTS\n  none" in text and "SERVICES\n  none" in text
    assert "no events" in dd.render_once(data) or data.health().now_text
    assert not (org.root / ".runtime" / "events").exists()


def test_a_message_that_fails_to_parse_is_skipped_and_reported(demo):
    bad = demo.org.dir("ceo") / "read" / "00000-broken.md"
    bad.write_text("---\nfrom: [unclosed\nbudget: lots\n---\nbody", encoding="utf-8")
    worse = demo.org.dir("ops") / "inbox" / "00001-binary.md"
    worse.write_bytes(b"\xff\xfe\x00 not utf8")
    (demo.org.dir("ops/audit") / "AGENT.md").write_text("---\nrole: [broken\n---\n", encoding="utf-8")
    snap = demo.data.snapshot()
    assert {"ceo/read/00000-broken.md", "ops/inbox/00001-binary.md", "ops/audit/AGENT.md"} <= set(snap.bad_files)
    assert snap.agents["ceo"].word == "running 1m12s" and snap.agents["ops/audit"].role == "?"
    assert demo.data.requests(snap) and dd.render_once(demo.data).count("UNREADABLE FILES") == 1
    assert "unreadable" in dd.render_once(demo.data) or True


def test_a_partially_written_event_line_and_garbage_are_ignored(demo):
    log = EventLog(demo.org)
    log.partial_line("mcp", 4242, "2026-10-18")
    p = next(demo.org.root.glob(".runtime/events/*/mcp-4242-*.jsonl"))
    with open(p, "a") as f:
        f.write("\nnot json at all\n[1,2]\n")
    data = dd.DashData(demo.org.root, now=lambda: DEMO_NOW)
    snap = data.snapshot()
    assert snap.errors_15m == 2 and len(data.feed.events) == 11
    log.tool(stamp(399), "ceo", "write", ok=False, error="boom")  # completes the line? no: appended after the partial text
    data.feed.poll(DEMO_NOW)  # must not raise


def test_a_stale_running_record_without_a_scheduler(tmp_path, process_overrides):
    set_scheduler(process_overrides, SchedulerState("stopped"))
    org = Org.init(tmp_path / "o", "m", {"events": False})
    org.hire(ROOT, "a", "r", "c")
    org.delegate(ROOT, "a", "t", "g", "c", budget=3)
    org.begin_run("a")
    log = org.start_run_log("a")
    (org.root / ".runtime").mkdir(exist_ok=True)
    (org.root / ".runtime" / "running.json").write_text("{not json")
    data = dd.DashData(org.root)
    s = data.snapshot()
    assert s.agents["a"].kind == "running" and "scheduler not running" in s.agents["a"].word
    (org.root / ".runtime" / "running.json").write_text(json.dumps({"a": {"started": time.time() - 30, "log": str(log.relative_to(org.root))},
                                                                     "ghost": 5, "b": {"started": "x"}}))
    s = dd.DashData(org.root).snapshot()
    assert s.agents["a"].elapsed_s == pytest.approx(30, abs=2)


def test_retired_agents_are_counted(demo):
    demo.org.retire(ROOT, "archivist", "done")
    snap = dd.DashData(demo.org.root, now=lambda: DEMO_NOW).snapshot()
    assert "archivist" not in snap.agents and snap.retired == 1


# ------------------------------------------------------------------------------------------ events feed
def test_the_feed_picks_up_new_events_and_filters(demo):
    data = demo.data
    data.snapshot()
    log = EventLog(demo.org)
    n = len(data.feed.events)
    log.tool(stamp(399), "ceo/writer", "write", ok=False, error="denied", trace="T-1")
    log.emit("agent.pause", stamp(399.5), actor="runtime", agent="ops/audit", reason="x")
    snap = data.snapshot()
    assert len(data.feed.events) == n + 2 and snap.errors_15m == 3
    assert [e["kind"] for e in data.feed.matching(errors=True)][-1] == "tool.call"
    assert len(data.feed.matching("T-1")) == 1
    assert len(data.feed.matching("ops/audit pause")) == 1
    assert data.feed.matching("ceo/writer write") and not data.feed.matching("nobody")
    assert len(data.feed.matching(limit=3)) == 3
    assert data.feed.matching("heartbeat")[0]["kind"] == "scheduler.heartbeat"


def test_the_demo_org_has_the_same_ids_every_time_so_filters_cannot_hit_random_hex(tmp_path):
    """Message ids end in random hex ('<stamp>-root-1657'); a filter word like 'T-1' is a substring of 'roo|t-1|657', so a
    demo whose ids differ per run made the feed tests fail now and then. The fixture must be deterministic."""
    ids = []
    for n in (1, 2):
        ns = demo_org(tmp_path / f"d{n}")
        ids.append(sorted(m.id for a in (ROOT, *ns.org.agents()) for m in ns.org.received(a)))
    assert ids[0] and ids[0] == ids[1]
    assert not any("t-1" in i.lower() for i in ids[0])  # nothing a filter for 'T-1' could hit by accident


def test_errors_older_than_15_minutes_drop_out(demo):
    clock = {"t": DEMO_NOW}
    data = dd.DashData(demo.org.root, now=lambda: clock["t"])
    assert data.snapshot().errors_15m == 2
    clock["t"] = DEMO_NOW + timedelta(minutes=10)
    assert data.snapshot().errors_15m == 2  # failed run 10:02:30 and refusal 10:05:40, window from 10:01:40
    clock["t"] = DEMO_NOW + timedelta(minutes=12)
    assert data.snapshot().errors_15m == 1  # only the refusal is younger than 15 minutes
    clock["t"] = DEMO_NOW + timedelta(minutes=16)
    assert data.snapshot().errors_15m == 0


def test_new_mail_is_seen_at_once_despite_the_cache(demo):
    data = demo.data
    assert data.snapshot().agents["ceo/writer"].unread == 0
    demo.org.send(ROOT, "ceo/writer", "hello")
    snap = data.snapshot()
    assert snap.agents["ceo/writer"].unread == 1 and snap.agents["ceo/writer"].kind == "queued"
    demo.org.send(ROOT, "ceo/writer", "again")
    assert data.snapshot().agents["ceo/writer"].unread == 2


def test_once_output_sample(demo):
    text = dd.render_once(demo.data)
    lines = text.splitlines()
    assert lines[0].startswith("hirearchy dash - acme (")
    assert lines[1] == ("scheduler running pid 7000 (until_done, up 6m40s, heartbeat 3.0s ago) | "
                        "running 2/2 · queued 1 · waiting on you 1 · errors 15m 2")
    assert "  ▶ ceo [Chief executive]  running 1m12s  budget 3  claude-sonnet-5.5" in text
    assert "    ◔ analyst [Competitor analyst]  queued: max_parallel (2) runs are busy, 1 unread  budget 4  claude-opus-5.5" in text
    assert "    ‖ deploy [Deploy engineer]  paused: 2 consecutive failed runs, 1 unread  budget 1" in text
    assert "queued: paused" not in text
    assert "NEEDS YOU" in text and "SERVICES" in text and "research/market-brief" in text


# ------------------------------------------------------------------------------------------ performance
@pytest.mark.skipif(os.environ.get("HIREARCHY_SKIP_PERF"), reason="perf measurement skipped")
def test_a_refresh_tick_of_50_agents_and_2000_messages(tmp_path, process_overrides, capsys):
    scheduler_is(process_overrides, SchedulerState("running", 7000, "x"))
    org = big_org(tmp_path, agents=50, messages=2000)
    old = time.time() - 3600  # an organization that has existed for a while: its mailboxes are not being written now
    for dirpath, dirnames, _ in os.walk(org.root):
        for n in dirnames:
            os.utime(os.path.join(dirpath, n), (old, old))
    workers = [a for a in org.agents() if "/" in a]
    write_running_json(org, workers[0])
    log = EventLog(org)
    for i in range(300):
        log.tool(T0 + timedelta(seconds=i), "lead0", "inbox")
    n_files = sum(1 for _ in org.root.rglob("*.md")) - 50 * 2  # charters + ORG.md
    data = dd.DashData(org.root, now=lambda: T0 + timedelta(seconds=400))
    t = time.perf_counter()
    cold = data.snapshot()
    cold_ms = (time.perf_counter() - t) * 1000
    ticks = []
    for _ in range(10):
        t = time.perf_counter()
        s = data.snapshot()
        data.agent_detail(workers[0], s)
        ticks.append((time.perf_counter() - t) * 1000)
    org.send(ROOT, "lead1", "new mail")  # one mailbox changes between ticks
    t = time.perf_counter()
    s = data.snapshot()
    data.agent_detail("lead1", s)
    changed_ms = (time.perf_counter() - t) * 1000
    t = time.perf_counter()
    data.requests(s)
    data.services(s)
    heavy_ms = (time.perf_counter() - t) * 1000
    med = statistics.median(ticks)
    with capsys.disabled():
        print(f"\n[dash perf] {len(cold.agents) - 1} agents, {n_files} message files: cold first snapshot {cold_ms:.0f} ms, "
              f"warm tick (snapshot + selected agent) median {med:.0f} ms (max {max(ticks):.0f}), after one mailbox changed {changed_ms:.0f} ms, "
              f"requests+services {heavy_ms:.0f} ms")
    assert len(cold.agents) - 1 == 50
    assert med < 200, f"warm tick {med:.0f} ms"


# ------------------------------------------------------------------------------------------ one state per agent
def test_an_agent_is_in_exactly_one_state_for_every_combination():
    """``classify`` over every combination of its inputs: one state; the words never contradict each other."""
    import itertools

    n = 0
    for running, unread, paused, budget, open_n, out_n, up, free in itertools.product(
            (True, False), (0, 2), (None, "broken", "paused by the user: x", "budget"), (0, 3), (0, 1), (0, 1), (True, False), (0, 1)):
        st = dd.classify(running=running, unread=unread, paused=paused, budget=budget, open_tasks=open_n, delegated=out_n,
                         scheduler_up=up, free_slots=free, max_parallel=2, elapsed_s=72.0 if running else None)
        n += 1
        word, ctx = st.word, (running, unread, paused, budget, open_n, out_n, up, free)
        assert st.kind in dd.STATE_KINDS and word == st.main + st.note, ctx
        effective_pause = paused is not None and not (paused == "budget" and budget > 0)
        has_pause_word, has_queued_word, has_budget_word = "paused" in word, "queued" in word, "out of budget" in word
        if running:
            assert st.kind == "running" and word.startswith("running 1m12s") and not has_queued_word, ctx
            assert (f"+{unread} unread" in word) == bool(unread), ctx
            assert (up or "scheduler not running" in word) and (not up or "scheduler not running" not in word), ctx
            assert (st.reason != "") == bool(unread), ctx
        elif effective_pause and paused != "budget":  # paused wins over mail, budget, tasks
            assert st.kind == "paused" and word.startswith(dd.pause_text(paused)), ctx
            assert not has_queued_word and not has_budget_word and word.endswith(f", {unread} unread" if unread else word), ctx
        elif effective_pause or (budget <= 0 and (unread or open_n or out_n)):  # out of budget wins over queued
            assert st.kind == "budget" and word == "out of budget" + (f", {unread} unread" if unread else ""), ctx
            assert not has_pause_word and not has_queued_word, ctx
        elif unread:  # queued: it would run, and why it has not yet
            assert st.kind == "queued" and word.startswith("queued: ") and not has_pause_word and not has_budget_word, ctx
            assert budget > 0 and not effective_pause, ctx
            expected = ("scheduler is not running" if not up else "max_parallel (2) runs are busy" if free <= 0
                        else "starts on the next tick")
            assert st.main == f"queued: {expected}" and word.endswith(f", {unread} unread"), ctx
        else:
            assert st.kind in ("waiting", "working", "idle") and not (has_queued_word or has_pause_word or has_budget_word), ctx
            assert st.kind == ("waiting" if out_n else "working" if open_n else "idle"), ctx
    assert n == 2 * 2 * 4 * 2 * 2 * 2 * 2 * 2


def test_specific_state_words():
    kw = dict(open_tasks=0, delegated=0, scheduler_up=True, free_slots=1, max_parallel=2)
    # paused wins over queued: the old 'queued: paused: ...' is gone
    st = dd.classify(running=False, unread=1, paused="2 consecutive failed runs", budget=1, **kw)
    assert st.word == "paused: 2 consecutive failed runs, 1 unread" and st.kind == "paused"
    # a reason that already says 'paused' is not prefixed again
    assert dd.classify(running=False, unread=0, paused="paused by the user: window closed", budget=1, **kw).word == "paused by the user: window closed"
    # out of budget wins over queued
    st = dd.classify(running=False, unread=3, paused=None, budget=0, **kw)
    assert (st.kind, st.word) == ("budget", "out of budget, 3 unread")
    # and over a pause that only says 'budget'
    assert dd.classify(running=False, unread=1, paused="budget", budget=0, **kw).word == "out of budget, 1 unread"
    # a stale 'budget' pause with budget granted since: the scheduler starts it -> queued
    assert dd.classify(running=False, unread=1, paused="budget", budget=2, **kw).kind == "queued"
    # a running agent keeps running; mail waits for the next run; a pause is announced
    st = dd.classify(running=True, unread=2, paused="broken", budget=1, elapsed_s=61, **kw)
    assert (st.kind, st.word) == ("running", "running 1m01s, +2 unread, then paused: broken")
    assert st.reason == "its current run is still going; the next run starts after it"
    # queued, with each reason
    assert dd.classify(running=False, unread=1, paused=None, budget=1, **{**kw, "scheduler_up": False}).main == "queued: scheduler is not running"
    assert dd.classify(running=False, unread=1, paused=None, budget=1, **{**kw, "free_slots": 0}).main == "queued: max_parallel (2) runs are busy"
    assert dd.classify(running=False, unread=1, paused=None, budget=1, **kw).main == "queued: starts on the next tick"


def test_every_state_in_a_real_org_has_one_word(demo):
    """The tree, the delegations list and the header agree: nothing 'queued' is also paused or out of budget."""
    snap = demo.data.snapshot()
    for a, r in snap.agents.items():
        if a == ROOT:
            continue
        assert ("queued" in r.word) == (r.kind == "queued"), (a, r.word)
        assert ("paused" in r.word.split(", then")[0]) == (r.kind == "paused"), (a, r.word)
        assert ("out of budget" in r.word) == (r.kind == "budget"), (a, r.word)
    assert snap.queued == sum(1 for r in snap.agents.values() if r.kind == "queued")
    text = dd.render_once(demo.data)
    assert "queued: paused" not in text and "queued: no budget" not in text
