"""The commands that show the organization: ``status health progress dash``."""

from __future__ import annotations

import argparse
import json

from ..daemon import SchedulerStatus
from ..dashdata import SnapshotRenderer
from ..health import HealthAnalyzer, HealthRenderer
from ..kernel import ROOT, Provider
from ..mail import TaskQuery
from ..overview import OrgTree
from ..progress import ProgressReporter
from ._ports import Arguments, Command, DashboardRunner, OrgSession, Output, Terminal


class StatusCommand(Command):
    def __init__(
        self, session: OrgSession, tree: Provider[OrgTree], tasks: Provider[TaskQuery], scheduler: Provider[SchedulerStatus], out: Output,
    ) -> None:
        self._session = session
        self._tree = tree
        self._tasks = tasks
        self._scheduler = scheduler
        self._out = out

    def add_arguments(self, sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
        s = sub.add_parser("status", help="show the organization tree")
        s.set_defaults(fn=self.run)

    def run(self, args: Arguments) -> None:
        self._session.open(args)
        self._out.say(self._tree().tree())
        out = self._tasks().outstanding(ROOT)
        if out:
            self._out.say("\nyour outstanding tasks:")
            for t in out:
                self._out.say(f"  {t.id} \"{t.title}\" -> {t.to}")
        self._out.say(f"\n{self._scheduler().describe()}")


class HealthCommand(Command):
    def __init__(self, session: OrgSession, analyzer: Provider[HealthAnalyzer], renderer: Provider[HealthRenderer], out: Output) -> None:
        self._session = session
        self._analyzer = analyzer
        self._renderer = renderer
        self._out = out

    def add_arguments(self, sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
        s = sub.add_parser("health", help="show stuck, expensive, low-quality and idle agents and branches")
        s.add_argument("--agent", metavar="ADDR", help="only this agent and its subtree (default: whole organization)")
        s.add_argument("--json", action="store_true", help="print the structured data")
        s.set_defaults(fn=self.run)

    def run(self, args: Arguments) -> None:
        self._session.open(args)
        report = self._analyzer().org_health(args.agent or ROOT)
        self._out.say(json.dumps(report.to_dict(), indent=2) if args.json else self._renderer().render_text(report))


class ProgressCommand(Command):
    def __init__(self, session: OrgSession, progress: Provider[ProgressReporter], out: Output) -> None:
        self._session = session
        self._progress = progress
        self._out = out

    def add_arguments(self, sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
        s = sub.add_parser("progress", help="one line per task you gave: state, who is busy, cost, last activity; what needs you")
        s.add_argument("task_id", nargs="?", help="only this task (default: open tasks and those finished in the last day)")
        s.add_argument("--wait", type=int, default=0, metavar="SECONDS",
                       help="first wait (up to 900) until a task finishes, fails, blocks or stalls, or something needs you")
        s.set_defaults(fn=self.run)

    def run(self, args: Arguments) -> None:
        self._session.open(args)
        self._out.say(self._progress().describe_progress(args.task_id, args.wait))


class DashCommand(Command):
    """The terminal dashboard. Read-only: no file is written in the org and no event is emitted."""

    def __init__(self, session: OrgSession, snapshots: Provider[SnapshotRenderer], dashboard: DashboardRunner, terminal: Terminal, out: Output) -> None:
        self._session = session
        self._snapshots = snapshots
        self._dashboard = dashboard
        self._terminal = terminal
        self._out = out

    def add_arguments(self, sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
        s = sub.add_parser("dash", help="terminal dashboard: agents, workflows, services, events, health (read-only)")
        s.add_argument("--root", dest="root", default=argparse.SUPPRESS, help="organization directory (same as the global --root)")
        s.add_argument("--interval", type=float, default=2.0, metavar="SECONDS", help="refresh every SECONDS (default 2)")
        s.add_argument("--once", action="store_true", help="print a plain-text snapshot and exit (also used when there is no terminal)")
        s.set_defaults(fn=self.run)

    def run(self, args: Arguments) -> None:
        root = self._session.open(args)
        if args.once or not self._terminal.is_interactive():
            self._out.say(self._snapshots().render_once())
            return
        self._dashboard.run(root, args.interval)
