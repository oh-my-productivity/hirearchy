#!/usr/bin/env python3
"""E5 clause-1 trigger: the facilitator's injected wrong rework of memo 1 (protocol.md section 5).

Run with:  uv --directory /Volumes/workspace/hirearchy run python <this file> --org S/org --revises <memo-1 task id> --out S/injection
Other modes:
  --dry-run    verify the text md5s, parse the revised task, print the request arguments; no server, no org write
  --selftest   start the server (root binding), initialize and list tools only; makes no tool call
  --stop       stream end only (protocol 4.8): call stop() once; nothing else
  --poll-check preflight only (protocol 4.14): run the step-4 polling loop alone, progress(task_id=--task, wait_seconds) and nothing
               else, for at most --max-seconds; log to <out>/poll-check-log.txt; no request, no start, no org write

It is an MCP stdio client of the SAME server command the assistant profile uses (`uv --directory <repo> run hirearchy mcp`,
ORG_ROOT=<org>; ORG_AGENT and ORG_REQUIRE_AGENT removed, so the server binds as root). No LLM is involved.
Exactly these calls, in this order: progress(); request(...); start(); progress(task_id, wait_seconds=300) repeated; progress(); status().
It never calls inbox, feedback, define_service, send, delegate, reclaim, services, whoami (stop only with --stop).
The title and note are read at run time from E2's sent file and their md5s are asserted before anything is sent.
F-E4-9 fix (E5): progress(task_id, wait_seconds) returns at once when nothing can progress ("Not waiting: ..."), and E4's loop then
re-polled without delay (36,513 calls in s2). The loop now pauses after every reply that came back without waiting (5 s, doubling up
to 60 s; reset after a reply that waited), stops at 20 minutes from the request as before or after MAX_POLLS polls, and logs every
poll and the poll count. The calls, their arguments and the end condition are unchanged.
Exit codes: 0 done; 2 text/identity assertion or argument error (nothing sent); 3 precondition not met (scheduler running; nothing sent,
rerun with --force after the facilitator's wait); 4 refused or failed request (nothing recorded); 5 failure after the request was sent.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO = "/Volumes/workspace/hirearchy/.worktrees/p2-arm-c"
E2_FILE = Path(REPO) / "studies/E2-service-reflection-regression/evidence/msgs/root-sent/20261018T035429740646-root-d90e.md"
TITLE_MD5 = "849fe21b104be883af9b3c06367d4445"
NOTE_MD5 = "4cdbcb9b682f2f25dcb31c83d3743fec"
NOTE_LEN = 866
BUDGET = 6
SOURCE = "relayed"
NOTE_HEADING = "## Note from the requester"
WAIT_STEP = 300          # seconds per progress() wait
WINDOW_MAX = 20 * 60     # seconds from the request
# F-E4-9 fix (E5): pacing of the step-4 loop when progress(wait_seconds) does not wait.
QUICK_REPLY = 5.0        # a progress reply faster than this (seconds) did not wait
PAUSE_START = 5.0        # the pause after the first quick reply (seconds)
PAUSE_MAX = 60.0         # the pause doubles after each further quick reply in a row, up to this
MAX_POLLS = 300          # hard bound on progress(task_id) polls per window (with the pauses, 20 minutes allow at most 241)


def md5(text: str) -> str:
    return hashlib.md5(text.encode("utf-8")).hexdigest()


def frontmatter_and_body(path: Path) -> tuple[dict[str, str], str]:
    text = path.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.S)
    if not m:
        raise ValueError(f"no front matter in {path}")
    import yaml  # PyYAML is a dependency of the product (repo venv)
    return yaml.safe_load(m.group(1)), m.group(2)


def note_of(body: str) -> str:
    """The text under '## Note from the requester', up to the next '## ' heading or the end; trailing newline removed."""
    i = body.index(NOTE_HEADING + "\n") + len(NOTE_HEADING) + 1
    rest = body[i:]
    j = rest.find("\n## ")
    return (rest if j < 0 else rest[:j]).rstrip("\n")


def injected_text() -> tuple[str, str]:
    fm, body = frontmatter_and_body(E2_FILE)
    title, note = str(fm["title"]), note_of(body)
    if md5(title) != TITLE_MD5:
        raise AssertionError(f"title md5 {md5(title)} != {TITLE_MD5}")
    if len(note) != NOTE_LEN or md5(note) != NOTE_MD5:
        raise AssertionError(f"note len/md5 {len(note)}/{md5(note)} != {NOTE_LEN}/{NOTE_MD5}")
    return title, note


def find_task_file(org: Path, task_id: str) -> Path:
    for sub in ("sent", "read", "inbox"):
        p = org / sub / f"{task_id}.md"
        if p.is_file():
            return p
    raise FileNotFoundError(f"task {task_id} not found under {org}/(sent|read|inbox)")


def revised_task(org: Path, task_id: str) -> tuple[str, dict[str, str], Path]:
    path = find_task_file(org, task_id)
    fm, body = frontmatter_and_body(path)
    service = str(fm["service"])
    m = re.search(r"^## Request\n(.*?)(?=^## |\Z)", body, re.S | re.M)
    inputs: dict[str, str] = {}
    for line in (m.group(1) if m else "").splitlines():
        lm = re.match(r"^- ([^:]+): (.*)$", line)
        if lm:
            inputs[lm.group(1).strip()] = lm.group(2).strip()
    if not inputs:
        raise ValueError(f"no '## Request' inputs in {path}")
    return service, inputs, path


class Log:
    def __init__(self, out: Path, name: str = "injection-log.txt") -> None:
        out.mkdir(parents=True, exist_ok=True)
        self.path = out / name

    def write(self, text: str) -> None:
        with self.path.open("a", encoding="utf-8") as f:
            f.write(text.rstrip("\n") + "\n")

    def stamp(self) -> str:
        now = datetime.now(timezone.utc)
        return f"{now.strftime('%Y-%m-%dT%H:%M:%SZ')} (local {now.astimezone().strftime('%H:%M:%S %Z')})"

    def call(self, name: str, args: dict, reply: str, started: str) -> None:
        self.write(f"--- {name} at {started} -> reply at {self.stamp()}\nargs: {json.dumps(args, ensure_ascii=False)}\nreply:\n{reply}\n")


def server_params(org: Path):
    from mcp import StdioServerParameters
    env = {k: v for k, v in os.environ.items() if k not in ("ORG_AGENT", "ORG_REQUIRE_AGENT")}
    env["ORG_ROOT"] = str(org)
    return StdioServerParameters(command="uv", args=["--directory", REPO, "run", "hirearchy", "mcp"], env=env)


def text_of(result) -> str:
    return "\n".join(getattr(c, "text", "") for c in result.content)


async def call(session, log: Log, name: str, args: dict, timeout: int = 120) -> str:
    started = log.stamp()
    res = await session.call_tool(name, args, read_timeout_seconds=timedelta(seconds=timeout))
    reply = text_of(res)
    log.call(name, args, reply, started)
    if res.isError:
        raise RuntimeError(f"{name} returned an error: {reply}")
    return reply


def settled(reply: str, task_id: str) -> bool:
    """The end condition of protocol 5.3 step 4 (unchanged from E4): the task's line shows done, failed or blocked, and the reply
    shows the scheduler stopped."""
    line = next((ln for ln in reply.splitlines() if f"(task {task_id})" in ln), "")
    return bool(re.search(r"\]?: (done|failed|blocked)\b", line)) and "scheduler: stopped" in reply


async def poll_until_settled(progress, task_id: str, window_start: float, log: Log, window: float = WINDOW_MAX,
                             clock=time.monotonic, sleep=None) -> dict:
    """Protocol 5.3 step 4: progress(task_id=..., wait_seconds=min(300, time left)) repeated until settled(), until `window` seconds
    after `window_start`, or MAX_POLLS polls. `progress(args, timeout)` makes and logs one call and returns its reply.
    F-E4-9: a reply that came back in less than QUICK_REPLY seconds did not wait, so the loop pauses before the next poll
    (PAUSE_START, doubling per quick reply in a row up to PAUSE_MAX, never past the window); a reply that waited resets the pause.
    `clock` and `sleep` are injectable so the loop can be exercised offline with a stub (harness/test_poll_loop.py)."""
    if sleep is None:
        import anyio
        sleep = anyio.sleep
    polls = quick = 0
    paused = 0.0
    pause = PAUSE_START
    end = "window cap: 20 minutes passed" if window == WINDOW_MAX else f"window cap: {window:.0f} seconds passed"
    while True:
        left = window - (clock() - window_start)
        if left <= 0:
            log.write(end)
            break
        if polls >= MAX_POLLS:
            end = f"poll cap: {MAX_POLLS} polls"
            log.write(end)
            break
        wait = int(min(WAIT_STEP, left))
        t0 = clock()
        reply = await progress({"task_id": task_id, "wait_seconds": wait}, wait + 180)
        polls += 1
        took = clock() - t0
        if settled(reply, task_id):
            end = "settled: the task's line shows done, failed or blocked, and the scheduler has stopped"
            log.write(f"poll {polls}: reply after {took:.1f}s; settled")
            break
        if took < QUICK_REPLY:
            quick += 1
            nap = max(0.0, min(pause, window - (clock() - window_start)))
            log.write(f"poll {polls}: reply after {took:.1f}s (did not wait); pausing {nap:.1f}s before the next poll")
            if nap > 0:
                await sleep(nap)
                paused += nap
            pause = min(pause * 2, PAUSE_MAX)
        else:
            log.write(f"poll {polls}: reply after {took:.1f}s (waited); not settled")
            pause = PAUSE_START
    stats = {"polls": polls, "quick_replies": quick, "paused_seconds": round(paused, 1), "end": end}
    log.write(f"polling ended ({end}): progress(task_id) polls {polls}, quick replies {quick}, paused {paused:.1f}s in all")
    return stats


async def run(args: argparse.Namespace) -> int:
    from mcp import ClientSession
    from mcp.client.stdio import stdio_client

    org, out = Path(args.org).resolve(), Path(args.out)
    log = Log(out)
    marker = out / "injection-done.marker"
    script_md5 = hashlib.md5(Path(__file__).read_bytes()).hexdigest()
    title, note = injected_text()

    if args.stop:
        log.write(f"## STOP mode (stream end), script md5 {script_md5}, org {org}, {log.stamp()}")
        async with stdio_client(server_params(org)) as (r, w), ClientSession(r, w) as s:
            await s.initialize()
            await call(s, log, "stop", {})
        return 0

    if args.poll_check:
        plog = Log(out, "poll-check-log.txt")
        plog.write(f"## POLL CHECK (protocol 4.14; progress(task_id) only), script md5 {script_md5}, org {org}, task {args.task}, "
                   f"max {args.max_seconds}s, {plog.stamp()}")
        async with stdio_client(server_params(org)) as (r, w), ClientSession(r, w) as s:
            await s.initialize()
            stats = await poll_until_settled(lambda a, t: call(s, plog, "progress", a, timeout=t), args.task, time.monotonic(), plog,
                                             window=float(args.max_seconds))
        print(json.dumps(stats))
        return 0

    if args.selftest:
        async with stdio_client(server_params(org)) as (r, w), ClientSession(r, w) as s:
            await s.initialize()
            tools = await s.list_tools()
            print("tools:", ", ".join(sorted(t.name for t in tools.tools)))
        return 0

    if marker.exists():
        print("refused: an injection is already recorded for this stream", file=sys.stderr)
        return 2

    service, inputs, task_path = revised_task(org, args.revises)
    request_args = {"service": service, "inputs": inputs, "title": title, "note": note, "budget": BUDGET,
                    "revises": args.revises, "source": SOURCE}
    log.write(f"## INJECTION script md5 {script_md5}\norg: {org}\nrevised task file: {task_path}\n"
              f"title md5 {md5(title)}  note len {len(note)} md5 {md5(note)}  (asserted equal to protocol 5.1)\nstarted: {log.stamp()}")

    async with stdio_client(server_params(org)) as (read, write), ClientSession(read, write) as session:
        await session.initialize()
        # 1. precondition check (read-only)
        before = await call(session, log, "progress", {})
        if "scheduler: running" in before and not args.force:
            log.write("PRECONDITION NOT MET: a scheduler is running; nothing sent. Facilitator waits (file listing only) up to 20 min, then reruns with --force.")
            return 3
        if "scheduler: running" in before:
            log.write("NOTE: --force, scheduler still running after the facilitator's wait; injecting in any case (recorded).")
        # 2. the request
        window_start = time.monotonic()
        window_start_stamp = log.stamp()
        (out / "request-args.json").write_text(json.dumps(request_args, ensure_ascii=False, indent=2), encoding="utf-8")
        try:
            reply = await call(session, log, "request", request_args)
        except Exception as e:  # noqa: BLE001 - refused or failed before anything was recorded
            log.write(f"REQUEST REFUSED/FAILED (nothing recorded by the product): {e}")
            return 4
        marker.write_text(f"request sent {window_start_stamp}\n", encoding="utf-8")
        m = re.search(r"task (\d{8}T\d{6,}-root-[0-9a-f]+)", reply)
        if not m:
            log.write("FAILURE AFTER REQUEST: the injected task id was not found in the reply")
            return 5
        new_id = m.group(1)
        log.write(f"injected task id: {new_id}\nwindow start (request): {window_start_stamp}")
        try:
            # 3. start
            await call(session, log, "start", {})
            # 4. wait until the injected task is done/failed/blocked and the scheduler has stopped, or 20 minutes (F-E4-9: paced)
            await poll_until_settled(lambda a, t: call(session, log, "progress", a, timeout=t), new_id, window_start, log)
            # 5. final state (read-only)
            await call(session, log, "progress", {})
            await call(session, log, "status", {})
        except Exception as e:  # noqa: BLE001
            log.write(f"FAILURE AFTER REQUEST: {e!r}")
            return 5
        log.write(f"window end (final progress): {log.stamp()}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--org", required=True, help="S/org of the stream")
    ap.add_argument("--revises", help="the memo-1 root task id (the task whose done result was memo 1's first delivery)")
    ap.add_argument("--out", help="S/injection (log directory)")
    ap.add_argument("--force", action="store_true", help="inject although a scheduler still runs (after the 20-minute wait)")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--stop", action="store_true")
    ap.add_argument("--poll-check", action="store_true", help="preflight only: the step-4 polling loop alone (progress only)")
    ap.add_argument("--task", help="--poll-check: the task id to poll")
    ap.add_argument("--max-seconds", type=int, default=120, help="--poll-check: the window in seconds (default 120)")
    a = ap.parse_args()
    try:
        if a.dry_run:
            title, note = injected_text()
            print(f"title md5 {md5(title)} ok; note len {len(note)} md5 {md5(note)} ok")
            if a.revises:
                service, inputs, path = revised_task(Path(a.org), a.revises)
                print(json.dumps({"service": service, "inputs": inputs, "title": title, "note": f"<{len(note)} chars>",
                                  "budget": BUDGET, "revises": a.revises, "source": SOURCE}, ensure_ascii=False, indent=2))
                print("task file:", path)
            return 0
        if not a.out and not a.selftest:
            ap.error("--out is required")
        if a.poll_check and not a.task:
            ap.error("--poll-check needs --task")
        if not (a.selftest or a.stop or a.poll_check) and not a.revises:
            ap.error("--revises is required")
        import anyio
        a.out = a.out or "/tmp"
        return anyio.run(run, a)
    except (AssertionError, ValueError, FileNotFoundError, KeyError) as e:
        print(f"error (nothing sent): {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
