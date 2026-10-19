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
        raise NotImplementedError

    def run(self, args: Arguments) -> None:
        raise NotImplementedError


class HealthCommand(Command):
    def __init__(self, session: OrgSession, analyzer: Provider[HealthAnalyzer], renderer: Provider[HealthRenderer], out: Output) -> None:
        self._session = session
        self._analyzer = analyzer
        self._renderer = renderer
        self._out = out

    def add_arguments(self, sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
        raise NotImplementedError

    def run(self, args: Arguments) -> None:
        raise NotImplementedError


class ProgressCommand(Command):
    def __init__(self, session: OrgSession, progress: Provider[ProgressReporter], out: Output) -> None:
        self._session = session
        self._progress = progress
        self._out = out

    def add_arguments(self, sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
        raise NotImplementedError

    def run(self, args: Arguments) -> None:
        raise NotImplementedError


class DashCommand(Command):
    """The terminal dashboard. Read-only: no file is written in the org and no event is emitted."""

    def __init__(self, session: OrgSession, snapshots: Provider[SnapshotRenderer], dashboard: DashboardRunner, terminal: Terminal, out: Output) -> None:
        self._session = session
        self._snapshots = snapshots
        self._dashboard = dashboard
        self._terminal = terminal
        self._out = out

    def add_arguments(self, sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
        raise NotImplementedError

    def run(self, args: Arguments) -> None:
        raise NotImplementedError
