# mypy: ignore-errors
"""The widgets of the dashboard: the scrollable text pane, the row table, the agent tree, the footer, the two header lines and the overlay.

Textual subclasses (they must inherit the framework's types, so they are exempt from the Protocol rule); they depend only on the data classes of
``dashdata`` and the vocabulary of ``_state``."""

from __future__ import annotations

from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import DataTable, Footer, Static, Tree

from ..dashdata import Snapshot
from ..kernel import ROOT
from ._state import KIND_STYLE, VIEW_NAMES, VIEWS


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
