"""The Textual app of the dashboard: the layout, the refresh machinery (one worker at a time), the screens and the keys.

It is given its queries (``DashboardQueries``) and asks them only from the worker thread, one refresh at a time: the five queries share one cache that is not
thread-safe. Read-only: it never writes inside the organization and emits no event."""

from __future__ import annotations

import time
from pathlib import Path

from rich.text import Text
from textual import on
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.pilot import Pilot
from textual.screen import ModalScreen
from textual.timer import Timer
from textual.widgets import ContentSwitcher, DataTable, Input, Static, TabbedContent, TabPane, Tree

from ..dashdata import AgentDetail, EventLine, HealthView, MsgRow, RequestRow, Section, ServiceRow, Snapshot
from ..kernel import ROOT, JsonObject, fmt_dur
from ._ports import DashboardQueries
from ._render import _hidden, doc_renderable, event_text
from ._state import HELP, TABS, VIEWS, Ctx, Tick
from ._widgets import AgentTree, ContextFooter, NavTable, StatusBar, TextPane, TextScreen


SCREENS = Binding.Group("Screen", compact=True)
TAB_KEYS = Binding.Group("Tab", compact=True)


class DashApp(App[None]):
    TITLE = "hirearchy dash"
    ENABLE_COMMAND_PALETTE = False
    CSS_PATH = Path(__file__).with_name("dashboard.tcss")
    BINDINGS = [
        Binding("1", "view('org')", "Screen", key_display="1", group=SCREENS),
        Binding("2", "view('flows')", "Screen", key_display="2", group=SCREENS),
        Binding("3", "view('services')", "Screen", key_display="3", group=SCREENS),
        Binding("4", "view('events')", "Screen", key_display="4", group=SCREENS),
        Binding("5", "view('health')", "Screen", key_display="5", group=SCREENS),
        Binding("r", "refresh", "Refresh"),
        Binding("p", "toggle_pause", "Pause"),
        Binding("escape,backspace", "back", "Back", show=False),
        Binding("question_mark", "help", "Help", key_display="?"),
        Binding("q", "quit", "Quit"),
        Binding("e", "toggle_errors", "Errors only"),
        Binding("slash", "filter", "Filter", key_display="/"),
        Binding("f", "toggle_follow", "Follow"),
        Binding("x", "toggle_raw", "Raw events"),
        Binding("c", "check", "Check"),
        Binding("h", "focus_tree", "Agents", show=False),
        Binding("left_square_bracket", "tab(-1)", "Tab", key_display="[", group=TAB_KEYS),
        Binding("right_square_bracket", "tab(1)", "Tab", key_display="]", group=TAB_KEYS),
    ]

    def __init__(self, data: DashboardQueries, interval: float = 2.0):
        super().__init__()
        self.data = data
        self.interval = max(0.2, float(interval))
        self.view = "org"
        self.selected = ROOT
        self.snap: Snapshot | None = None
        self.paused = False
        self.last_error: str | None = None
        self.last_ms = 0.0
        self.refreshes = 0
        self.flow_open: str | None = None
        self.service_open: tuple[str, str] | None = None
        self.event_text = ""
        self.event_errors = False
        self.event_follow = True
        self.raw_events = False  # x: events as the log has them (ids, pgids, budgets) instead of readable lines
        self._busy = False
        self._again = False
        self._timer: Timer | None = None
        self._msg_rows: dict[str, MsgRow] = {}
        self._req_rows: dict[str, RequestRow] = {}
        self._svc_rows: dict[str, ServiceRow] = {}
        self._check_text = ""
        self._events_total = 0
        self.detail: AgentDetail | None = None

    # ---------------------------------------------------------------- layout
    def compose(self) -> ComposeResult:
        yield StatusBar(id="header")
        with ContentSwitcher(id="screens", initial="org-view"):
            with Horizontal(id="org-view"):
                yield AgentTree(id="agent-tree")
                with TabbedContent(id="agent-tabs", initial="tab-overview"):
                    with TabPane("Overview", id="tab-overview"):
                        yield TextPane(id="pane-overview")
                    with TabPane("Activity", id="tab-activity"):
                        yield TextPane(id="pane-activity", sticky=True)
                    with TabPane("Messages", id="tab-messages"):
                        yield Static("Enter opens a message", id="msg-hint", markup=False)
                        yield NavTable(id="pane-messages")
                    with TabPane("Run log", id="tab-runlog"):
                        yield TextPane(id="pane-runlog", sticky=True)
                    with TabPane("Memory", id="tab-memory"):
                        yield TextPane(id="pane-memory")
                    with TabPane("Charter", id="tab-charter"):
                        yield TextPane(id="pane-charter")
            with Vertical(id="flows-view", classes="list-detail"):
                yield NavTable(id="flows-table")
                yield Static("", id="flows-title", classes="detail-title hidden", markup=False)
                yield _hidden(TextPane(id="flows-detail"))
            with Vertical(id="services-view", classes="list-detail"):
                yield NavTable(id="services-table")
                yield Static("", id="services-title", classes="detail-title hidden", markup=False)
                yield _hidden(TextPane(id="services-detail"))
            with Vertical(id="events-view"):
                yield Input(placeholder="filter: words that must appear in agent / kind / trace / tool  (Enter keeps it, Esc clears)",
                            id="events-filter", classes="hidden")
                yield Static("", id="events-bar", markup=False)
                yield TextPane(id="events-body", sticky=True)
            with Vertical(id="health-view"):
                yield TextPane(id="health-body")
        yield Static("", id="statusline", classes="hidden", markup=False)
        yield ContextFooter()

    def on_mount(self) -> None:
        self.query_one("#agent-tree", AgentTree).focus()
        self._timer = self.set_interval(self.interval, self.request_refresh)
        self._show_header()
        self.request_refresh()

    # ---------------------------------------------------------------- refresh machinery
    def request_refresh(self) -> None:
        """Start a refresh in a worker thread (at most one at a time; a request during one runs another right after)."""
        if self._busy:
            self._again = True
            return
        self._busy = True
        ctx = Ctx(self.view, self.selected, self.flow_open, self.service_open, self.event_text, self.event_errors, self.raw_events)
        self.run_worker(lambda: self._compute(ctx), thread=True, group="tick", exit_on_error=False)

    def _compute(self, ctx: Ctx) -> None:
        t0 = time.perf_counter()
        tick = Tick()
        try:
            d = self.data
            snap = tick.snap = d.snapshot()
            if ctx.view == "org":
                tick.detail = d.agent_detail(ctx.selected if ctx.selected in snap.agents else ROOT, snap, raw=ctx.raw)
            elif ctx.view == "flows":
                tick.requests = d.requests(snap)
            elif ctx.view == "services":
                tick.services = d.services(snap)
                if ctx.service_open:
                    tick.service_doc = d.service_detail(*ctx.service_open)
            elif ctx.view == "events":
                tick.events = d.feed.matching(ctx.event_text, ctx.event_errors, limit=1500) if d.feed else []
                tick.event_lines = d.event_lines(tick.events, actor=True, raw=ctx.raw)
            elif ctx.view == "health":
                tick.health = d.health(snap)
        except Exception as exc:  # noqa: BLE001 - shown in the status line; the app keeps running
            tick.error = f"refresh failed: {type(exc).__name__}: {exc}"
        tick.ms = (time.perf_counter() - t0) * 1000
        try:
            self.call_from_thread(self._apply, tick)
        except Exception:  # noqa: BLE001 - the app is closing
            self._busy = False

    def _apply(self, tick: Tick) -> None:
        self._busy = False
        self.refreshes += 1
        self.last_ms = tick.ms
        try:
            if tick.error:
                self._status(tick.error)
            else:
                self._status(None)
            if tick.snap is not None:
                self.snap = tick.snap
                tree = self.query_one("#agent-tree", AgentTree)
                tree.sync(tick.snap)
                cursor = tree.cursor_node
                if self.selected not in tick.snap.agents and cursor is not None:  # the selected agent is gone
                    self.selected = cursor.data or ROOT
                self._show_header()
            if tick.detail is not None:
                self._show_detail(tick.detail)
            if tick.requests is not None:
                self._show_requests(tick.requests)
            if tick.services is not None:
                self._show_services(tick.services, tick.service_doc)
            if tick.events is not None:
                self._show_events(tick.events, tick.event_lines or [])
            if tick.health is not None:
                self._show_health(tick.health)
        except Exception as exc:  # noqa: BLE001 - a display bug must not stop the dashboard
            self._status(f"display failed: {type(exc).__name__}: {exc}")
        if self._again:
            self._again = False
            self.request_refresh()

    def _status(self, text: str | None) -> None:
        self.last_error = text
        line = self.query_one("#statusline", Static)
        if text:
            line.update(Text(text, style="bold"))
            line.remove_class("hidden")
        else:
            line.add_class("hidden")
        self._show_header()

    def _show_header(self) -> None:
        self.query_one("#header", StatusBar).show(self.snap, self.view, self.paused, self.interval, self.last_error)

    async def settle(self, pilot: Pilot[None] | None = None) -> None:
        """Wait until no refresh is running and everything it produced is on the screen (for tests and scripts)."""
        import asyncio

        for _ in range(200):
            await self.workers.wait_for_complete()  # a worker returns only after its call_from_thread callback ran
            await asyncio.sleep(0)
            if pilot is not None:
                await pilot.pause()
            if not self._busy and not self._again:
                return

    # ---------------------------------------------------------------- org view
    @on(Tree.NodeHighlighted, "#agent-tree")
    def _highlighted(self, event: Tree.NodeHighlighted[str]) -> None:
        tree = self.query_one("#agent-tree", AgentTree)
        if tree.quiet:
            return
        addr = event.node.data or ROOT
        if addr != self.selected:
            self.selected = addr
            self.request_refresh()

    @on(Tree.NodeSelected, "#agent-tree")
    def _selected(self, event: Tree.NodeSelected[str]) -> None:
        self.action_pane()

    def action_pane(self) -> None:
        """Move the focus from the tree into the details of the selected agent."""
        tabs = self.query_one("#agent-tabs", TabbedContent)
        active = (tabs.active or "tab-overview").removeprefix("tab-")
        target = self.query_one(f"#pane-{active}")
        target.focus()

    def action_focus_tree(self) -> None:
        if self.view == "org":
            self.query_one("#agent-tree").focus()

    def _active_tab(self) -> str:
        try:
            return (self.query_one("#agent-tabs", TabbedContent).active or "tab-overview").removeprefix("tab-")
        except Exception:  # noqa: BLE001
            return "overview"

    def action_tab(self, step: int) -> None:
        if self.view != "org":
            return
        tabs = self.query_one("#agent-tabs", TabbedContent)
        names = [f"tab-{t}" for t in TABS]
        i = names.index(tabs.active) if tabs.active in names else 0
        tabs.active = names[(i + int(step)) % len(names)]

    def _show_detail(self, d: AgentDetail) -> None:
        if d.addr != self.selected and self.selected in (self.snap.agents if self.snap else {}):
            return  # the selection moved on while this was computed; the next refresh brings the right one
        self.detail = d
        self._show_tab(self.query_one("#agent-tabs", TabbedContent).active)

    @on(TabbedContent.TabActivated, "#agent-tabs")
    def _tab_activated(self, event: TabbedContent.TabActivated) -> None:
        self._show_tab(event.pane.id or "")
        self.refresh_bindings()

    def _show_tab(self, tab_id: str) -> None:
        """Fill the visible tab only (the others are filled when they are opened)."""
        d = self.detail
        if d is None:
            return
        subject = d.addr
        name = (tab_id or "tab-overview").removeprefix("tab-")
        if name == "overview":
            text = doc_renderable(d.overview)
            self.query_one("#pane-overview", TextPane).set_content(text, key=text.plain, subject=subject)
        elif name == "activity":
            last = d.events[-1].get("seq") if d.events else None
            hint = "raw events (x: readable)" if self.raw_events else "x: raw events (ids, budgets, arguments)"
            body = Text(hint + "\n", style="dim")
            if d.events:
                body.append_text(event_text(d.activity))
            self.query_one("#pane-activity", TextPane).set_content(
                body if d.events else Text("(no events for this agent yet)", style="dim"),
                key=(len(d.events), last, d.events[-1].get("ts") if d.events else None, self.raw_events), subject=subject)
        elif name == "messages":
            self._show_messages(d)
        elif name == "runlog":
            self._show_runlog(d, subject)
        elif name == "memory":
            self.query_one("#pane-memory", TextPane).set_content(Text(d.memory), key=d.memory, subject=subject)
        elif name == "charter":
            self.query_one("#pane-charter", TextPane).set_content(Text(d.charter), key=d.charter, subject=subject)

    def _show_messages(self, d: AgentDetail) -> None:
        table = self.query_one("#pane-messages", NavTable)
        self._msg_rows = {}
        rows = []
        for m in d.messages:
            key = f"{m.box}:{m.id}"
            self._msg_rows[key] = m
            when = f"{m.when:%m-%d %H:%M:%S}" if m.when else "?"
            who = f"{m.sender} -> {m.to}"
            style = "bold" if m.box == "inbox" else ""
            title = m.title or "(no title)"
            if m.status:
                title += f"  [{m.status}]"
            if m.budget:
                title += f"  +{m.budget} runs"
            rows.append((key, [Text(when, style=style), Text(m.box, style="yellow" if m.box == "inbox" else "dim"),
                               Text(m.type, style=style), Text(who, style=style), Text(title, style=style)]))
        table.sync([("when", "when"), ("box", "box"), ("type", "type"), ("who", "from -> to"), ("title", "title")], rows)
        self.query_one("#msg-hint", Static).update(
            Text(f"{len(d.messages)} message(s), newest first; unread in bold.  Enter opens the selected one.", style="dim"))

    def _show_runlog(self, d: AgentDetail, subject: str) -> None:
        log = d.runlog
        pane = self.query_one("#pane-runlog", TextPane)
        out = Text()
        if log.path is None:
            out.append(log.note or "no run log", style="dim")
            pane.set_content(out, key=("none", log.note), subject=subject)
            return
        for h in log.header:
            out.append(h + "\n", style="bold cyan")
        out.append(f"{log.rel}  ({log.size:,} bytes)" + ("  [following]" if log.running else "  [last run]") + "\n", style="dim")
        if log.truncated:
            out.append(f"... only the last {len(log.lines)} lines are shown ...\n", style="dim")
        out.append("\n")
        for line in log.lines:
            out.append(line + "\n", style="dim" if line.startswith("# ") else "")
        pane.set_content(out, key=(log.path, log.stamp, log.size, len(log.lines), log.header[-1:] if log.header else None, log.running),
                         subject=subject)

    @on(DataTable.RowSelected, "#pane-messages")
    def _open_message(self, event: DataTable.RowSelected) -> None:
        row = self._msg_rows.get(event.row_key.value or "")
        if row is None:
            return
        title = f"{row.type} {row.id}"
        self.push_screen(TextScreen(title, self.data.message_text(row)))

    # ---------------------------------------------------------------- workflows
    def _show_requests(self, rows: list[RequestRow]) -> None:
        table = self.query_one("#flows-table", NavTable)
        self._req_rows = {r.id: r for r in rows}
        style = {"working": "green", "waiting": "blue", "stalled": "bold red", "blocked": "bold yellow", "done": "dim", "failed": "red"}
        cells = []
        for r in rows:
            st = style.get(r.klass, "")
            last = fmt_dur(r.last_activity_s * 1000) + " ago" if r.last_activity_s is not None else "-"
            title = r.title + (" (rework)" if r.revises else "") + (f" [{r.service}]" if r.service else "")
            state = r.state if len(r.state) <= 34 else r.state[:33] + "…"
            runs = f"{r.runs_used}/{r.runs_given}"
            cells.append((r.id, [Text(state, style=st), Text(title), Text(r.assignee), Text(runs), Text(last),
                                 Text(f"{r.needs_you} for you" if r.needs_you else "", style="bold yellow")]))
        table.sync([("state", "state"), ("title", "request"), ("to", "to"), ("runs", "runs"), ("last", "last activity"),
                    ("needs", "needs you")], cells)
        if not rows:
            self.query_one("#flows-title", Static).update("")

    @on(DataTable.RowSelected, "#flows-table")
    def _open_trace(self, event: DataTable.RowSelected) -> None:
        rid = event.row_key.value
        if rid:
            self.open_trace(rid)

    def open_trace(self, rid: str) -> None:
        self.flow_open = rid
        row = self._req_rows.get(rid)
        title = self.query_one("#flows-title", Static)
        title.update(Text(f"trace of {row.title if row else rid}   (Esc: back, r: recompute)"))
        title.remove_class("hidden")
        self.query_one("#flows-table").add_class("hidden")
        pane = self.query_one("#flows-detail", TextPane)
        pane.remove_class("hidden")
        pane.set_content(Text("computing the trace ..."), subject=rid)
        pane.focus()
        self.run_worker(lambda: self._compute_trace(rid), thread=True, group="trace", exit_on_error=False)

    def _compute_trace(self, rid: str) -> None:
        try:
            body = self.data.request_line(rid) + "\n\n" + self.data.trace_text(rid)
        except Exception as exc:  # noqa: BLE001
            body = f"the trace could not be computed: {type(exc).__name__}: {exc}"
        try:
            self.call_from_thread(self._show_trace, rid, body)
        except Exception:  # noqa: BLE001
            pass

    def _show_trace(self, rid: str, body: str) -> None:
        if self.flow_open != rid:
            return
        pane = self.query_one("#flows-detail", TextPane)
        pane.set_content(Text(body), key=None, subject=rid)

    # ---------------------------------------------------------------- services
    def _show_services(self, rows: list[ServiceRow], doc: list[Section] | None) -> None:
        table = self.query_one("#services-table", NavTable)
        self._svc_rows = {f"{r.owner}/{r.name}": r for r in rows}
        cells = []
        for r in rows:
            s = r.stats
            fb = f"{s.accept}✓ {s.reject}✗" if (s.accept or s.reject) else "-"
            cells.append((f"{r.owner}/{r.name}", [
                Text(r.name, style="bold"), Text(r.owner), Text(f"c{r.contract_version} p{r.playbook_version}" + (" locked" if r.locked else "")),
                Text(str(s.requests)), Text(f"{s.done}/{s.failed}/{s.open}"), Text(str(s.reworked)), Text(fb),
                Text(f"{s.avg_runs:g}" if s.avg_runs is not None else "-"), Text(r.playbook_reason, style="dim")]))
        table.sync([("name", "service"), ("owner", "owner"), ("ver", "versions"), ("req", "requests"), ("res", "done/failed/open"),
                    ("rework", "reworked"), ("fb", "feedback"), ("runs", "avg runs"), ("why", "latest playbook reason")], cells)
        if doc is not None and self.service_open:
            pane = self.query_one("#services-detail", TextPane)
            text = doc_renderable(doc)
            pane.set_content(text, key=text.plain, subject=self.service_open)

    @on(DataTable.RowSelected, "#services-table")
    def _open_service(self, event: DataTable.RowSelected) -> None:
        key = event.row_key.value or ""
        row = self._svc_rows.get(key)
        if row is None:
            return
        self.service_open = (row.owner, row.name)
        title = self.query_one("#services-title", Static)
        title.update(Text(f"service {row.name} of {row.owner}   (Esc: back)"))
        title.remove_class("hidden")
        self.query_one("#services-table").add_class("hidden")
        pane = self.query_one("#services-detail", TextPane)
        pane.remove_class("hidden")
        pane.set_content(Text("..."), subject=self.service_open)
        pane.focus()
        self.request_refresh()

    # ---------------------------------------------------------------- events
    def _show_events(self, events: list[JsonObject], lines: list[EventLine]) -> None:
        pane = self.query_one("#events-body", TextPane)
        last = events[-1] if events else None
        key = (len(events), last.get("seq") if last else None, last.get("ts") if last else None, last.get("pid") if last else None,
               self.event_text, self.event_errors, self.raw_events)
        pane.set_content(event_text(lines) if events else Text("(no matching events)", style="dim"), key=key,
                         subject=(self.event_text, self.event_errors), follow=self.event_follow)
        total = len(self.data.feed.events) if self.data.feed else 0
        bits = [f"{len(events)} of {total} event(s) in memory", "errors only" if self.event_errors else "all kinds",
                f"filter: {self.event_text!r}" if self.event_text else "no filter", "following" if self.event_follow else "not following",
                "raw" if self.raw_events else "readable"]
        if self.data.feed is not None and not self.data.feed.any:
            bits.append("this organization has no event files yet")
        self.query_one("#events-bar", Static).update(Text("  ·  ".join(bits) + "      e errors · / filter · f follow · x raw", style="dim"))

    def action_toggle_errors(self) -> None:
        self.event_errors = not self.event_errors
        self.request_refresh()

    def action_filter(self) -> None:
        box = self.query_one("#events-filter", Input)
        box.remove_class("hidden")
        box.focus()

    def action_toggle_raw(self) -> None:
        """Events as the log has them (ids, process groups, budgets before/after, arguments) or as readable lines."""
        self.raw_events = not self.raw_events
        self.request_refresh()

    def action_toggle_follow(self) -> None:
        self.event_follow = not self.event_follow
        pane = self.query_one("#events-body", TextPane)
        pane.sticky = self.event_follow
        if self.event_follow:
            pane.scroll_end(animate=False)
        self.request_refresh()

    @on(Input.Changed, "#events-filter")
    def _filter_changed(self, event: Input.Changed) -> None:
        self.event_text = event.value.strip()
        self.request_refresh()

    @on(Input.Submitted, "#events-filter")
    def _filter_done(self, event: Input.Submitted) -> None:
        self.query_one("#events-body", TextPane).focus()

    # ---------------------------------------------------------------- health
    def _show_health(self, h: HealthView) -> None:
        out = Text()
        out.append("observe now\n", style="bold underline")
        out.append(h.now_text + "\n\n")
        out.append(f"Health flags ({h.summary})\n", style="bold underline")
        if h.flagged:
            for addr, flags in h.flagged:
                out.append(f"{addr}\n", style="bold")
                for flag, why in flags:
                    why = why.removeprefix(flag.replace("_", " ") + ": ")  # "!paused: paused: ..." says it once
                    out.append(f"   !{flag}: {why}\n", style="yellow")
        else:
            out.append("no agent is flagged\n")
        out.append("\nConsistency check (c runs it)\n", style="bold underline")
        out.append((self._check_text or "not run yet - press c") + "\n", style="" if self._check_text else "dim")
        self.query_one("#health-body", TextPane).set_content(out, key=out.plain, subject="health")

    def action_check(self) -> None:
        if self.view != "health":
            return
        self._check_text = "running the check ..."
        self.run_worker(self._run_check, thread=True, group="check", exit_on_error=False)
        self.request_refresh()

    def _run_check(self) -> None:
        when, text, ok = self.data.run_check()
        stamp = f"{when:%H:%M:%S}Z"
        out = f"checked at {stamp}\n{text}"
        self._check_text = out
        try:
            self.call_from_thread(self.request_refresh)
        except Exception:  # noqa: BLE001
            pass

    # ---------------------------------------------------------------- global actions
    def action_view(self, name: str) -> None:
        if name not in VIEWS:
            return
        self.view = name
        self.query_one("#screens", ContentSwitcher).current = f"{name}-view"
        focus = {"org": "#agent-tree", "flows": "#flows-detail" if self.flow_open else "#flows-table",
                 "services": "#services-detail" if self.service_open else "#services-table",
                 "events": "#events-body", "health": "#health-body"}[name]
        self.query_one(focus).focus()
        self._show_header()
        self.refresh_bindings()
        self.request_refresh()

    def action_refresh(self) -> None:
        if self.flow_open and self.view == "flows":
            self.open_trace(self.flow_open)
        self.request_refresh()

    def action_toggle_pause(self) -> None:
        self.paused = not self.paused
        if self._timer is not None:
            (self._timer.pause if self.paused else self._timer.resume)()
        self._show_header()

    def action_help(self) -> None:
        if isinstance(self.screen, TextScreen):
            return
        self.push_screen(TextScreen("hirearchy dash - keys", HELP, box_id="help-box"))

    def action_back(self) -> None:  # type: ignore[override]  # (Textual's is a coroutine that goes back in a history this app does not have)
        if isinstance(self.screen, ModalScreen):
            return
        if self.view == "flows" and self.flow_open:
            self.flow_open = None
            self.query_one("#flows-title").add_class("hidden")
            self.query_one("#flows-detail").add_class("hidden")
            self.query_one("#flows-table").remove_class("hidden")
            self.query_one("#flows-table").focus()
        elif self.view == "services" and self.service_open:
            self.service_open = None
            self.query_one("#services-title").add_class("hidden")
            self.query_one("#services-detail").add_class("hidden")
            self.query_one("#services-table").remove_class("hidden")
            self.query_one("#services-table").focus()
        elif self.view == "org":
            self.query_one("#agent-tree").focus()
        elif self.view == "events":
            box = self.query_one("#events-filter", Input)
            if self.event_text or not box.has_class("hidden"):
                box.value = ""
                box.add_class("hidden")
                self.event_text = ""
                self.query_one("#events-body").focus()
                self.request_refresh()

    # the keys of one screen are only active on that screen
    def check_action(self, action: str, parameters: tuple[object, ...]) -> bool | None:
        modal = isinstance(self.screen, ModalScreen)
        if action in ("view", "refresh", "back", "tab") and modal:
            return False
        if action in ("toggle_errors", "filter", "toggle_follow"):
            return self.view == "events" and not modal
        if action == "toggle_raw":
            return not modal and (self.view == "events" or (self.view == "org" and self._active_tab() == "activity"))
        if action == "check":
            return self.view == "health" and not modal
        if action in ("tab", "focus_tree"):
            return self.view == "org" and not modal
        return True
