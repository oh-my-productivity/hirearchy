"""The commands that maintain or run the organization: ``upgrade-rules install-skill review run mcp kiro-profile``."""

from __future__ import annotations

import argparse
import json

from ..kernel import OrgError, Provider
from ..kiro import McpServerLocator, ProfileProvisioner
from ..review import HealthReviewer
from ..skill import SkillInstaller
from ..snapshots import OrgSnapshotter
from ..upgrade import RulesUpgrader
from ._ports import Arguments, Command, McpRunner, OrgSession, Output, SchedulerRunner


class UpgradeRulesCommand(Command):
    def __init__(self, session: OrgSession, upgrader: Provider[RulesUpgrader], out: Output) -> None:
        self._session = session
        self._upgrader = upgrader
        self._out = out

    def add_arguments(self, sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
        raise NotImplementedError

    def run(self, args: Arguments) -> None:
        raise NotImplementedError


class InstallSkillCommand(Command):
    """Needs no organization: it copies a file into a skills directory."""

    def __init__(self, installer: SkillInstaller, out: Output) -> None:
        self._installer = installer
        self._out = out

    def add_arguments(self, sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
        raise NotImplementedError

    def run(self, args: Arguments) -> None:
        raise NotImplementedError


class ReviewCommand(Command):
    def __init__(self, session: OrgSession, reviewer: Provider[HealthReviewer], snapshots: Provider[OrgSnapshotter], out: Output) -> None:
        self._session = session
        self._reviewer = reviewer
        self._snapshots = snapshots
        self._out = out

    def add_arguments(self, sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
        raise NotImplementedError

    def run(self, args: Arguments) -> None:
        raise NotImplementedError


class RunCommand(Command):
    def __init__(self, session: OrgSession, scheduler: SchedulerRunner) -> None:
        self._session = session
        self._scheduler = scheduler

    def add_arguments(self, sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
        raise NotImplementedError

    def run(self, args: Arguments) -> None:
        raise NotImplementedError


class McpCommand(Command):
    def __init__(self, server: McpRunner) -> None:
        self._server = server

    def add_arguments(self, sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
        raise NotImplementedError

    def run(self, args: Arguments) -> None:
        raise NotImplementedError


class KiroProfileCommand(Command):
    def __init__(self, session: OrgSession, profiles: Provider[ProfileProvisioner], locator: Provider[McpServerLocator], out: Output) -> None:
        self._session = session
        self._profiles = profiles
        self._locator = locator
        self._out = out

    def add_arguments(self, sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
        raise NotImplementedError

    def run(self, args: Arguments) -> None:
        raise NotImplementedError
