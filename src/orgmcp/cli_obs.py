"""``orgmcp obs now|trace|metrics|events`` and ``orgmcp check``: the command line for the read-only views of
:mod:`orgmcp.observe`. ``register_obs(sub)`` is the only thing ``cli.main`` calls."""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

from . import observe
from .core import Org


def _org(args) -> Org:
    return Org(Path(args.root or Org.find_root()).expanduser().resolve())


def _dump(data) -> str:
    return json.dumps(observe._plain(data), indent=2, default=str)


def cmd_now(args) -> None:
    org = _org(args)
    while True:
        view = observe.now_view(org)
        if args.json:
            print(_dump(view))
        else:
            if args.watch and sys.stdout.isatty():
                print("\033[2J\033[H", end="")
            print(observe.render_now(view))
        if not args.watch:
            return
        try:
            time.sleep(args.watch)
        except KeyboardInterrupt:
            return
        if not sys.stdout.isatty() and not args.json:
            print("-" * 40)


def cmd_trace(args) -> None:
    tr = observe.trace(_org(args), args.task_id)
    print(_dump(tr) if args.json else observe.render_trace(tr))


def cmd_metrics(args) -> None:
    m = observe.metrics(_org(args), args.since, args.by, agent=args.agent)
    print(_dump(m) if args.json else observe.render_metrics(m, args.limit))


def cmd_events(args) -> None:
    org = _org(args)
    kw = dict(agent=args.agent, kind=args.kind, trace=args.trace, errors=args.errors)
    follower = observe.Follower(org, observe._matcher(**kw)) if args.follow else None  # before the listing: no gap
    view = observe.events_view(org, args.since, args.until, limit=args.limit, **kw)
    view["any"] = bool(observe.event_files(org))
    if args.json:
        for ev in view["events"]:
            print(json.dumps(ev, default=str))
    else:
        print(observe.render_events(view))
    if follower is None:
        return
    try:
        while True:
            time.sleep(args.poll)
            for ev in follower.poll():
                print(json.dumps(ev, default=str) if args.json else observe.format_event(ev), flush=True)
    except KeyboardInterrupt:
        return


def cmd_check(args) -> None:
    res = observe.check(_org(args))
    print(_dump(res) if args.json else observe.render_check(res))
    if not res["ok"]:
        sys.exit(1)


def register_obs(sub) -> None:
    """Add ``obs {now,trace,metrics,events}`` and ``check`` to the top-level subparsers."""
    s = sub.add_parser("obs", help="read-only views of how the organization runs: now, trace, metrics, events")
    views = s.add_subparsers(dest="obs_cmd", required=True)

    v = views.add_parser("now", help="what is happening right now: scheduler, runs, queue, what waits on you, recent errors")
    v.add_argument("--watch", type=float, metavar="SECONDS", help="repeat every SECONDS until Ctrl-C")
    v.add_argument("--json", action="store_true")
    v.set_defaults(fn=cmd_now)

    v = views.add_parser("trace", help="one request (a root task) as a tree of messages, runs, tool calls and refusals, with totals")
    v.add_argument("task_id")
    v.add_argument("--json", action="store_true")
    v.set_defaults(fn=cmd_trace)

    v = views.add_parser("metrics", help="runs, failures, refusals and latency percentiles over a time window")
    v.add_argument("--since", default="24h", help="15m, 24h, 7d or an ISO timestamp (default 24h)")
    v.add_argument("--by", choices=["agent", "tool", "service", "trace"], help="also group by this")
    v.add_argument("--agent", metavar="ADDR", help="only this agent")
    v.add_argument("--limit", type=int, default=50, help="rows shown per table")
    v.add_argument("--json", action="store_true")
    v.set_defaults(fn=cmd_metrics)

    v = views.add_parser("events", help="the merged raw event stream, filtered")
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
    v.set_defaults(fn=cmd_events)

    s = sub.add_parser("check", help="invariants of the runtime: messages intact, budget conserved, nothing stuck (exit 1 on FAIL)")
    s.add_argument("--json", action="store_true")
    s.set_defaults(fn=cmd_check)
