"""Command line for the human (root) and the runtime."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from .core import ROOT, Org, OrgError


def _text(value: str) -> str:
    """Accept literal text or @path/to/file."""
    return Path(value[1:]).expanduser().read_text(encoding="utf-8") if value.startswith("@") else value


def _announce(path) -> None:
    """Say which organization a mutating command is about to change (stderr, so output stays clean)."""
    print(f"org: {Path(path).expanduser().resolve()}", file=sys.stderr, flush=True)


def _org(args, mutating: bool = False) -> Org:
    root = Path(args.root or Org.find_root()).expanduser().resolve()
    if mutating:
        _announce(root)  # before anything is read or written; also shown if the path turns out not to be an org
    return Org(root)


def cmd_init(args) -> None:
    cfg = {"default_model": args.model} if args.model else None
    _announce(args.path)
    org = Org.init(args.path, _text(args.mission) if args.mission else None, cfg)
    print(f"initialized organization at {org.root}\nedit {org.root / 'ORG.md'} to set the mission and limits")


def cmd_hire(args) -> None:
    org = _org(args, mutating=True)
    addr = org.hire(
        args.parent, args.name, args.role, _text(args.charter), model=args.model,
        tools=[t for t in (args.tools or "").split(",") if t], can_hire=args.can_hire,
        max_children=args.max_children, workspace=args.workspace,
    )
    org.commit(f"root: hired {addr}")
    print(f"hired {addr}")


def cmd_task(args) -> None:
    org = _org(args, mutating=True)
    msg = org.delegate(
        ROOT, args.to, args.title, _text(args.goal), _text(args.acceptance), args.input, args.budget, args.revises
    )
    org.commit(f"root: task {msg.id} -> {msg.to}")
    print(f"task {msg.id} -> {msg.to} (budget {msg.budget})")


def _bp_org(args) -> Org | None:
    try:
        return _org(args)
    except OrgError:
        return None


def cmd_plan(args) -> None:
    from . import blueprint

    org = _bp_org(args)
    bp = blueprint.load(Path(args.blueprint))
    issues = blueprint.validate(bp, org=org, allowed_roots=args.allow_root or None)
    print(blueprint.render_plan(bp, issues, org=org, allowed_roots=args.allow_root or None))
    if blueprint.errors(issues):
        sys.exit(1)


def cmd_apply(args) -> None:
    from . import blueprint

    org = _org(args)
    summary = blueprint.apply(org, blueprint.load(Path(args.blueprint)), allowed_roots=args.allow_root or None)
    print(f"org: {org.root}\n{summary.text()}")


def cmd_send(args) -> None:
    org = _org(args, mutating=True)
    msg = org.send(ROOT, args.to, _text(args.body), title=args.title, reply_to=args.reply_to, budget=args.budget)
    org.commit(f"root: note {msg.id} -> {msg.to}")
    print(f"sent {msg.id} -> {msg.to}")


def cmd_status(args) -> None:
    org = _org(args)
    print(org.tree())
    out = org.outstanding(ROOT)
    if out:
        print("\nyour outstanding tasks:")
        for t in out:
            print(f"  {t.id} \"{t.title}\" -> {t.to}")


def cmd_health(args) -> None:
    from .health import org_health, render_text

    org = _org(args)
    report = org_health(org, args.agent or ROOT)
    print(json.dumps(report.to_dict(), indent=2) if args.json else render_text(report))


def cmd_progress(args) -> None:
    from .progress import progress

    print(progress(_org(args), args.task_id))


def cmd_review(args) -> None:
    from .review import review

    org = _org(args, mutating=not args.dry_run)
    result = review(org, dry_run=args.dry_run)
    if result.notes and not args.dry_run:
        org.commit("root: health review")
    print(result.render(args.dry_run))


def cmd_inbox(args) -> None:
    org = _org(args, mutating=not args.keep)  # reading marks the mail as read
    batch = org.messages(ROOT, "inbox") if args.keep else org.begin_run(ROOT)
    if not args.keep:
        org.end_run(ROOT, ok=True)
    print("\n".join(m.render() for m in batch) or "(no new messages)")


def cmd_resume(args) -> None:
    org = _org(args, mutating=True)
    addr = org.require(args.agent)  # normalized: "ceo/" and "ceo" are the same agent
    org.resume(addr)
    org.clear_failures(addr)
    print(f"resumed {addr}")


def cmd_run(args) -> None:
    from .scheduler import Scheduler, kiro_runner

    org = _org(args, mutating=True)
    sched = Scheduler(org, kiro_runner(args.kiro))
    if args.once:
        sched.acquire()
        try:
            sched.tick(max_runs=args.max_runs)
            while sched.runs:
                time.sleep(float(org.config["poll_seconds"]))
                sched._reap()
        finally:
            sched.release()
    else:
        sched.serve(until_idle=args.until_idle, max_runs=args.max_runs)


def cmd_mcp(args) -> None:
    from .server import serve

    serve()


def cmd_kiro_profile(args) -> None:
    from .scheduler import ensure_kiro_profile, mcp_server_command

    org = _org(args, mutating=True)  # the profile belongs to this organization
    name = ensure_kiro_profile([t for t in (args.tools or "").split(",") if t], org=org)
    print(f"wrote ~/.kiro/agents/{name}.json (mcp server: {json.dumps(mcp_server_command())})")


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(prog="orgmcp", description="A file-based organization of agents, run over MCP.")
    p.add_argument("--root", help="organization directory (default: $ORG_ROOT or nearest dir with ORG.md)")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("init", help="create a new organization")
    s.add_argument("path", nargs="?", default="org")
    s.add_argument("--mission", help="mission text or @file")
    s.add_argument("--model", help="default kiro model for all agents")
    s.set_defaults(fn=cmd_init)

    s = sub.add_parser("hire", help="create an agent (as root)")
    s.add_argument("parent", help="'root' or an agent address")
    s.add_argument("name")
    s.add_argument("--role", required=True)
    s.add_argument("--charter", required=True, help="charter text or @file")
    s.add_argument("--model")
    s.add_argument("--tools", help="comma-separated kiro built-in tools, e.g. read,write,shell")
    s.add_argument("--can-hire", action="store_true")
    s.add_argument("--max-children", type=int, default=5)
    s.add_argument("--workspace")
    s.set_defaults(fn=cmd_hire)

    s = sub.add_parser("task", help="give a task to an agent (as root)")
    s.add_argument("to")
    s.add_argument("--title", required=True)
    s.add_argument("--goal", required=True, help="text or @file")
    s.add_argument("--acceptance", required=True, help="text or @file")
    s.add_argument("--input", action="append", default=[], help="path for the agent to read (repeatable)")
    s.add_argument("--budget", type=int)
    s.add_argument("--revises", metavar="TASK_ID", help="send back for rework: id of an earlier task sent to this agent")
    s.set_defaults(fn=cmd_task)

    s = sub.add_parser("plan", help="validate a blueprint and print the plan for approval (exit 1 on errors)")
    s.add_argument("blueprint", help="blueprint YAML/JSON file")
    s.add_argument("--allow-root", action="append", metavar="DIR", help="directory workspaces may be in (repeatable; default: home, temp, cwd)")
    s.set_defaults(fn=cmd_plan)

    s = sub.add_parser("apply", help="create the agents of a blueprint and give its first task (as root)")
    s.add_argument("blueprint", help="blueprint YAML/JSON file")
    s.add_argument("--allow-root", action="append", metavar="DIR", help="directory workspaces may be in (repeatable; default: home, temp, cwd)")
    s.set_defaults(fn=cmd_apply)

    s = sub.add_parser("send", help="send a note to an agent (as root)")
    s.add_argument("to")
    s.add_argument("body", help="text or @file")
    s.add_argument("--title", default="")
    s.add_argument("--reply-to")
    s.add_argument("--budget", type=int, default=0, help="grant extra runs")
    s.set_defaults(fn=cmd_send)

    s = sub.add_parser("status", help="show the organization tree")
    s.set_defaults(fn=cmd_status)

    s = sub.add_parser("health", help="show stuck, expensive, low-quality and idle agents and branches")
    s.add_argument("--agent", metavar="ADDR", help="only this agent and its subtree (default: whole organization)")
    s.add_argument("--json", action="store_true", help="print the structured data")
    s.set_defaults(fn=cmd_health)

    s = sub.add_parser("progress", help="one line per task you gave: state, who is busy, cost, last activity; what needs you")
    s.add_argument("task_id", nargs="?", help="only this task (default: open tasks and those finished in the last day)")
    s.set_defaults(fn=cmd_progress)

    s = sub.add_parser("review", help="run a health review now: tell managers (and you) about flagged agents")
    s.add_argument("--dry-run", action="store_true", help="print what would be sent; write nothing")
    s.set_defaults(fn=cmd_review)

    s = sub.add_parser("inbox", help="read your (root) messages")
    s.add_argument("--keep", action="store_true", help="do not mark as read")
    s.set_defaults(fn=cmd_inbox)

    s = sub.add_parser("resume", help="unpause an agent")
    s.add_argument("agent")
    s.set_defaults(fn=cmd_resume)

    s = sub.add_parser("run", help="run the scheduler")
    s.add_argument("--once", action="store_true", help="one pass, wait for those runs, exit")
    s.add_argument("--until-idle", action="store_true", help="exit when nothing is left to do")
    s.add_argument("--max-runs", type=int, help="stop starting runs after this many (safety cap)")
    s.add_argument("--kiro", default="kiro-cli", help="kiro-cli binary")
    s.set_defaults(fn=cmd_run)

    s = sub.add_parser("mcp", help="run the MCP server on stdio (identity from $ORG_AGENT, default root)")
    s.set_defaults(fn=cmd_mcp)

    s = sub.add_parser("kiro-profile", help="write this organization's internal kiro profile (the scheduler does this itself)")
    s.add_argument("--tools")
    s.set_defaults(fn=cmd_kiro_profile)

    args = p.parse_args(argv)
    try:
        args.fn(args)
    except OrgError as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(1)
