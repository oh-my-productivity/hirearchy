"""The commands of the standing services: ``services define-service request feedback retire-service``."""

from __future__ import annotations

import argparse

from ..kernel import ROOT, OrgError, Provider, norm
from ..reflection import ServiceReports
from ..services import ContractNormalizer, ServiceCatalog, ServiceCommands
from ..snapshots import OrgSnapshotter
from ._ports import Arguments, Command, OrgSession, Output, TextSource


class ServicesCommand(Command):
    def __init__(self, session: OrgSession, reports: Provider[ServiceReports], out: Output) -> None:
        self._session = session
        self._reports = reports
        self._out = out

    def add_arguments(self, sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
        raise NotImplementedError

    def run(self, args: Arguments) -> None:
        raise NotImplementedError


class DefineServiceCommand(Command):
    def __init__(
        self, session: OrgSession, commands: Provider[ServiceCommands], catalog: Provider[ServiceCatalog], contracts: Provider[ContractNormalizer],
        snapshots: Provider[OrgSnapshotter], text: TextSource, out: Output,
    ) -> None:
        self._session = session
        self._commands = commands
        self._catalog = catalog
        self._contracts = contracts
        self._snapshots = snapshots
        self._text = text
        self._out = out

    def add_arguments(self, sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
        raise NotImplementedError

    def run(self, args: Arguments) -> None:
        raise NotImplementedError


class RequestCommand(Command):
    def __init__(self, session: OrgSession, commands: Provider[ServiceCommands], snapshots: Provider[OrgSnapshotter], out: Output) -> None:
        self._session = session
        self._commands = commands
        self._snapshots = snapshots
        self._out = out

    def add_arguments(self, sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
        raise NotImplementedError

    def run(self, args: Arguments) -> None:
        raise NotImplementedError


class FeedbackCommand(Command):
    def __init__(self, session: OrgSession, commands: Provider[ServiceCommands], snapshots: Provider[OrgSnapshotter], out: Output) -> None:
        self._session = session
        self._commands = commands
        self._snapshots = snapshots
        self._out = out

    def add_arguments(self, sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
        raise NotImplementedError

    def run(self, args: Arguments) -> None:
        raise NotImplementedError


class RetireServiceCommand(Command):
    def __init__(self, session: OrgSession, commands: Provider[ServiceCommands], snapshots: Provider[OrgSnapshotter], out: Output) -> None:
        self._session = session
        self._commands = commands
        self._snapshots = snapshots
        self._out = out

    def add_arguments(self, sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
        raise NotImplementedError

    def run(self, args: Arguments) -> None:
        raise NotImplementedError
