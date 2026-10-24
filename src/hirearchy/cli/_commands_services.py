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
        s = sub.add_parser("services", help="list the services you can request from your direct reports, with their record")
        s.set_defaults(fn=self.run)

    def run(self, args: Arguments) -> None:
        self._session.open(args)
        self._out.say(self._reports().services_text(ROOT))


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
        s = sub.add_parser("define-service", help="define a standing service of a top-level agent, or amend its contract (as root): "
                           "on an existing service pass only what changes")
        s.add_argument("owner", help="the top-level agent that offers the service")
        s.add_argument("name", help="lowercase-dashed service name")
        s.add_argument("--description", help="one line: what the service delivers (a first definition needs it)")
        s.add_argument("--input", action="append", metavar="'name*:description'",
                       help="an input of a request; a trailing * on the name = required (repeatable)")
        s.add_argument("--acceptance", action="append", metavar="TEXT|@FILE",
                       help="a criterion, or @file with one criterion per line (repeatable); replaces all existing ones")
        s.add_argument("--add-acceptance", action="append", metavar="TEXT|@FILE",
                       help="amendment: add a criterion (repeatable); not with --acceptance")
        s.add_argument("--remove-acceptance", action="append", metavar="TEXT|@FILE",
                       help="amendment: drop a criterion, by its exact text (repeatable); not with --acceptance")
        s.add_argument("--answers", metavar="VERDICT_ID",
                       help="amendment of the criteria: the rejection the user's answer is about (its message id)")
        s.add_argument("--about", metavar="ID", help="the C or R id your question named")
        s.add_argument("--words", metavar="TEXT|@FILE",
                       help="the user's words, verbatim (their answer; alone: a change they asked for on their own)")
        s.add_argument("--deliverable", help="what is handed back (a first definition needs it)")
        s.add_argument("--format")
        s.add_argument("--max-words", type=int)
        s.add_argument("--path", help="absolute folder for the deliverable")
        s.add_argument("--budget", type=int, help="runs handed down with each request (a first definition needs it)")
        s.add_argument("--playbook", metavar="@FILE", help="initial playbook (first definition only)")
        s.add_argument("--locked", action=argparse.BooleanOptionalAction, default=None,
                       help="--locked: the owner may not revise the playbook; --no-locked undoes it")
        s.add_argument("--notes", help="free text for the owner, or @file")
        s.set_defaults(fn=self.run)

    def run(self, args: Arguments) -> None:
        self._session.open(args, mutating=True)
        read = self._text.read
        deliverable = {"description": args.deliverable, "format": args.format, "max_words": args.max_words, "path": args.path}
        given = {k: v for k, v in deliverable.items() if v}
        if given and "description" not in given:  # an amendment of single deliverable parts: the rest stays
            old = self._catalog().read_contract(norm(args.owner), args.name)
            if old is not None:
                given = {**old.deliverable, **given}
        text = self._commands().define_service(
            ROOT, args.owner, args.name, description=args.description,
            inputs=[self._contracts().parse_input_spec(i) for i in args.input] if args.input is not None else None,
            acceptance=[read(a) for a in args.acceptance] if args.acceptance is not None else None,
            deliverable=given or None, budget=args.budget, playbook=read(args.playbook) if args.playbook else None,
            locked=args.locked, notes=read(args.notes) if args.notes else None,
            add_acceptance=[read(a) for a in args.add_acceptance] if args.add_acceptance is not None else None,
            remove_acceptance=[read(a) for a in args.remove_acceptance] if args.remove_acceptance is not None else None,
            answers=args.answers, about=args.about, words=read(args.words) if args.words is not None else None,
        )
        self._snapshots().commit(f"root: service {args.name} of {args.owner}")
        self._out.say(text)


class RequestCommand(Command):
    def __init__(self, session: OrgSession, commands: Provider[ServiceCommands], snapshots: Provider[OrgSnapshotter], out: Output) -> None:
        self._session = session
        self._commands = commands
        self._snapshots = snapshots
        self._out = out

    def add_arguments(self, sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
        s = sub.add_parser("request", help="ask a top-level agent for one of its services (as root)")
        s.add_argument("service")
        s.add_argument("--input", action="append", metavar="KEY=VALUE", help="a value for an input of the service (repeatable)")
        s.add_argument("--title", default="")
        s.add_argument("--note", default="", help="free text for the owner")
        s.add_argument(
            "--budget", type=int,
            help="runs handed down (default: the contract's; for a rework you asked for, what is left of the runs you approved for the case, at most the "
                 "contract's, 1 when none is left)",
        )
        s.add_argument("--revises", metavar="TASK_ID", help="send back an earlier request of this service for rework")
        s.add_argument("--source", choices=("human", "relayed"), help="who asked for a rework (--revises): human (you, the default) or relayed")
        s.add_argument("--base", choices=("delivered", "latest"), help="which version a rework you asked for starts from, when the team's own rework changed the "
                                                                        "delivery you judged: delivered (what you judged) or latest")
        s.set_defaults(fn=self.run)

    def run(self, args: Arguments) -> None:
        self._session.open(args, mutating=True)
        inputs = {}
        for item in args.input or []:
            key, sep, value = item.partition("=")
            if not sep:
                raise OrgError(f"--input must be key=value (got {item!r})")
            inputs[key.strip()] = value
        source = args.source or ("human" if args.revises else None)  # the human typed it; a fresh request is not stamped
        msg = self._commands().request(ROOT, args.service, inputs, title=args.title, note=args.note, budget=args.budget, revises=args.revises,
                                       source=source, base=args.base)
        self._snapshots().commit(f"root: request {msg.id} -> {msg.to}")
        based = f", base {args.base}" if args.base else ""
        self._out.say(f"request {msg.id} -> {msg.to} (service {msg.service}, budget {msg.budget}{based})")


class FeedbackCommand(Command):
    def __init__(self, session: OrgSession, commands: Provider[ServiceCommands], snapshots: Provider[OrgSnapshotter], out: Output) -> None:
        self._session = session
        self._commands = commands
        self._snapshots = snapshots
        self._out = out

    def add_arguments(self, sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
        s = sub.add_parser("feedback", help="accept or reject a delivered service request (as root)")
        s.add_argument("task_id")
        s.add_argument("verdict", choices=["accept", "reject"])
        s.add_argument("--note", default="", help="what was wrong (required for reject)")
        s.add_argument("--source", choices=("human", "relayed"), default="human",
                       help="human (default): your own judgement; relayed: someone else's reading of the delivery")
        s.add_argument("--criterion", action="append", metavar="ID",
                       help="what a rejection was about: C<k> (a contract criterion), R<k> (an earlier rejection it repeats) or none (no lasting rule) "
                       "(an answer that changes no criterion)")
        s.add_argument("--confirms", metavar="VERDICT_ID",
                       help="record --criterion for an earlier rejection (its message id) instead of a new verdict; --note is your answer")
        s.set_defaults(fn=self.run)

    def run(self, args: Arguments) -> None:
        self._session.open(args, mutating=True)
        msg = self._commands().feedback(
            ROOT, args.task_id, args.verdict, args.note, source=args.source, criterion=args.criterion, confirms=args.confirms,
        )
        self._snapshots().commit(f"root: feedback {msg.id} -> {msg.to}")
        if args.confirms:
            self._out.say(f"link on {args.confirms} -> {msg.to}: {msg.criterion} (message {msg.id}, source {msg.source})")
            return
        about = f", about {msg.criterion}" if msg.criterion else ""
        self._out.say(f"feedback {args.verdict} on {args.task_id} -> {msg.to} (message {msg.id}, source {msg.source}{about})")
        if args.verdict == "reject" and args.criterion and args.source == "human":
            # The terminal is the user's own seat, so the criterion they typed is their yes: it is recorded as a `confirms` link (a criterion on
            # the verdict itself is the assistant's reading). The verdict is already written and committed; if this call fails, the error follows.
            link = self._commands().feedback(
                ROOT, args.task_id, "reject", args.note, source="human", criterion=args.criterion, confirms=msg.id,
            )
            self._snapshots().commit(f"root: feedback {link.id} -> {link.to}")
            self._out.say(f"link on {msg.id} -> {link.to}: {link.criterion} (message {link.id}, source {link.source})")


class RetireServiceCommand(Command):
    def __init__(self, session: OrgSession, commands: Provider[ServiceCommands], snapshots: Provider[OrgSnapshotter], out: Output) -> None:
        self._session = session
        self._commands = commands
        self._snapshots = snapshots
        self._out = out

    def add_arguments(self, sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
        s = sub.add_parser("retire-service", help="take a service out of use (its files are kept)")
        s.add_argument("owner")
        s.add_argument("name")
        s.add_argument("--reason", required=True)
        s.set_defaults(fn=self.run)

    def run(self, args: Arguments) -> None:
        self._session.open(args, mutating=True)
        self._out.say(self._commands().retire_service(ROOT, args.owner, args.name, args.reason))
        self._snapshots().commit(f"root: retired service {args.name} of {args.owner}")
