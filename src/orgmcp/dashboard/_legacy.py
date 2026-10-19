# mypy: ignore-errors
"""The terminal dashboard (``orgmcp dash``): a Textual app, thin over :mod:`orgmcp.dashboard_data`.

Read-only: it never writes inside the organization and emits no event. All reading happens in a worker thread
(one refresh at a time); the widgets are updated on the UI thread and keep selection, scroll position and the
expanded nodes of the agent tree across refreshes. An exception in a refresh is shown in the status line above the
footer and the app keeps running.

Screens (one window, switched with 1-5): Org, Workflows, Services, Events, Health. Keys: see ``HELP`` (``?``).
"""

from __future__ import annotations

import importlib
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable

from rich.text import Text
from textual import on
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import ContentSwitcher, DataTable, Footer, Input, Static, TabbedContent, TabPane, Tree

from ..dashdata import AgentDetail, EventLine, HealthView, MsgRow, RequestRow, RunLog, Section, ServiceRow, Snapshot, doc_text
from ..kernel import ROOT, fmt_dur

VIEWS = ("org", "flows", "services", "events", "health")
VIEW_NAMES = {"org": "Org", "flows": "Workflows", "services": "Services", "events": "Events", "health": "Health"}
TABS = ("overview", "activity", "messages", "runlog", "memory", "charter")
TAB_NAMES = {"overview": "Overview", "activity": "Activity", "messages": "Messages", "runlog": "Run log",
             "memory": "Memory", "charter": "Charter"}

KIND_STYLE = {"running": "bold green", "queued": "yellow", "working": "cyan", "waiting": "blue", "idle": "dim",
              "paused": "magenta", "budget": "bold red", "you": "bold white"}

HELP = """\
GLOBAL
  1 2 3 4 5     Org · Workflows · Services · Events · Health
  Tab / Shift+Tab   cycle focus between the panes
  ↑ ↓  j k      move            g / G   top / bottom
  ← →  h l      fold / unfold a node, or switch pane
  Enter         open (agent -> its details, request -> trace, service -> cases, message -> text)
  Esc / Backspace   back (close an overlay, leave a trace or a service, return to the agent list)
  r             refresh now     p   pause / resume the automatic refresh
  ?             this help       q   quit

1 ORG  (agent tree on the left, details of the selected agent on the right)
  [ ]           previous / next tab: Overview · Activity · Messages · Run log · Memory · Charter
  Space         fold / unfold the selected node
  root selected: what needs you and your requests; an agent: its run, tasks, delegations, latest activity
  Messages tab: Enter opens the message.   Run log tab: follows the log while it grows (scroll up to stop).

2 WORKFLOWS   one line per request you gave; Enter opens its trace (messages, runs, tool calls, timings)
3 SERVICES    one line per service; Enter opens its record, cases, playbook and contract
4 EVENTS      the live merged event stream
  e             errors only    /   filter (words: agent, kind, trace, tool)    f   follow on / off
  x             raw events: ids, process groups, budgets, arguments (also on the Org > Activity tab)
5 HEALTH      observe now, health flags;  c  runs the consistency check (on demand)

The dashboard is read-only: grants, start/stop and feedback stay with the assistant and the CLI.
"""


def _plain(value: str) -> Text:
    """Literal text (never markup)."""
    return Text(value)


def doc_renderable(doc: list[Section]) -> Text:
    out = Text()
    for i, s in enumerate(doc):
        if i:
            out.append("\n")
        if s.title:
            out.append(s.title + "\n", style="bold underline")
        for n, line in enumerate(s.lines):
            out.append(line + "\n", style="red" if n in s.errors else "")
    return out


def event_text(lines: list[EventLine]) -> Text:
    """The event lines; refusals and failures in red. Long lines wrap in the pane (nothing is cut)."""
    out = Text()
    for line in lines:
        out.append(line.text + "\n", style="red" if line.error else "")
    return out


# ================================================================================================ widgets


class TextPane(VerticalScroll, can_focus=True):
    """A scrollable block of text that keeps its scroll position when the text is replaced; ``sticky`` panes follow
    the end while they are scrolled to the end (like ``tail -f``)."""

    BINDINGS = [
        Binding("j", "scroll_down", "Down", show=False),
        Binding("k", "scroll_up", "Up", show=False),
        Binding("g", "scroll_home", "Top", show=False),
        Binding("G", "scroll_end", "Bottom", show=False),
        Binding("space", "page_down", "Page", show=False),
    ]

    def __init__(self, *, id: str | None = None, sticky: bool = False, wrap: bool = True):
        super().__init__(id=id, classes="" if wrap else "nowrap")
        self.sticky = sticky
        self.body = Static("", markup=False)
        self._key: object = None
        self._subject: object = None
        self.text_now = ""

    def compose(self) -> ComposeResult:
        yield self.body

    def set_content(self, content: Text | str, key: object = None, subject: object = None, follow: bool | None = None) -> None:
        """Show ``content``. Unchanged ``key`` -> nothing happens. A new ``subject`` (another agent) starts at the top
        (sticky panes: at the end); the same subject keeps the scroll position."""
        if key is not None and key == self._key and subject == self._subject:
            return
        new_subject = subject != self._subject
        at_end = self.scroll_y >= self.max_scroll_y - 1
        self._key, self._subject = key, subject
        renderable = content if isinstance(content, Text) else Text(content)
        self.text_now = renderable.plain
        self.body.update(renderable)
        stick = self.sticky if follow is None else follow
        if new_subject:
            self.call_after_refresh(self.scroll_end if stick else self.scroll_home, animate=False)
        elif stick and at_end:
            self.call_after_refresh(self.scroll_end, animate=False)


def _hidden(widget):
    widget.add_class("hidden")
    return widget


class NavTable(DataTable):
    """A row table with vim keys that updates in place: the cursor row (by key) and the scroll position survive."""

    BINDINGS = [
        Binding("j", "cursor_down", "Down", show=False),
        Binding("k", "cursor_up", "Up", show=False),
        Binding("g", "top", "Top", show=False),
        Binding("G", "bottom", "Bottom", show=False),
        Binding("enter", "select_cursor", "Open"),
    ]

    def __init__(self, *, id: str | None = None):
        super().__init__(id=id, cursor_type="row", zebra_stripes=True)
        self._cells: dict[str, list] = {}
        self._keys: list[str] = []
        self._columns: list[tuple[str, str]] = []

    def action_top(self) -> None:
        if self.row_count:
            self.move_cursor(row=0)

    def action_bottom(self) -> None:
        if self.row_count:
            self.move_cursor(row=self.row_count - 1)

    def current_key(self) -> str | None:
        if not self.row_count:
            return None
        try:
            return self.coordinate_to_cell_key(self.cursor_coordinate).row_key.value
        except Exception:  # noqa: BLE001
            return None

    def sync(self, columns: list[tuple[str, str]], rows: list[tuple[str, list]]) -> None:
        if not self.columns:
            for key, label in columns:
                self.add_column(label, key=key)
            self._columns = list(columns)
        keys = [k for k, _ in rows]
        if keys == self._keys:  # same rows in the same order: change only the cells that differ
            for k, cells in rows:
                old = self._cells.get(k, [])
                for i, ((ck, _), cell) in enumerate(zip(columns, cells)):
                    if i >= len(old) or old[i] != cell:
                        self.update_cell(k, ck, cell)
                self._cells[k] = list(cells)
            return
        current, scroll = self.current_key(), (self.scroll_x, self.scroll_y)
        self.clear()
        for k, cells in rows:
            self.add_row(*cells, key=k)
        self._keys = keys
        self._cells = {k: list(c) for k, c in rows}
        if current in keys:
            self.move_cursor(row=keys.index(current), animate=False, scroll=False)
            self.call_after_refresh(self.scroll_to, scroll[0], scroll[1], animate=False)


class AgentTree(Tree[str]):
    """The agent hierarchy. Nodes persist between refreshes (expansion and cursor are kept); the tree is rebuilt only
    when agents appear or disappear."""

    BINDINGS = [
        Binding("j", "cursor_down", "Down", show=False),
        Binding("k", "cursor_up", "Up", show=False),
        Binding("g", "top", "Top", show=False),
        Binding("G", "bottom", "Bottom", show=False),
        Binding("enter", "select_cursor", "Open"),
        Binding("left,h", "fold", "Fold", key_display="←/h"),
        Binding("right,l", "unfold", "Unfold/pane", key_display="→/l"),
    ]

    def __init__(self, *, id: str | None = None):
        super().__init__("root", data=ROOT, id=id)
        self.show_root = True
        self.auto_expand = False
        self.guide_depth = 3
        self.nodes: dict[str, object] = {}
        self._order: list[str] = []
        self._known: set[str] = set()
        self.quiet = False  # True while the tree is being rebuilt: no highlight events for the app
        self._snap: Snapshot | None = None
        self._labels: dict[str, Text] = {}

    def action_top(self) -> None:
        self.move_cursor(self.root)

    def action_bottom(self) -> None:
        self.move_cursor_to_line(len(self._tree_lines) - 1)

    def action_fold(self) -> None:
        node = self.cursor_node
        if node is None:
            return
        if node.is_expanded and node.children:
            node.collapse()
        elif node.parent is not None:
            self.move_cursor(node.parent)

    def action_unfold(self) -> None:
        node = self.cursor_node
        if node is None:
            return
        if node.children and not node.is_expanded:
            node.expand()
        else:
            self.app.action_pane()  # type: ignore[attr-defined]

    @staticmethod
    def label_for(snap: Snapshot, addr: str, collapsed: bool, avail: int | None = None) -> Text:
        """The label of a node. ``avail``: cells the label may take (the pane width less the guides); a state that is
        longer is cut with an ellipsis in its main text - the mail count and the budget at the end always stay, the
        whole state is in the Overview tab."""
        r = snap.agents[addr]
        below = ""
        if collapsed and (r.below_running or r.below_queued):  # what a folded node hides: "[2 running, 1 queued below]"
            below = "  [" + ", ".join(f"{n} {w}" for n, w in ((r.below_running, "running"), (r.below_queued, "queued")) if n) + " below]"
        if addr == ROOT:
            t = Text.assemble(("★ ", "bold yellow"), ("root", "bold"), (" (you)", "dim"))
            if snap.needs_you:
                t.append(f"  needs you: {len(snap.needs_you)}", style="bold yellow")
            if below:
                t.append(below, style="dim")
            return t
        style = KIND_STYLE.get(r.kind, "")
        budget = f"  {r.budget} left" if r.budget is not None else ""
        main = r.main or r.word
        if avail is not None:
            def room_for(tail: str, with_budget: bool = True) -> int:
                return avail - (len(r.glyph) + 1 + len(r.name) + 2 + len(r.note) + (len(budget) if with_budget else 0) + len(tail))

            short = r.short or main
            # in order of preference: everything; the shorter wording; without the fold summary; without the budget; cut
            for text, tail, with_budget in ((main, below, True), (short, below, True), (short, "", True), (short, "", False)):
                if room_for(tail, with_budget) >= len(text):
                    main, below = text, tail
                    if not with_budget:
                        budget = ""
                    break
            else:
                main, below, budget = short, "", ""
                room = room_for("", False)
                main = main[: max(room - 1, 0)].rstrip() + "…" if room > 1 else "…"
        t = Text.assemble((r.glyph + " ", style), (r.name, "bold"), ("  " + main + r.note, style))
        if budget and r.budget is not None:
            t.append(budget, style="dim" if r.budget > 0 else "red")
        if below:
            t.append(below, style="dim")
        if avail:
            t.truncate(avail, overflow="ellipsis")
        return t

    def avail(self, addr: str) -> int | None:
        """Cells a node's label may take: the content width less the guides (and the fold icon) of its depth."""
        width = self.scrollable_content_region.width
        if width <= 0 or self._snap is None or addr not in self._snap.agents:
            return None
        level = self._snap.agents[addr].depth
        return max(12, width - level * self.guide_depth - 2)

    def on_resize(self, event) -> None:
        self._labels = {}  # widths changed: every label is made again
        if self._snap is not None:
            self.sync(self._snap)

    def _relabel(self, node) -> None:
        if self._snap is not None and node.data in self._snap.agents:
            label = self.label_for(self._snap, node.data, collapsed=not node.is_expanded, avail=self.avail(node.data))
            self._labels[node.data] = label
            node.set_label(label)

    def on_tree_node_collapsed(self, event: Tree.NodeCollapsed) -> None:
        self._relabel(event.node)

    def on_tree_node_expanded(self, event: Tree.NodeExpanded) -> None:
        self._relabel(event.node)

    def sync(self, snap: Snapshot) -> None:
        self._snap = snap
        order = [a for a in snap.order]
        if order != self._order:
            self._rebuild(snap, order)
        for addr, node in self.nodes.items():
            if addr in snap.agents:
                label = self.label_for(snap, addr, collapsed=not node.is_expanded, avail=self.avail(addr))
                if self._labels.get(addr) != label:  # unchanged labels are not touched: no redraw
                    self._labels[addr] = label
                    node.set_label(label)  # type: ignore[attr-defined]

    def _rebuild(self, snap: Snapshot, order: list[str]) -> None:
        keep = self.cursor_node.data if self.cursor_node is not None else ROOT
        expanded = {a for a, n in self.nodes.items() if n.is_expanded}  # type: ignore[attr-defined]
        first = not self._known
        self.quiet = True
        try:
            self.clear()
            self._labels = {}
            self.nodes = {ROOT: self.root}
            self.root.data = ROOT
            self.root.expand()
            for addr in order[1:]:
                row = snap.agents[addr]
                parent = self.nodes.get(row.parent or ROOT, self.root)
                new = addr not in self._known
                node = parent.add(self.label_for(snap, addr, False, self.avail(addr)), data=addr, expand=(new or addr in expanded),  # type: ignore[attr-defined]
                                  allow_expand=bool(row.children))
                self.nodes[addr] = node
            self._known = set(order)
            self._order = list(order)
            target = self.nodes.get(keep, self.root)
            try:
                _ = self._tree_lines  # build the lines so that node.line is valid
            except Exception:  # noqa: BLE001
                pass
            self.move_cursor(target)
        finally:
            self.quiet = False


class ContextFooter(Footer):
    """The footer, rebuilt only when the keys it shows actually change (Textual rebuilds it on every binding refresh,
    which is far too costly for a screen that updates every few seconds)."""

    _shown: tuple | None = None

    def bindings_changed(self, screen) -> None:
        try:
            shown = tuple((b.key, b.action, b.description, enabled) for (_, b, enabled, _) in screen.active_bindings.values() if b.show)
        except Exception:  # noqa: BLE001
            shown = None
        if shown is not None and shown == self._shown:
            return
        self._shown = shown
        super().bindings_changed(screen)


class StatusBar(Vertical):
    """The two header lines: the title with the screen switcher, and the scheduler + counts."""

    def __init__(self, **kw):
        super().__init__(**kw)
        self._last = {}

    def compose(self) -> ComposeResult:
        yield Static("", id="header-title", markup=False)
        yield Static("", id="header-counts", markup=False)

    def show(self, snap: Snapshot | None, view: str, paused: bool, interval: float, error: str | None = None) -> None:
        title = Text.assemble(("orgmcp dash ", "bold"))
        if snap is not None:
            title.append(snap.org_name, style="bold cyan")
            title.append(f"  {snap.at:%H:%M:%S}Z", style="dim")
        title.append("  ")
        for i, v in enumerate(VIEWS, 1):
            on_it = v == view
            title.append(f" {i} {VIEW_NAMES[v]} ", style="reverse bold" if on_it else "dim")
        if paused:
            title.append("  refresh paused (p resumes)", style="bold black on yellow")
        else:
            title.append(f"  refresh {interval:g}s", style="dim")
        if error:
            title.append("  refresh failed - see below", style="bold white on red")
        self._set("#header-title", title)
        counts = Text()
        if snap is None:
            counts.append("loading ...", style="dim")
        else:
            s = snap.scheduler
            counts.append(s.text, style="green" if s.state == "running" else "bold red" if s.state != "running" else "")
            counts.append("  |  ")
            counts.append(f"running {snap.running}/{snap.max_parallel}", style="bold green" if snap.running else "dim")
            counts.append("  queued ")
            counts.append(str(snap.queued), style="yellow" if snap.queued else "dim")
            counts.append("  waiting on you ")
            counts.append(str(len(snap.needs_you)), style="bold yellow" if snap.needs_you else "dim")
            counts.append("  errors 15m ")
            counts.append(str(snap.errors_15m), style="bold red" if snap.errors_15m else "dim")
            if snap.bad_files:
                counts.append(f"  unreadable files {len(snap.bad_files)}", style="red")
        self._set("#header-counts", counts)

    def _set(self, selector: str, text: Text) -> None:
        if self._last.get(selector) != text:
            self._last[selector] = text
            self.query_one(selector, Static).update(text)

    _last: dict


class TextScreen(ModalScreen[None]):
    """A scrollable overlay (a message, the help). Esc / Backspace / Enter close it."""

    BINDINGS = [
        Binding("escape,backspace,enter", "close", "Close"),
        Binding("question_mark", "close", "Close", show=False),
    ]

    def __init__(self, title: str, text: str, *, box_id: str = "modal-box"):
        super().__init__()
        self.title_text, self.body_text, self.box_id = title, text, box_id

    def compose(self) -> ComposeResult:
        with Vertical(id=self.box_id):
            yield Static(Text(self.title_text), id="modal-title", markup=False)
            pane = TextPane(id="modal-pane")
            yield pane

    def on_mount(self) -> None:
        pane = self.query_one("#modal-pane", TextPane)
        pane.set_content(Text(self.body_text), subject=self.title_text)
        pane.focus()

    def action_close(self) -> None:
        self.dismiss(None)


# ================================================================================================ the app


@dataclass
class Ctx:
    """What the worker needs to know about the screen (captured on the UI thread)."""

    view: str
    selected: str
    flow_open: str | None
    service_open: tuple[str, str] | None
    event_text: str
    event_errors: bool
    raw: bool = False


@dataclass
class Tick:
    snap: Snapshot | None = None
    detail: AgentDetail | None = None
    requests: list[RequestRow] | None = None
    services: list[ServiceRow] | None = None
    service_doc: list[Section] | None = None
    events: list[dict] | None = None
    event_lines: list[EventLine] | None = None
    health: HealthView | None = None
    error: str | None = None
    ms: float = 0.0


SCREENS = Binding.Group("Screen", compact=True)
TAB_KEYS = Binding.Group("Tab", compact=True)


class DashApp(App):
    TITLE = "orgmcp dash"
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

    def __init__(self, root: str | Path, interval: float = 2.0, now: Callable[[], datetime] | None = None):
        super().__init__()
        self.data = importlib.import_module(f"orgmcp.{'dashboard_data'}").DashData(root, now=now)  # (an entry point may not import it: the layers contract)
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
        self._timer = None
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

    async def settle(self, pilot=None) -> None:
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
    def _highlighted(self, event: Tree.NodeHighlighted) -> None:
        tree = self.query_one("#agent-tree", AgentTree)
        if tree.quiet:
            return
        addr = event.node.data or ROOT
        if addr != self.selected:
            self.selected = addr
            self.request_refresh()

    @on(Tree.NodeSelected, "#agent-tree")
    def _selected(self, event: Tree.NodeSelected) -> None:
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
    def _show_events(self, events: list[dict], lines: list[EventLine]) -> None:
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
        self.push_screen(TextScreen("orgmcp dash - keys", HELP, box_id="help-box"))

    def action_back(self) -> None:
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
    def check_action(self, action: str, parameters: tuple) -> bool | None:
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


def run_dashboard(root: str | Path, interval: float = 2.0) -> None:
    DashApp(root, interval=interval).run()
