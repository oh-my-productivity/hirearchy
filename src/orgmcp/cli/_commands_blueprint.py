"""The commands of the blueprints: ``plan`` (read-only) and ``apply``."""

from __future__ import annotations

import argparse
from pathlib import Path

from ..blueprint import BlueprintApplier, BlueprintLoader, BlueprintValidator, PlanRenderer, errors
from ..kernel import Provider
from ._ports import Arguments, Command, OrgSession, Output


class PlanCommand(Command):
    """Validates a blueprint and prints the plan for approval: against the organization if there is one, else against the defaults of a new one."""

    def __init__(
        self, session: OrgSession, loader: Provider[BlueprintLoader], validator: Provider[BlueprintValidator], renderer: Provider[PlanRenderer],
        out: Output,
    ) -> None:
        self._session = session
        self._loader = loader
        self._validator = validator
        self._renderer = renderer
        self._out = out

    def add_arguments(self, sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
        s = sub.add_parser("plan", help="validate a blueprint and print the plan for approval (exit 1 on errors)")
        s.add_argument("blueprint", help="blueprint YAML/JSON file")
        s.add_argument("--allow-root", action="append", metavar="DIR", help="directory workspaces may be in (repeatable; default: home, temp, cwd)")
        s.set_defaults(fn=self.run)

    def run(self, args: Arguments) -> None:
        exists = self._session.present(args)
        bp = self._loader().load(Path(args.blueprint))
        issues = self._validator().validate(bp, org_exists=exists, allowed_roots=args.allow_root or None)
        self._out.say(self._renderer().render_plan(bp, issues, allowed_roots=args.allow_root or None))
        if errors(issues):
            raise SystemExit(1)


class ApplyCommand(Command):
    def __init__(self, session: OrgSession, loader: Provider[BlueprintLoader], applier: Provider[BlueprintApplier], out: Output) -> None:
        self._session = session
        self._loader = loader
        self._applier = applier
        self._out = out

    def add_arguments(self, sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
        s = sub.add_parser("apply", help="create the agents of a blueprint and give its first task (as root)")
        s.add_argument("blueprint", help="blueprint YAML/JSON file")
        s.add_argument("--allow-root", action="append", metavar="DIR", help="directory workspaces may be in (repeatable; default: home, temp, cwd)")
        s.set_defaults(fn=self.run)

    def run(self, args: Arguments) -> None:
        self._session.open(args, mutating=True)  # says which organization it is about to change, before anything is written
        summary = self._applier().apply(self._loader().load(Path(args.blueprint)), allowed_roots=args.allow_root or None)
        self._out.say(summary.text())
