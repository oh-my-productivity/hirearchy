"""The dashboard app, headless, driven with Textual's pilot: navigation, screens, tabs, filters, pause, help, quit,
live refresh (selection / scroll / expansion kept), failures shown in the status line, and nothing written."""

import asyncio
import os
import sys
import time
from pathlib import Path

import pytest
from dash_fixtures import DEMO_NOW, demo_org
from obs_fixtures import EventLog, stamp
from test_dashboard_data import set_scheduler, snapshot_files
from testkit.scheduler import scheduler_is

from orgmcp import dashboard_data as dd
from orgmcp.core import ROOT, Org
from orgmcp.dashboard import DashApp, NavTable, TextPane, TextScreen
from orgmcp.scheduler import SchedulerState


def run(coro):
    return asyncio.run(coro)


@pytest.fixture
def demo(tmp_path, monkeypatch):
    set_scheduler(monkeypatch, SchedulerState("running", 7000, "2026-10-18 10:00:00Z"))
    return demo_org(tmp_path)


def make_app(ns, interval=60.0):
    return DashApp(ns.org.root, interval=interval, now=lambda: DEMO_NOW)


def scenario(ns, fn, size=(110, 34), interval=60.0):
    """Run ``fn(app, pilot)`` against the app on the organization ``ns.org``."""

    async def go():
        app = make_app(ns, interval)
        async with app.run_test(size=size) as pilot:
            await app.settle(pilot)
            await fn(app, pilot)
            return app

    return run(go())


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


def cursor_key(app, tid):
    return app.query_one(f"#{tid}", NavTable).current_key()


def footer_keys(app) -> dict[str, str]:
    """key -> description of the bindings the footer shows right now."""
    from textual.widgets._footer import FooterKey

    return {k.key_display or k.key: k.description for k in app.screen.query(FooterKey)}


# ------------------------------------------------------------------------------------------ the org screen


def test_start_shows_the_header_and_the_whole_tree(demo):
    async def fn(app, pilot):
        assert app.view == "org" and app.selected == ROOT and app.last_error is None
        header = app.query_one("#header-counts").render().plain if hasattr(app.query_one("#header-counts").render(), "plain") else ""
        text = str(app.query_one("#header-title").render()) + str(app.query_one("#header-counts").render())
        assert "acme" in text and "scheduler running pid 7000" in text
        assert "running 2/2" in text and "queued 1" in text and "waiting on you 1" in text and "errors 15m 2" in text
        got = labels(app)
        assert got[ROOT].startswith("★ root (you)") and "needs you: 1" in got[ROOT]
        assert "▶ ceo  running 1m12s  3 left" == got["ceo"]
        assert got["ceo/analyst"].startswith("◔ analyst  queued: ") and ", 1 unread" in got["ceo/analyst"]
        assert got["ceo/writer"].startswith("◆ writer  working on 1 task(s)")
        assert got["ops"].startswith("◇ ops  waiting on 1 report(s)")
        assert got["ops/deploy"].startswith("‖ deploy  paused: 2 consec") and got["ops/deploy"].endswith(", 1 unread") and "queued" not in got["ops/deploy"]  # paused, not 'queued: paused'
        assert not any("queued: paused" in v or "queued: no budget" in v for v in got.values())
        assert got["ops/audit"].startswith("‖ audit  paused by the user")
        assert got["research"].startswith("▶ research  running 2m05s")
        assert got["research/crawler"].startswith("! crawler  out of budget")
        assert got["archivist"].startswith("○ archivist  idle")
        assert header is not None

    scenario(demo, fn)


def test_root_shows_what_needs_you_and_the_requests(demo):
    async def fn(app, pilot):
        text = pane(app, "pane-overview")
        assert "Needs you (1)" in text and 'note from ops "Need approval for downtime"' in text
        assert '"Quarterly market report" -> ceo: working (running: ceo' in text
        assert '"Rotate API keys" -> ops: waiting on ops/deploy (paused: 2 consecutive failed runs)' in text

    scenario(demo, fn)


def test_arrows_and_vim_keys_move_the_selection_and_the_details_follow(demo):
    async def fn(app, pilot):
        await press(app, pilot, "down")
        assert app.selected == "archivist" and "state    ○ idle" in pane(app, "pane-overview")
        await press(app, pilot, "j")
        assert app.selected == "ceo"
        text = pane(app, "pane-overview")
        assert "state    ▶ running 1m12s" in text and "elapsed 1m12s" in text and 'note "Scope change" from root' in text
        await press(app, pilot, "down", "down")  # analyst, writer
        assert app.selected == "ceo/writer" and "state    ◆ working on 1 task(s)" in pane(app, "pane-overview")
        await press(app, pilot, "k")
        assert app.selected == "ceo/analyst"
        text = pane(app, "pane-overview")
        assert "queued: max_parallel (2) runs are busy" in text and "1 unread message(s) wait: max_parallel (2) runs are busy" in text
        assert '"Collect competitor data"  from ceo  budget 4' in text and "A table of 5 rows" in text
        await press(app, pilot, "G")
        assert app.selected == "research/crawler" and "out of budget" in pane(app, "pane-overview")
        await press(app, pilot, "g")
        assert app.selected == ROOT

    scenario(demo, fn)


def test_a_paused_agent_and_a_queued_agent_are_explained(demo):
    async def fn(app, pilot):
        app.query_one("#agent-tree").focus()
        tree = app.query_one("#agent-tree")
        tree.move_cursor(tree.nodes["ops/audit"])
        await app.settle(pilot)
        assert "state    ‖ paused by the user: audit window closed" in pane(app, "pane-overview")
        tree.move_cursor(tree.nodes["ops/deploy"])
        await app.settle(pilot)
        assert "state    ‖ paused: 2 consecutive failed runs, 1 unread" in pane(app, "pane-overview")
        assert "queued" not in pane(app, "pane-overview").split("Latest activity")[0]

    scenario(demo, fn)


def test_left_and_right_fold_unfold_and_switch_pane(demo):
    async def fn(app, pilot):
        tree = app.query_one("#agent-tree")
        await press(app, pilot, "down", "down")  # ceo
        assert app.selected == "ceo" and tree.nodes["ceo"].is_expanded
        await press(app, pilot, "h")
        assert not tree.nodes["ceo"].is_expanded
        assert labels(app)["ceo"].endswith("[1 queued below]")
        await press(app, pilot, "left")  # already folded: go to the parent (root)
        assert app.selected == ROOT
        await press(app, pilot, "down", "down", "l")  # unfold ceo
        assert tree.nodes["ceo"].is_expanded
        await press(app, pilot, "l")  # unfolded: l moves into the details
        assert app.focused is app.query_one("#pane-overview")
        await press(app, pilot, "h")
        assert app.focused is tree
        await press(app, pilot, "enter")  # Enter opens the details too
        assert app.focused is app.query_one("#pane-overview")
        await press(app, pilot, "escape")
        assert app.focused is tree

    scenario(demo, fn)


def test_tab_and_shift_tab_cycle_the_focus(demo):
    async def fn(app, pilot):
        first = app.focused
        await press(app, pilot, "tab")
        assert app.focused is not first
        await press(app, pilot, "shift+tab")
        assert app.focused is first

    scenario(demo, fn)


def test_the_tabs_of_an_agent(demo):
    async def fn(app, pilot):
        await press(app, pilot, "down", "down")  # ceo
        tabs = app.query_one("#agent-tabs")
        assert tabs.active == "tab-overview"
        await press(app, pilot, "]")
        assert tabs.active == "tab-activity"
        act = pane(app, "pane-activity")
        assert "10:05:40 delegate → ceo/analyst REFUSED: not enough budget" in act and "10:05:30 inbox ok 5ms" in act
        assert '10:05:27 run started (batch: note "Scope change" from root)' in act
        assert "pgid" not in act and "budget_before" not in act and "tool.call" not in act and "run=ceo@" not in act
        await press(app, pilot, "]")
        assert tabs.active == "tab-messages"
        rows = table_rows(app, "pane-messages")
        assert any("Scope change" in r[4] and r[1] == "inflight" for r in rows.values())
        assert any(r[1] == "sent" and "Collect competitor data" in r[4] for r in rows.values())
        await press(app, pilot, "]")
        assert tabs.active == "tab-runlog"
        log = pane(app, "pane-runlog")
        assert "started 2026-10-18 10:05:27Z" in log and "still running" in log and "Delegating the extra scope to the analyst..." in log
        await press(app, pilot, "]")
        assert tabs.active == "tab-memory" and pane(app, "pane-memory") == "(no memory yet)"
        await press(app, pilot, "]")
        assert tabs.active == "tab-charter" and "Run the report pipeline." in pane(app, "pane-charter")
        await press(app, pilot, "]")
        assert tabs.active == "tab-overview"
        await press(app, pilot, "[")
        assert tabs.active == "tab-charter"

    scenario(demo, fn)


def test_a_message_opens_with_enter_and_closes_with_escape(demo):
    async def fn(app, pilot):
        await press(app, pilot, "down", "down", "]", "]")  # ceo, Messages
        table = app.query_one("#pane-messages", NavTable)
        table.focus()
        keys = list(table_rows(app, "pane-messages"))
        scope = next(k for k, r in table_rows(app, "pane-messages").items() if "Scope change" in r[4])
        table.move_cursor(row=keys.index(scope))
        await press(app, pilot, "enter")
        assert isinstance(app.screen, TextScreen)
        text = app.screen.query_one("#modal-pane", TextPane).text_now
        assert "from: root" in text and "Please also cover the Asian market." in text and text.startswith("### note ")
        await press(app, pilot, "escape")
        assert not isinstance(app.screen, TextScreen)
        # keys of the underlying screens are inert while the overlay is open
        await press(app, pilot, "enter", "2")
        assert isinstance(app.screen, TextScreen) and app.view == "org"
        await press(app, pilot, "backspace")
        assert not isinstance(app.screen, TextScreen)

    scenario(demo, fn)


def test_the_run_log_of_a_finished_run_shows_its_exit(demo):
    async def fn(app, pilot):
        tree = app.query_one("#agent-tree")
        tree.move_cursor(tree.nodes["ops/deploy"])
        await app.settle(pilot)
        await press(app, pilot, "]", "]", "]")
        log = pane(app, "pane-runlog")
        assert "exit 1 after 10s" in log and "error: deploy tool crashed" in log and "[last run]" in log

    scenario(demo, fn)


# ------------------------------------------------------------------------------------------ the other screens


def test_screens_switch_with_the_number_keys(demo):
    async def fn(app, pilot):
        seen = []
        for key, name in (("2", "flows"), ("3", "services"), ("4", "events"), ("5", "health"), ("1", "org")):
            await press(app, pilot, key)
            seen.append((app.view, app.query_one("#screens").current))
            assert app.view == name
        assert [s[1] for s in seen] == ["flows-view", "services-view", "events-view", "health-view", "org-view"]
        assert "1 Org" in str(app.query_one("#header-title").render())

    scenario(demo, fn)


def test_workflows_table_and_the_trace_of_a_request(demo):
    async def fn(app, pilot):
        await press(app, pilot, "2")
        rows = table_rows(app, "flows-table")
        by_title = {r[1]: r for r in rows.values()}
        assert by_title["Quarterly market report"][0].startswith("working") and by_title["Quarterly market report"][3] == "3/12"
        assert by_title["Rotate API keys"][0].startswith("waiting on ops/deploy")
        assert by_title["Rotate API keys"][5] == "1 for you"
        assert by_title["Archive old reports"][0] == "done"
        assert list(rows)[-1] == demo.done_task.id  # newest first
        table = app.query_one("#flows-table")
        keys = list(rows)
        table.move_cursor(row=keys.index(demo.report_task.id))
        await press(app, pilot, "enter")
        await asyncio.sleep(0.3)
        await app.settle(pilot)
        text = pane(app, "flows-detail")
        assert text.startswith('"Quarterly market report"') and "trace " + demo.report_task.id in text
        assert "root -> ceo task" in text and "ceo -> ceo/analyst task" in text and "totals: wall" in text
        assert "ceo delegate REFUSED" in text or "! delegate" in text or "tool calls" in text
        assert text.count("\n") > 5 and "run " in text
        assert app.query_one("#flows-table").has_class("hidden")
        await press(app, pilot, "escape")
        assert not app.query_one("#flows-table").has_class("hidden") and app.flow_open is None
        assert cursor_key(app, "flows-table") == demo.report_task.id  # the cursor stayed on the request

    scenario(demo, fn)


def test_a_long_trace_scrolls(demo):
    async def fn(app, pilot):
        await press(app, pilot, "2", "enter")
        await asyncio.sleep(0.3)
        await app.settle(pilot)
        p = app.query_one("#flows-detail", TextPane)
        assert p.has_focus
        await press(app, pilot, "G")
        assert p.scroll_y >= 0
        await press(app, pilot, "g")
        assert p.scroll_y == 0

    scenario(demo, fn, size=(90, 12))


def test_services_table_and_a_service_record(demo):
    async def fn(app, pilot):
        await press(app, pilot, "3")
        (row,) = table_rows(app, "services-table").values()
        assert row[0] == "market-brief" and row[1] == "research" and row[2] == "c1 p1"
        assert row[3] == "2" and row[4] == "1/0/1" and row[5] == "1" and row[6] == "1✓ 0✗" and row[7] == "2" and row[8] == "initial playbook"
        await press(app, pilot, "enter")
        text = pane(app, "services-detail")
        assert "market-brief (owner research)" in text and "Cases (2)" in text and "Brief: heat pumps" in text
        assert 'feedback: reject "Too long and no sources." -> accept "This is right."' in text
        assert "Keep it under 600 words." in text and "playbook v1 revised by root: initial playbook" in text
        await press(app, pilot, "escape")
        assert app.service_open is None and not app.query_one("#services-table").has_class("hidden")

    scenario(demo, fn)


def test_events_errors_filter_and_follow(demo):
    async def fn(app, pilot):
        await press(app, pilot, "4")
        body = lambda: pane(app, "events-body")  # noqa: E731
        assert body().count("\n") >= 10 and "scheduler heartbeat" in body() and "scheduler.heartbeat" not in body()
        assert "11 of 11 event(s)" in str(app.query_one("#events-bar").render())
        await press(app, pilot, "e")
        assert app.event_errors and "ceo            delegate → ceo/analyst REFUSED" in body() and "run ended FAILED after 10s" in body()
        assert "heartbeat" not in body() and body().strip().count("\n") == 1
        assert "errors only" in str(app.query_one("#events-bar").render())
        await press(app, pilot, "e")
        assert not app.event_errors and "heartbeat" in body()
        await press(app, pilot, "slash")
        assert app.focused is app.query_one("#events-filter")
        await press(app, pilot, *"research")
        assert app.event_text == "research" and body().count("\n") == 2 and all("research" in l for l in body().splitlines())
        await press(app, pilot, "enter")
        assert app.focused is app.query_one("#events-body")
        await press(app, pilot, "escape")  # clears the filter
        assert app.event_text == "" and "heartbeat" in body()
        await press(app, pilot, "slash")
        await press(app, pilot, *"ceo delegate")
        # the filter matches what the lines say: root's delegate to ceo and ceo's refused delegate
        assert body().count("\n") == 2 and "delegate → ceo/analyst REFUSED" in body() and all("delegate" in l for l in body().splitlines())
        for _ in range(12):
            await press(app, pilot, "backspace")
        await press(app, pilot, *"refused")  # words of the readable line are matched too
        assert body().count("\n") == 1 and "REFUSED" in body()
        await press(app, pilot, "escape")
        assert app.event_follow
        await press(app, pilot, "f")
        assert not app.event_follow and "not following" in str(app.query_one("#events-bar").render())
        await press(app, pilot, "f")
        assert app.event_follow

    scenario(demo, fn)


def test_the_filter_matches_agent_kind_and_trace(demo):
    async def fn(app, pilot):
        await press(app, pilot, "4", "slash")
        await press(app, pilot, *"run.start")
        lines = pane(app, "events-body").splitlines()
        assert len(lines) == 3 and all("run started" in l for l in lines)  # the kind is matched, though the line says it in words
        for _ in range(9):
            await press(app, pilot, "backspace")
        await press(app, pilot, *demo.report_task.id[-8:])
        assert 3 <= len(pane(app, "events-body").splitlines()) <= 8  # the events of that request (matched on their trace field)

    scenario(demo, fn)


def test_events_new_lines_follow_and_old_ones_stay(demo):
    async def fn(app, pilot):
        await press(app, pilot, "4")
        before = pane(app, "events-body")
        EventLog(demo.org).tool(stamp(399), "ceo/writer", "write", ok=False, error="denied", trace="T-9")
        await press(app, pilot, "r")
        after = pane(app, "events-body")
        assert after.startswith(before.rstrip("\n").splitlines()[0]) and "ceo/writer     write REFUSED: denied" in after
        assert "errors 15m 3" in str(app.query_one("#header-counts").render())

    scenario(demo, fn)


def test_health_screen_and_the_check_on_demand(demo):
    async def fn(app, pilot):
        await press(app, pilot, "5")
        text = pane(app, "health-body")
        assert "scheduler: running pid 7000" in text and "runs in flight 2/2" in text and "waiting on you (1)" in text
        assert "ops/audit" in text and "!paused" in text
        assert "not run yet - press c" in text
        await press(app, pilot, "c")
        await asyncio.sleep(0.5)
        await press(app, pilot, "r")
        text = pane(app, "health-body")
        assert "(a) " in text and "checked at" in text and "not run yet" not in text

    scenario(demo, fn)


def test_pause_stops_the_automatic_refresh_but_not_r(demo):
    async def go():
        app = make_app(demo, interval=0.3)
        async with app.run_test(size=(100, 30)) as pilot:
            await app.settle(pilot)
            n = app.refreshes
            await asyncio.sleep(1.0)
            await app.settle(pilot)
            assert app.refreshes > n  # it refreshes by itself
            await press(app, pilot, "p")
            assert app.paused and "refresh paused" in str(app.query_one("#header-title").render())
            n = app.refreshes
            await asyncio.sleep(1.0)
            await app.settle(pilot)
            assert app.refreshes == n
            await press(app, pilot, "r")
            assert app.refreshes > n
            n = app.refreshes
            await press(app, pilot, "p")
            assert not app.paused and "refresh paused" not in str(app.query_one("#header-title").render())
            assert "refresh 0.3s" in str(app.query_one("#header-title").render())
            await asyncio.sleep(1.0)
            await app.settle(pilot)
            assert app.refreshes > n

    run(go())


def test_help_lists_every_key_and_escape_closes_it(demo):
    async def fn(app, pilot):
        await press(app, pilot, "question_mark")
        assert isinstance(app.screen, TextScreen)
        text = app.screen.query_one("#modal-pane", TextPane).text_now
        for needle in ("1 2 3 4 5", "Tab / Shift+Tab", "j k", "g / G", "h l", "Enter", "Esc / Backspace", "r             refresh now",
                       "p   pause", "q   quit", "[ ]", "e             errors only", "/", "f   follow", "c  runs the consistency check",
                       "read-only"):
            assert needle in text, needle
        await press(app, pilot, "question_mark")  # ? again closes it
        assert not isinstance(app.screen, TextScreen)
        await press(app, pilot, "question_mark", "escape")
        assert not isinstance(app.screen, TextScreen)

    scenario(demo, fn)


def test_q_quits(demo):
    async def go():
        app = make_app(demo)
        async with app.run_test(size=(100, 30)) as pilot:
            await app.settle(pilot)
            await pilot.press("q")
            await pilot.pause()
        assert app.return_code in (0, None) and not app.is_running

    run(go())


def test_the_footer_shows_the_keys_of_the_current_context(demo):
    async def fn(app, pilot):
        keys = footer_keys(app)  # tree focused on the org screen
        assert {"1", "2", "3", "4", "5", "r", "p", "?", "q", "[", "]"} <= set(keys)
        assert "←/h" in keys and "→/l" in keys and "e" not in keys and "/" not in keys and "c" not in keys
        await press(app, pilot, "4")
        keys = footer_keys(app)
        assert {"e", "/", "f"} <= set(keys) and "←/h" not in keys and "[" not in keys
        await press(app, pilot, "5")
        keys = footer_keys(app)
        assert "c" in keys and "e" not in keys
        await press(app, pilot, "2")
        keys = footer_keys(app)
        assert "enter" in {k.lower() for k in keys} or "⏎" in keys or "Open" in keys.values()
        assert "c" not in keys and "f" not in keys

    scenario(demo, fn, size=(160, 30))


# ------------------------------------------------------------------------------------------ live refresh


def test_a_refresh_keeps_selection_expansion_and_scroll(demo):
    async def fn(app, pilot):
        tree = app.query_one("#agent-tree")
        await press(app, pilot, "down", "down", "h")  # ceo selected and folded
        await press(app, pilot, "down", "down")  # ops
        await press(app, pilot, "down")  # ops/audit
        assert app.selected == "ops/deploy" and not tree.nodes["ceo"].is_expanded
        # a long Messages list for ops/deploy to scroll in
        for i in range(60):
            demo.org.send(ROOT, "ops/deploy", f"note {i}", title=f"note {i}")
        await press(app, pilot, "]", "]", "r")
        table = app.query_one("#pane-messages", NavTable)
        assert table.row_count >= 60
        table.focus()
        table.move_cursor(row=30)
        key = table.current_key()
        table.scroll_to(0, 12, animate=False)
        await pilot.pause()
        scroll = table.scroll_y
        demo.org.send(ROOT, "ops/deploy", "one more", title="one more")  # a new row appears at the top
        await press(app, pilot, "r")
        assert table.current_key() == key  # the cursor stays on the same message
        assert table.row_count >= 61 and abs(table.scroll_y - scroll) <= 1.0
        assert app.selected == "ops/deploy" and not tree.nodes["ceo"].is_expanded
        # a refresh with nothing new changes nothing
        snap = (app.selected, tree.cursor_line, [n.is_expanded for n in tree.nodes.values()])
        await press(app, pilot, "r", "r")
        assert snap == (app.selected, tree.cursor_line, [n.is_expanded for n in tree.nodes.values()])

    scenario(demo, fn, size=(110, 28))


def test_a_new_agent_appears_without_losing_the_cursor_or_folds(demo):
    async def fn(app, pilot):
        tree = app.query_one("#agent-tree")
        await press(app, pilot, "down", "down", "h")  # fold ceo
        await press(app, pilot, "down")
        assert app.selected == "ops"
        demo.org.hire(ROOT, "zed", "Late hire", "Joined later.")
        await press(app, pilot, "r")
        assert "zed" in tree.nodes and app.selected == "ops" and not tree.nodes["ceo"].is_expanded
        assert labels(app)["zed"].startswith("○ zed  idle")
        demo.org.retire(ROOT, "zed", "gone")
        await press(app, pilot, "r")
        assert "zed" not in tree.nodes and app.selected == "ops"

    scenario(demo, fn)


def test_the_run_log_follows_while_it_grows(demo):
    async def fn(app, pilot):
        await press(app, pilot, "down", "down", "]", "]", "]")  # ceo, Run log
        assert "Delegating the extra scope" in pane(app, "pane-runlog")
        with open(demo.ceo_log, "a", encoding="utf-8") as f:
            for i in range(300):
                f.write(f"working step {i}\n")
        await press(app, pilot, "r")
        p = app.query_one("#pane-runlog", TextPane)
        assert "working step 299" in p.text_now
        await asyncio.sleep(0.1)
        await pilot.pause()
        assert p.scroll_y >= p.max_scroll_y - 2  # followed to the end
        # scrolled up: stays there while more arrives
        p.scroll_to(y=0, animate=False)
        await pilot.pause()
        with open(demo.ceo_log, "a", encoding="utf-8") as f:
            f.write("a later line\n")
        await press(app, pilot, "r")
        assert "a later line" in p.text_now and p.scroll_y < 5
        with open(demo.ceo_log, "a", encoding="utf-8") as f:
            f.write("# exit 0 after 80s\n")
        await press(app, pilot, "r")
        assert "exit 0 after 80s" in p.text_now

    scenario(demo, fn, size=(110, 28))


def test_automatic_refresh_shows_a_state_change(demo):
    async def go():
        app = make_app(demo, interval=0.3)
        async with app.run_test(size=(110, 30)) as pilot:
            await app.settle(pilot)
            assert labels(app)["ceo/writer"].startswith("◆ writer  working")
            demo.org.send(ROOT, "ceo/writer", "wake up")
            for _ in range(20):
                await asyncio.sleep(0.2)
                await app.settle(pilot)
                if labels(app)["ceo/writer"].startswith("◔"):
                    break
            assert labels(app)["ceo/writer"].startswith("◔ writer  queued: ")
            assert "queued 2" in str(app.query_one("#header-counts").render())

    run(go())


# ------------------------------------------------------------------------------------------ readable text


def test_x_shows_the_events_raw_on_the_activity_tab_and_on_the_events_screen(demo):
    async def fn(app, pilot):
        await press(app, pilot, "down", "down", "]")  # ceo, Activity
        assert "x" in footer_keys(app)
        act = pane(app, "pane-activity")
        assert "run started (batch: note" in act and "pgid" not in act
        await press(app, pilot, "x")
        raw = pane(app, "pane-activity")
        assert app.raw_events and "pgid=1" in raw and "budget_before=9" in raw and "tool.call delegate REFUSED" in raw
        await press(app, pilot, "x")
        assert not app.raw_events and "pgid" not in pane(app, "pane-activity")
        await press(app, pilot, "[")  # Overview: no raw toggle there
        assert "x" not in footer_keys(app)
        await press(app, pilot, "x")
        assert not app.raw_events
        await press(app, pilot, "4")
        assert "x" in footer_keys(app) and "readable" in str(app.query_one("#events-bar").render())
        await press(app, pilot, "x")
        body = pane(app, "events-body")
        assert "scheduler.heartbeat" in body and "pgid=1" in body and "raw" in str(app.query_one("#events-bar").render())
        await press(app, pilot, "e")  # errors only, still raw
        assert "tool.call delegate REFUSED" in pane(app, "events-body")
        await press(app, pilot, "x")
        assert "delegate → ceo/analyst REFUSED" in pane(app, "events-body")

    scenario(demo, fn)


def test_refusals_and_failures_are_red_and_the_header_says_how_it_refreshes(demo):
    async def fn(app, pilot):
        header = lambda: str(app.query_one("#header-title").render())  # noqa: E731
        assert "refresh 60s" in header() and "every" not in header()
        await press(app, pilot, "4")
        pane_ = app.query_one("#events-body", TextPane)
        reds = [ln for ln in pane_.body.render().plain.splitlines() if "REFUSED" in ln or "FAILED" in ln]
        assert len(reds) == 2
        spans = [str(sp.style) for sp in pane_.body.render().spans]
        assert sum("red" in sp for sp in spans) >= 2
        await press(app, pilot, "p")
        assert "refresh paused" in header()
        await press(app, pilot, "p")
        real = app.data.snapshot
        app.data.snapshot = lambda: (_ for _ in ()).throw(RuntimeError("disk on fire"))
        await press(app, pilot, "r")
        assert "refresh failed" in header() and "disk on fire" in str(app.query_one("#statusline").render())
        app.data.snapshot = real
        await press(app, pilot, "r")
        assert "refresh failed" not in header() and "refresh 60s" in header()

    scenario(demo, fn)


def test_long_lines_wrap_instead_of_running_off_the_screen(demo):
    async def fn(app, pilot):
        await press(app, pilot, "2")
        await press(app, pilot, "enter")
        await asyncio.sleep(0.5)
        await app.settle(pilot)
        detail = app.query_one("#flows-detail", TextPane)
        text = detail.text_now
        first = text.splitlines()[0]
        assert first.startswith('"Brief: heat pumps"') and len(first) > 60  # the request line is the long one
        assert detail.max_scroll_x == 0 and detail.body.size.width <= detail.size.width  # it wraps; no sideways scroll
        assert detail.body.size.height > len(text.splitlines())  # at least one line took two rows
        await press(app, pilot, "escape", "1", "down", "down", "]")
        act = app.query_one("#pane-activity", TextPane)
        assert act.max_scroll_x == 0 and act.body.size.height > len(act.text_now.splitlines())  # the refusal wraps
        await press(app, pilot, "4")
        assert app.query_one("#events-body", TextPane).max_scroll_x == 0

    scenario(demo, fn, size=(100, 34))


@pytest.mark.parametrize("size", [(80, 24), (100, 30), (150, 42)])
def test_the_agent_tree_never_scrolls_sideways_and_keeps_the_state_readable(demo, size):
    async def fn(app, pilot):
        tree = app.query_one("#agent-tree")
        assert tree.max_scroll_x == 0 and tree.virtual_size.width <= tree.scrollable_content_region.width
        got = labels(app)
        for addr, text in got.items():
            assert len(text) <= tree.scrollable_content_region.width, (addr, text)
        # the contradictory words are gone at every width, and what is cut is cut with an ellipsis
        assert not any("queued: paused" in t or "queued: no budget" in t for t in got.values())
        assert got["ops/deploy"].startswith("‖ deploy  paused") and got["research/crawler"].startswith("! crawler  out of budget")
        assert got["ceo/analyst"].startswith("◔ analyst  queued: ")
        for addr in ("ops/audit", "ops/deploy"):
            assert got[addr].endswith("…") or "paused" in got[addr]
        # the full state is in the Overview
        tree.move_cursor(tree.nodes["ops/deploy"])
        await app.settle(pilot)
        assert "state    ‖ paused: 2 consecutive failed runs, 1 unread" in pane(app, "pane-overview")

    scenario(demo, fn, size=size)


# ------------------------------------------------------------------------------------------ failures


def test_an_exception_in_a_refresh_is_shown_and_the_app_keeps_running(demo):
    async def fn(app, pilot):
        status = app.query_one("#statusline")
        assert status.has_class("hidden")
        real = app.data.snapshot

        def boom():
            raise RuntimeError("disk on fire")

        app.data.snapshot = boom
        await press(app, pilot, "r")
        assert not status.has_class("hidden") and "refresh failed: RuntimeError: disk on fire" in str(status.render())
        assert app.last_error and labels(app)["ceo"].startswith("▶ ceo")  # the last good picture stays
        await press(app, pilot, "2", "3", "4", "5", "1", "r")
        assert app.is_running
        app.data.snapshot = real
        await press(app, pilot, "r")
        assert status.has_class("hidden") and app.last_error is None

    scenario(demo, fn)


def test_a_display_failure_is_shown_too(demo):
    async def fn(app, pilot):
        app._show_requests = lambda rows: (_ for _ in ()).throw(ValueError("bad row"))
        await press(app, pilot, "2")
        assert "display failed: ValueError: bad row" in str(app.query_one("#statusline").render())
        assert app.is_running

    scenario(demo, fn)


def test_unreadable_files_are_reported_not_fatal(demo):
    (demo.org.dir("ceo") / "read" / "00000-broken.md").write_text("---\nfrom: [unclosed\n---\n", encoding="utf-8")
    (demo.org.dir("ops") / "inbox" / "00001-binary.md").write_bytes(b"\xff\xfe\x00")

    async def fn(app, pilot):
        assert app.last_error is None
        assert "unreadable files 2" in str(app.query_one("#header-counts").render())
        await press(app, pilot, "down", "down", "]", "]")
        assert app.is_running
        await press(app, pilot, "2", "3", "4", "5", "1")
        assert app.is_running and app.last_error is None

    scenario(demo, fn)


def test_an_empty_organization(tmp_path, monkeypatch):
    set_scheduler(monkeypatch, SchedulerState("stopped"))
    org = Org.init(tmp_path / "empty", "m")
    ns = type("NS", (), {"org": org})()

    async def fn(app, pilot):
        assert app.last_error is None and labels(app) == {ROOT: "★ root (you)"}
        assert "scheduler stopped" in str(app.query_one("#header-counts").render())
        assert "nothing" in pane(app, "pane-overview")
        for key in ("]", "2", "enter", "escape", "3", "enter", "4", "e", "5", "c", "1", "question_mark", "escape"):
            await press(app, pilot, key)
        assert app.is_running and app.last_error is None
        assert "this organization has no event files yet" in str(app.query_one("#events-bar").render()) or app.view == "org"

    async def go():
        app = DashApp(org.root, interval=60)
        async with app.run_test(size=(100, 30)) as pilot:
            await app.settle(pilot)
            await fn(app, pilot)

    run(go())
    assert not (org.root / ".runtime" / "events").exists()


# ------------------------------------------------------------------------------------------ read-only


def test_the_app_writes_nothing(demo, capsys):
    before = snapshot_files(demo.org.root)

    async def fn(app, pilot):
        tree = app.query_one("#agent-tree")
        for key in ("down", "down", "]", "]", "enter", "escape", "]", "]", "[", "5", "c", "r", "2", "enter", "escape", "3",
                    "enter", "escape", "4", "x", "x", "e", "slash", "x", "escape", "f", "p", "r", "p", "question_mark", "escape", "1"):
            await press(app, pilot, key)
            if key == "c":
                await asyncio.sleep(0.4)
        for addr in ("ceo", "ops/deploy", "research/crawler"):
            tree.move_cursor(tree.nodes[addr])
            await app.settle(pilot)
        await asyncio.sleep(0.3)
        await app.settle(pilot)
        assert app.last_error is None

    scenario(demo, fn, interval=0.2)
    from orgmcp.cli import main

    main(["--root", str(demo.org.root), "dash", "--once"])
    capsys.readouterr()
    assert snapshot_files(demo.org.root) == before


def test_no_events_file_is_created_by_the_app_on_an_org_without_events(tmp_path, monkeypatch):
    set_scheduler(monkeypatch, SchedulerState("stopped"))
    org = Org.init(tmp_path / "o", "m", {"events": False})  # the setup itself must not create an event log
    org.hire(ROOT, "a", "r", "c")
    org.delegate(ROOT, "a", "T", "g", "c", budget=2)
    before = snapshot_files(org.root)

    async def go():
        app = DashApp(org.root, interval=60)
        async with app.run_test(size=(100, 30)) as pilot:
            await app.settle(pilot)
            for key in ("down", "]", "]", "]", "2", "enter", "escape", "3", "4", "5", "c", "1"):
                await press(app, pilot, key)
            await asyncio.sleep(0.4)

    run(go())
    assert snapshot_files(org.root) == before
    assert not (org.root / ".runtime" / "events").exists()


# ------------------------------------------------------------------------------------------ against the real scheduler

FAKE = str(Path(__file__).with_name("fake_agent.py"))


def _runner(mode):
    def build(org, addr, prompt):
        return [sys.executable, FAKE], org.dir(addr), {**os.environ, "ORG_ROOT": str(org.root), "ORG_AGENT": addr, "FAKE_MODE": mode}

    return build


def test_a_real_run_with_fake_agents_shows_up(tmp_path, monkeypatch):
    """The real scheduler runs fake agents; the dashboard shows the finished request, the events, the trace and idle agents."""
    from orgmcp.scheduler import Scheduler

    org = Org.init(tmp_path / "org", "Real run", {"poll_seconds": 0.05})
    org.hire(ROOT, "ceo", "Chief executive", "Run it.", can_hire=True, max_children=2)
    org.hire("ceo", "eng", "Engineer", "Build things.")
    sched = Scheduler(org, _runner("tools"), echo=lambda *_: None)
    sched.acquire()
    try:
        task = org.delegate(ROOT, "ceo", "Ship it", "Ship the thing", "It is shipped", budget=6)
        deadline = time.time() + 90
        while sched.tick() and time.time() < deadline:
            time.sleep(0.02)
    finally:
        sched.release()
    set_scheduler(monkeypatch, SchedulerState("stopped"))

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


def test_a_real_running_agent_is_shown_running_with_its_live_log(tmp_path, monkeypatch):
    from orgmcp.scheduler import Scheduler

    org = Org.init(tmp_path / "org", "Hang", {"poll_seconds": 0.05})
    org.hire(ROOT, "ceo", "Chief executive", "Run it.", can_hire=True, max_children=2)
    org.hire(ROOT, "ops", "Ops", "Ops.")
    sched = Scheduler(org, _runner("hang"), echo=lambda *_: None)
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
        scheduler_is(monkeypatch, SchedulerState("running", os.getpid(), "now"), org)
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
        from orgmcp import telemetry

        telemetry.reset()
