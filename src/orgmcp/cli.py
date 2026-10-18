"""Command line for the human (root) and the runtime."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from . import telemetry
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
        max_children=args.max_children, workspace=args.workspace, inputs=args.inputs or None,
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


def cmd_services(args) -> None:
    from . import services

    print(services.services_text(_org(args), ROOT))


def cmd_define_service(args) -> None:
    from .services import parse_input_spec

    org = _org(args, mutating=True)
    deliverable = {"description": args.deliverable, "format": args.format, "max_words": args.max_words, "path": args.path}
    given = {k: v for k, v in deliverable.items() if v}
    if given and "description" not in given:  # an amendment of single deliverable parts: the rest stays
        from .services import read_contract

        old = read_contract(org, org.norm(args.owner), args.name)
        if old is not None:
            given = {**old.deliverable, **given}
    text = org.define_service(
        ROOT, args.owner, args.name, description=args.description,
        inputs=[parse_input_spec(i) for i in args.input] if args.input is not None else None,
        acceptance=[_text(a) for a in args.acceptance] if args.acceptance is not None else None,
        deliverable=given or None, budget=args.budget, playbook=_text(args.playbook) if args.playbook else None,
        locked=args.locked, notes=_text(args.notes) if args.notes else None,
        add_acceptance=[_text(a) for a in args.add_acceptance] if args.add_acceptance is not None else None,
        remove_acceptance=[_text(a) for a in args.remove_acceptance] if args.remove_acceptance is not None else None,
    )
    org.commit(f"root: service {args.name} of {args.owner}")
    print(text)


def cmd_request(args) -> None:
    org = _org(args, mutating=True)
    inputs = {}
    for item in args.input or []:
        key, sep, value = item.partition("=")
        if not sep:
            raise OrgError(f"--input must be key=value (got {item!r})")
        inputs[key.strip()] = value
    msg = org.request(ROOT, args.service, inputs, title=args.title, note=args.note, budget=args.budget, revises=args.revises)
    org.commit(f"root: request {msg.id} -> {msg.to}")
    print(f"request {msg.id} -> {msg.to} (service {msg.service}, budget {msg.budget})")


def cmd_feedback(args) -> None:
    org = _org(args, mutating=True)
    msg = org.feedback(ROOT, args.task_id, args.verdict, args.note)
    org.commit(f"root: feedback {msg.id} -> {msg.to}")
    print(f"feedback {args.verdict} on {args.task_id} -> {msg.to}")


def cmd_retire_service(args) -> None:
    org = _org(args, mutating=True)
    print(org.retire_service(ROOT, args.owner, args.name, args.reason))
    org.commit(f"root: retired service {args.name} of {args.owner}")


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

    org = _org(args, mutating=True)  # says which organization it is about to change, before anything is written
    summary = blueprint.apply(org, blueprint.load(Path(args.blueprint)), allowed_roots=args.allow_root or None)
    print(summary.text())


def cmd_send(args) -> None:
    org = _org(args, mutating=True)
    msg = org.send(ROOT, args.to, _text(args.body), title=args.title, reply_to=args.reply_to, budget=args.budget)
    org.commit(f"root: note {msg.id} -> {msg.to}")
    print(f"sent {msg.id} -> {msg.to}")


def cmd_status(args) -> None:
    from .scheduler import describe_scheduler

    org = _org(args)
    print(org.tree())
    out = org.outstanding(ROOT)
    if out:
        print("\nyour outstanding tasks:")
        for t in out:
            print(f"  {t.id} \"{t.title}\" -> {t.to}")
    print(f"\n{describe_scheduler(org)}")


def cmd_health(args) -> None:
    from .health import org_health, render_text

    org = _org(args)
    report = org_health(org, args.agent or ROOT)
    print(json.dumps(report.to_dict(), indent=2) if args.json else render_text(report))


def cmd_progress(args) -> None:
    from .progress import describe_progress

    print(describe_progress(_org(args), args.task_id, args.wait))


def cmd_upgrade_rules(args) -> None:
    from .upgrade import upgrade_rules

    org = _org(args, mutating=not args.dry_run)
    print(upgrade_rules(org, dry_run=args.dry_run).text())


def cmd_install_skill(args) -> None:
    from .skill import install_skill

    print(install_skill(args.dest, force=args.force))


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
    if args.until_done and args.once:
        raise OrgError("--until-done and --once are different modes: use one of them")
    sched = Scheduler(org, kiro_runner(args.kiro))
    if args.once:
        sched.mode, sched.max_runs, sched.exit_reason = "once", args.max_runs, "once: one pass done"
        sched.acquire()
        try:
            sched.tick(max_runs=args.max_runs)
            while sched.runs:
                time.sleep(float(org.config["poll_seconds"]))
                sched._reap()
        finally:
            sched.release()
    else:
        sched.serve(until_idle=args.until_idle, max_runs=args.max_runs, until_done=args.until_done)


def cmd_mcp(args) -> None:
    from .server import serve

    serve()


def cmd_kiro_profile(args) -> None:
    from .scheduler import ensure_kiro_profile, mcp_server_command

    org = _org(args, mutating=True)  # the profile belongs to this organization
    name = ensure_kiro_profile([t for t in (args.tools or "").split(",") if t], org=org)
    print(f"wrote ~/.kiro/agents/{name}.json (mcp server: {json.dumps(mcp_server_command())})")


def _record_command(args, started: float, failure: BaseException | None) -> None:
    """Emit the ``cli.command`` event of a finished command. Never raises."""
    try:
        if args.cmd == "mcp":  # a long-lived server: it records its tool calls itself
            return
        root = Path(args.path if args.cmd == "init" else args.root or Org.find_root()).expanduser().resolve()
        error = None
        if failure is not None:
            error = str(failure) or type(failure).__name__
        telemetry.emit(
            root, "cli.command", proc="cli", actor=ROOT, command=args.cmd, ok=failure is None,
            ms=round((time.perf_counter() - started) * 1000, 2),
            error=telemetry.clip(error, telemetry.ERROR_MAX) if error else None,
            error_type=type(failure).__name__ if failure is not None else None,
        )
    except Exception:  # noqa: BLE001
        pass


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
    s.add_argument("--inputs", action="append", metavar="PATH",
                   help="absolute folder the agent may only read, never change (repeatable)")
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

    s = sub.add_parser("services", help="list the services you can request from your direct reports, with their record")
    s.set_defaults(fn=cmd_services)

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
    s.add_argument("--deliverable", help="what is handed back (a first definition needs it)")
    s.add_argument("--format")
    s.add_argument("--max-words", type=int)
    s.add_argument("--path", help="absolute folder for the deliverable")
    s.add_argument("--budget", type=int, help="runs handed down with each request (a first definition needs it)")
    s.add_argument("--playbook", metavar="@FILE", help="initial playbook (first definition only)")
    s.add_argument("--locked", action=argparse.BooleanOptionalAction, default=None,
                   help="--locked: the owner may not revise the playbook; --no-locked undoes it")
    s.add_argument("--notes", help="free text for the owner, or @file")
    s.set_defaults(fn=cmd_define_service)

    s = sub.add_parser("request", help="ask a top-level agent for one of its services (as root)")
    s.add_argument("service")
    s.add_argument("--input", action="append", metavar="KEY=VALUE", help="a value for an input of the service (repeatable)")
    s.add_argument("--title", default="")
    s.add_argument("--note", default="", help="free text for the owner")
    s.add_argument("--budget", type=int, help="runs handed down (default: the contract's)")
    s.add_argument("--revises", metavar="TASK_ID", help="send back an earlier request of this service for rework")
    s.set_defaults(fn=cmd_request)

    s = sub.add_parser("feedback", help="accept or reject a delivered service request (as root)")
    s.add_argument("task_id")
    s.add_argument("verdict", choices=["accept", "reject"])
    s.add_argument("--note", default="", help="what was wrong (required for reject)")
    s.set_defaults(fn=cmd_feedback)

    s = sub.add_parser("retire-service", help="take a service out of use (its files are kept)")
    s.add_argument("owner")
    s.add_argument("name")
    s.add_argument("--reason", required=True)
    s.set_defaults(fn=cmd_retire_service)

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
    s.add_argument("--wait", type=int, default=0, metavar="SECONDS",
                   help="first wait (up to 900) until a task finishes, fails, blocks or stalls, or something needs you")
    s.set_defaults(fn=cmd_progress)

    s = sub.add_parser("upgrade-rules", help="rewrite the rules in ORG.md to the current template (keeps settings and mission)")
    s.add_argument("--dry-run", action="store_true", help="print what would change; write nothing")
    s.set_defaults(fn=cmd_upgrade_rules)

    s = sub.add_parser("install-skill", help="copy the orgmcp assistant skill into a kiro skills directory (default ~/.kiro/skills)")
    s.add_argument("--dest", metavar="DIR", help="skills directory to install into; the file goes to DIR/orgmcp/SKILL.md (default: ~/.kiro/skills)")
    s.add_argument("--force", action="store_true", help="overwrite a different existing SKILL.md")
    s.set_defaults(fn=cmd_install_skill)

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
    s.add_argument("--until-done", action="store_true",
                   help="exit when root has no open task and nothing is running or runnable (logs why, shown by status/progress)")
    s.add_argument("--max-runs", type=int, help="stop starting runs after this many (safety cap)")
    s.add_argument("--kiro", default="kiro-cli", help="kiro-cli binary")
    s.set_defaults(fn=cmd_run)

    s = sub.add_parser("mcp", help="run the MCP server on stdio (identity from $ORG_AGENT, default root)")
    s.set_defaults(fn=cmd_mcp)

    from .cli_obs import register_obs

    register_obs(sub)  # obs now|trace|metrics|events, check

    s = sub.add_parser("kiro-profile", help="write this organization's internal kiro profile (the scheduler does this itself)")
    s.add_argument("--tools")
    s.set_defaults(fn=cmd_kiro_profile)

    args = p.parse_args(argv)
    telemetry.set_process("cli")
    started = time.perf_counter()
    try:
        args.fn(args)
    except OrgError as exc:
        _record_command(args, started, exc)
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(1)
    except SystemExit as exc:  # a command that exits by itself (e.g. plan with errors): a non-zero code is a failure
        _record_command(args, started, None if exc.code in (None, 0) else RuntimeError(f"exit {exc.code}"))
        raise
    except BaseException as exc:
        _record_command(args, started, exc)
        raise
    else:
        _record_command(args, started, None)
