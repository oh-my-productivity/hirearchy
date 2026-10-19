"""The commands that make, change or read the people and the mail of the organization: ``init hire task send inbox resume``."""

from __future__ import annotations

import argparse

from ..agents import AgentDirectory
from ..bootstrap import OrgInitializer
from ..dispatch import MessageSender, TaskAssigner
from ..eligibility import FailureCounter, PauseStore
from ..hierarchy import Hiring
from ..kernel import ROOT, Provider
from ..mail import BatchStore, MailboxReader
from ..snapshots import OrgSnapshotter
from ._ports import Arguments, Command, OrgSession, Output, TextSource


class InitCommand(Command):
    def __init__(self, session: OrgSession, initializer: Provider[OrgInitializer], text: TextSource, out: Output) -> None:
        self._session = session
        self._initializer = initializer
        self._text = text
        self._out = out

    def add_arguments(self, sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
        raise NotImplementedError

    def run(self, args: Arguments) -> None:
        raise NotImplementedError


class HireCommand(Command):
    def __init__(self, session: OrgSession, hiring: Provider[Hiring], snapshots: Provider[OrgSnapshotter], text: TextSource, out: Output) -> None:
        self._session = session
        self._hiring = hiring
        self._snapshots = snapshots
        self._text = text
        self._out = out

    def add_arguments(self, sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
        raise NotImplementedError

    def run(self, args: Arguments) -> None:
        raise NotImplementedError


class TaskCommand(Command):
    def __init__(self, session: OrgSession, tasks: Provider[TaskAssigner], snapshots: Provider[OrgSnapshotter], text: TextSource, out: Output) -> None:
        self._session = session
        self._tasks = tasks
        self._snapshots = snapshots
        self._text = text
        self._out = out

    def add_arguments(self, sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
        raise NotImplementedError

    def run(self, args: Arguments) -> None:
        raise NotImplementedError


class SendCommand(Command):
    def __init__(self, session: OrgSession, sender: Provider[MessageSender], snapshots: Provider[OrgSnapshotter], text: TextSource, out: Output) -> None:
        self._session = session
        self._sender = sender
        self._snapshots = snapshots
        self._text = text
        self._out = out

    def add_arguments(self, sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
        raise NotImplementedError

    def run(self, args: Arguments) -> None:
        raise NotImplementedError


class InboxCommand(Command):
    def __init__(self, session: OrgSession, mailbox: Provider[MailboxReader], batches: Provider[BatchStore], out: Output) -> None:
        self._session = session
        self._mailbox = mailbox
        self._batches = batches
        self._out = out

    def add_arguments(self, sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
        raise NotImplementedError

    def run(self, args: Arguments) -> None:
        raise NotImplementedError


class ResumeCommand(Command):
    def __init__(
        self, session: OrgSession, agents: Provider[AgentDirectory], pauses: Provider[PauseStore], failures: Provider[FailureCounter], out: Output,
    ) -> None:
        self._session = session
        self._agents = agents
        self._pauses = pauses
        self._failures = failures
        self._out = out

    def add_arguments(self, sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
        raise NotImplementedError

    def run(self, args: Arguments) -> None:
        raise NotImplementedError
