"""``orgmcp obs now|trace|metrics|events`` and ``orgmcp check``: the command line of the read-only views of the observability."""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from typing import cast

from ..kernel import Clock, JsonObject, Provider
from ..observability import EventQueries, IntegrityChecks, MetricQueries, NowQueries, ObservabilityRenderer, TraceQueries, format_event
from ._ports import Arguments, Command, EventTails, JsonDump, OrgSession, Output, Terminal


class NowCommand(Command):
    def __init__(
        self, session: OrgSession, queries: Provider[NowQueries], renderer: Provider[ObservabilityRenderer], dump: JsonDump, terminal: Terminal,
        clock: Clock, out: Output,
    ) -> None:
        self._session = session
        self._queries = queries
        self._renderer = renderer
        self._dump = dump
        self._terminal = terminal
        self._clock = clock
        self._out = out

    def add_arguments(self, sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
        v = sub.add_parser("now", help="what is happening right now: scheduler, runs, queue, what waits on you, recent errors")
        v.add_argument("--watch", type=float, metavar="SECONDS", help="repeat every SECONDS until Ctrl-C")
        v.add_argument("--json", action="store_true")
        v.set_defaults(fn=self.run)

    def run(self, args: Arguments) -> None:
        self._session.open(args)
        while True:
            view = self._queries().now_view()
            if args.json:
                self._out.say(self._dump.dump(view))
            else:
                if args.watch and self._terminal.stdout_is_tty():
                    self._out.write("\033[2J\033[H")
                self._out.say(self._renderer().render_now(view))
            if not args.watch:
                return
            try:
                self._clock.sleep(args.watch)
            except KeyboardInterrupt:
                return
            if not self._terminal.stdout_is_tty() and not args.json:
                self._out.say("-" * 40)


class TraceCommand(Command):
    def __init__(self, session: OrgSession, traces: Provider[TraceQueries], renderer: Provider[ObservabilityRenderer], dump: JsonDump, out: Output) -> None:
        self._session = session
        self._traces = traces
        self._renderer = renderer
        self._dump = dump
        self._out = out

    def add_arguments(self, sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
        v = sub.add_parser("trace", help="one request (a root task) as a tree of messages, runs, tool calls and refusals, with totals")
        v.add_argument("task_id")
        v.add_argument("--json", action="store_true")
        v.set_defaults(fn=self.run)

    def run(self, args: Arguments) -> None:
        self._session.open(args)
        tr = self._traces().trace(args.task_id)
        self._out.say(self._dump.dump(tr) if args.json else self._renderer().render_trace(tr))


class MetricsCommand(Command):
    def __init__(self, session: OrgSession, metrics: Provider[MetricQueries], renderer: Provider[ObservabilityRenderer], dump: JsonDump, out: Output) -> None:
        self._session = session
        self._metrics = metrics
        self._renderer = renderer
        self._dump = dump
        self._out = out

    def add_arguments(self, sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
        v = sub.add_parser("metrics", help="runs, failures, refusals and latency percentiles over a time window")
        v.add_argument("--since", default="24h", help="15m, 24h, 7d or an ISO timestamp (default 24h)")
        v.add_argument("--by", choices=["agent", "tool", "service", "trace"], help="also group by this")
        v.add_argument("--agent", metavar="ADDR", help="only this agent")
        v.add_argument("--limit", type=int, default=50, help="rows shown per table")
        v.add_argument("--json", action="store_true")
        v.set_defaults(fn=self.run)

    def run(self, args: Arguments) -> None:
        self._session.open(args)
        m = self._metrics().metrics(args.since, args.by, agent=args.agent)
        self._out.say(self._dump.dump(m) if args.json else self._renderer().render_metrics(m, args.limit))


class EventsCommand(Command):
    def __init__(
        self, session: OrgSession, events: Provider[EventQueries], renderer: Provider[ObservabilityRenderer], tails: Provider[EventTails], dump: JsonDump,
        clock: Clock, out: Output,
    ) -> None:
        self._session = session
        self._events = events
        self._renderer = renderer
        self._tails = tails
        self._dump = dump
        self._clock = clock
        self._out = out

    def add_arguments(self, sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
        v = sub.add_parser("events", help="the merged raw event stream, filtered")
        v.add_argument("--since", default="24h", help="15m, 24h, 7d or an ISO timestamp (default 24h)")
        v.add_argument("--until")
        v.add_argument("--agent", metavar="ADDR")
        v.add_argument("--kind", help="an event kind or a prefix: tool.call, run, scheduler")
        v.add_argument("--trace", metavar="TASK_ID")
        v.add_argument("--errors", action="store_true", help="only refusals, failures, faults")
        v.add_argument("--limit", type=int, default=50, help="show the last N matching events")
        v.add_argument("--follow", action="store_true", help="keep printing new events until Ctrl-C")
        v.add_argument("--poll", type=float, default=0.5, help="seconds between looks when following")
        v.add_argument("--json", action="store_true", help="one JSON object per line")
        v.set_defaults(fn=self.run)

    def run(self, args: Arguments) -> None:
        self._session.open(args)
        tails = self._tails()
        follower = tails.follow(args.agent, args.kind, args.trace, args.errors) if args.follow else None  # before the listing: no gap
        view = self._events().events_view(
            args.since, args.until, args.agent, args.kind, args.trace, args.errors, args.limit,
        )
        view["any"] = tails.any()
        if args.json:
            for ev in cast("list[JsonObject]", view["events"]):
                self._out.say(json.dumps(ev, default=str))
        else:
            self._out.say(self._renderer().render_events(view))
        if follower is None:
            return
        try:
            while True:
                self._clock.sleep(args.poll)
                for ev in follower.poll():
                    self._out.say(json.dumps(ev, default=str) if args.json else format_event(ev), flush=True)
        except KeyboardInterrupt:
            return


class ObsCommand(Command):
    """``obs``: the views of the observability, each a command of its own."""

    def __init__(self, views: Sequence[Command]) -> None:
        self._views = list(views)

    def add_arguments(self, sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
        s = sub.add_parser("obs", help="read-only views of how the organization runs: now, trace, metrics, events")
        views = s.add_subparsers(dest="obs_cmd", required=True)
        for view in self._views:
            view.add_arguments(views)

    def run(self, args: Arguments) -> None:
        args.fn(args)


class CheckCommand(Command):
    def __init__(self, session: OrgSession, checks: Provider[IntegrityChecks], renderer: Provider[ObservabilityRenderer], dump: JsonDump, out: Output) -> None:
        self._session = session
        self._checks = checks
        self._renderer = renderer
        self._dump = dump
        self._out = out

    def add_arguments(self, sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
        s = sub.add_parser("check", help="invariants of the runtime: messages intact, budget conserved, nothing stuck (exit 1 on FAIL)")
        s.add_argument("--json", action="store_true")
        s.set_defaults(fn=self.run)

    def run(self, args: Arguments) -> None:
        self._session.open(args)
        res = self._checks().check()
        self._out.say(self._dump.dump(res) if args.json else self._renderer().render_check(res))
        if not res["ok"]:
            raise SystemExit(1)
