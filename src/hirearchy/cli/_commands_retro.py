"""``retro``: the retro brief at the terminal (design 4.7): ``hirearchy retro [--since DATE|DATETIME|MESSAGE_ID] [--json]``."""

from __future__ import annotations

import argparse
import json

from ..kernel import OrgError, Provider
from ..retro import RetroBriefs, brief_json, parse_since, render_brief
from ._ports import Arguments, Command, OrgSession, Output


class RetroCommand(Command):
    def __init__(self, session: OrgSession, briefs: Provider[RetroBriefs], out: Output) -> None:
        self._session = session
        self._briefs = briefs
        self._out = out

    def add_arguments(self, sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
        s = sub.add_parser("retro", help="the retro brief: what the client said, what got past a check, whether past changes held, how the organization changed, and at most 3 yes/no items")
        s.add_argument("--since", metavar="DATE|DATETIME|MESSAGE_ID", help="a look-back over that window (recorded nowhere); a date is local midnight, a datetime needs its offset")
        s.add_argument("--json", action="store_true", help="the same brief as JSON: every section and every count with its N")
        s.set_defaults(fn=self.run)

    def run(self, args: Arguments) -> None:
        try:
            when = parse_since(args.since) if args.since else None
        except OrgError as exc:
            self._out.warn(str(exc))
            raise SystemExit(2)
        self._session.open(args)
        brief = self._briefs().brief(since=when)
        self._out.say(json.dumps(brief_json(brief), indent=2) if args.json else render_brief(brief))
