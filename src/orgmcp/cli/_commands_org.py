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
        s = sub.add_parser("init", help="create a new organization")
        s.add_argument("path", nargs="?", default="org")
        s.add_argument("--mission", help="mission text or @file")
        s.add_argument("--model", help="default kiro model for all agents (default: claude-sonnet-5.5)")
        s.set_defaults(fn=self.run)

    def run(self, args: Arguments) -> None:
        cfg = {"default_model": args.model} if args.model else None
        root = self._session.create(args.path)
        self._initializer().init(root, self._text.read(args.mission) if args.mission else None, cfg)
        self._out.say(f"initialized organization at {root}\nedit {root / 'ORG.md'} to set the mission and limits")


class HireCommand(Command):
    def __init__(self, session: OrgSession, hiring: Provider[Hiring], snapshots: Provider[OrgSnapshotter], text: TextSource, out: Output) -> None:
        self._session = session
        self._hiring = hiring
        self._snapshots = snapshots
        self._text = text
        self._out = out

    def add_arguments(self, sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
        s = sub.add_parser("hire", help="create an agent (as root)")
        s.add_argument("parent", help="'root' or an agent address")
        s.add_argument("name")
        s.add_argument("--role", required=True)
        s.add_argument("--charter", required=True, help="charter text or @file")
        s.add_argument("--model", help="kiro model for this agent (default: the org's default model, claude-sonnet-5.5)")
        s.add_argument("--tools", help="comma-separated kiro built-in tools, e.g. read,write,shell")
        s.add_argument("--can-hire", action="store_true")
        s.add_argument("--max-children", type=int, default=5)
        s.add_argument("--workspace")
        s.add_argument("--inputs", action="append", metavar="PATH",
                       help="absolute folder the agent may only read, never change (repeatable)")
        s.set_defaults(fn=self.run)

    def run(self, args: Arguments) -> None:
        self._session.open(args, mutating=True)
        addr = self._hiring().hire(
            args.parent, args.name, args.role, self._text.read(args.charter), model=args.model,
            tools=[t for t in (args.tools or "").split(",") if t], can_hire=args.can_hire,
            max_children=args.max_children, workspace=args.workspace, inputs=args.inputs or None,
        )
        self._snapshots().commit(f"root: hired {addr}")
        self._out.say(f"hired {addr}")


class TaskCommand(Command):
    def __init__(self, session: OrgSession, tasks: Provider[TaskAssigner], snapshots: Provider[OrgSnapshotter], text: TextSource, out: Output) -> None:
        self._session = session
        self._tasks = tasks
        self._snapshots = snapshots
        self._text = text
        self._out = out

    def add_arguments(self, sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
        s = sub.add_parser("task", help="give a task to an agent (as root)")
        s.add_argument("to")
        s.add_argument("--title", required=True)
        s.add_argument("--goal", required=True, help="text or @file")
        s.add_argument("--acceptance", required=True, help="text or @file")
        s.add_argument("--input", action="append", default=[], help="path for the agent to read (repeatable)")
        s.add_argument("--budget", type=int)
        s.add_argument("--revises", metavar="TASK_ID", help="send back for rework: id of an earlier task sent to this agent")
        s.set_defaults(fn=self.run)

    def run(self, args: Arguments) -> None:
        self._session.open(args, mutating=True)
        msg = self._tasks().delegate(
            ROOT, args.to, args.title, self._text.read(args.goal), self._text.read(args.acceptance), args.input, args.budget, args.revises
        )
        self._snapshots().commit(f"root: task {msg.id} -> {msg.to}")
        self._out.say(f"task {msg.id} -> {msg.to} (budget {msg.budget})")


class SendCommand(Command):
    def __init__(self, session: OrgSession, sender: Provider[MessageSender], snapshots: Provider[OrgSnapshotter], text: TextSource, out: Output) -> None:
        self._session = session
        self._sender = sender
        self._snapshots = snapshots
        self._text = text
        self._out = out

    def add_arguments(self, sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
        s = sub.add_parser("send", help="send a note to an agent (as root)")
        s.add_argument("to")
        s.add_argument("body", help="text or @file")
        s.add_argument("--title", default="")
        s.add_argument("--reply-to")
        s.add_argument("--budget", type=int, default=0, help="grant extra runs")
        s.set_defaults(fn=self.run)

    def run(self, args: Arguments) -> None:
        self._session.open(args, mutating=True)
        msg = self._sender().send(ROOT, args.to, self._text.read(args.body), title=args.title, reply_to=args.reply_to, budget=args.budget)
        self._snapshots().commit(f"root: note {msg.id} -> {msg.to}")
        self._out.say(f"sent {msg.id} -> {msg.to}")


class InboxCommand(Command):
    def __init__(self, session: OrgSession, mailbox: Provider[MailboxReader], batches: Provider[BatchStore], out: Output) -> None:
        self._session = session
        self._mailbox = mailbox
        self._batches = batches
        self._out = out

    def add_arguments(self, sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
        s = sub.add_parser("inbox", help="read your (root) messages")
        s.add_argument("--keep", action="store_true", help="do not mark as read")
        s.set_defaults(fn=self.run)

    def run(self, args: Arguments) -> None:
        self._session.open(args, mutating=not args.keep)  # reading marks the mail as read
        batch = self._mailbox().messages(ROOT, "inbox") if args.keep else self._batches().begin(ROOT)
        if not args.keep:
            self._batches().end(ROOT, True)
        self._out.say("\n".join(m.render() for m in batch) or "(no new messages)")


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
        s = sub.add_parser("resume", help="unpause an agent")
        s.add_argument("agent")
        s.set_defaults(fn=self.run)

    def run(self, args: Arguments) -> None:
        self._session.open(args, mutating=True)
        addr = self._agents().require(args.agent)  # normalized: "ceo/" and "ceo" are the same agent
        self._pauses().resume(addr)
        self._failures().clear(addr)
        self._out.say(f"resumed {addr}")
