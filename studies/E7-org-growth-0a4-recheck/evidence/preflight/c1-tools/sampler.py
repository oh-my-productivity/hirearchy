#!/usr/bin/env python3
"""C1 sampler (stdlib only; DR-0a4-1, -3, -10). Writes only under --sb.

Started by its own run_in_background call BEFORE the chat call it watches. Every 0.1 s it reads `ps -A` in memory and writes, per sample, only the
processes it tracks: the chat process and its descendants, the scheduler (SB/org/.runtime/scheduler.pid) and its descendants, each run (child_pid of
every run.start event) and its descendants. It stops itself --window seconds after the chat process is gone (hard cap 900 s).

Files: SB/samples/<ID>-turn<K>.jsonl (samples), .meta.json (KIRO_* names of its own environment, chat first-seen/gone, changed names by group, D-OUT),
.done. Environment VALUES are kept in memory only and never written; only names are.
"""
from __future__ import annotations

import argparse
import datetime
import glob
import json
import os
import re
import subprocess
import sys
import time

PS_ALL = ["ps", "-A", "-ww", "-o", "pid=,ppid=,pgid=,sess=,stat=,lstart=,command="]
ROW = re.compile(r"^\s*(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\S+)\s+(\S+\s+\S+\s+\d+\s+[\d:]+\s+\d{4})\s+(.*)$")
NAME = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)=(.*)$")
VALID_NAME = re.compile(r"^[A-Z_][A-Z0-9_]*$")
M2_REFUSAL = ("PATH", "HOME", "KIRO_API_KEY", "KIRO_HOME", "ORG_ROOT", "HIREARCHY_STATE_DIR", "PYTHONUNBUFFERED")


def utc_ms(t: float | None = None) -> str:
    d = datetime.datetime.fromtimestamp(time.time() if t is None else t, datetime.timezone.utc)
    return d.isoformat(timespec="milliseconds")


def read_ps() -> dict[int, dict]:
    out = subprocess.run(PS_ALL, capture_output=True, text=True).stdout
    rows: dict[int, dict] = {}
    for line in out.splitlines():
        m = ROW.match(line)
        if m:
            pid = int(m.group(1))
            rows[pid] = {"pid": pid, "ppid": int(m.group(2)), "pgid": int(m.group(3)), "sess": int(m.group(4)),
                         "stat": m.group(5), "lstart": m.group(6), "cmd": m.group(7)}
    return rows


def descendants(rows: dict[int, dict], roots: list[int]) -> set[int]:
    kids: dict[int, list[int]] = {}
    for r in rows.values():
        kids.setdefault(r["ppid"], []).append(r["pid"])
    seen: set[int] = set()
    todo = [p for p in roots if p in rows]
    while todo:
        p = todo.pop()
        if p in seen:
            continue
        seen.add(p)
        todo.extend(kids.get(p, []))
    return seen


def parse_env(text: str) -> dict[str, str]:
    """`ps -E` output -> {NAME: value}; best effort (a value with spaces is re-joined with single spaces)."""
    env: dict[str, str] = {}
    last = None
    for tok in text.split():
        m = NAME.match(tok)
        if m:
            last = m.group(1)
            env[last] = m.group(2)
        elif last is not None:
            env[last] += " " + tok
    return env


def norm(v: str) -> str:
    return " ".join(v.split())


def ps_env(pid: int) -> dict[str, str]:
    out = subprocess.run(["ps", "-E", "-ww", "-o", "command=", "-p", str(pid)], capture_output=True, text=True).stdout
    return parse_env(out)


def changed_names(proc_env: dict[str, str]) -> list[str]:
    mine = {k: norm(v) for k, v in os.environ.items()}
    return sorted(k for k, v in proc_env.items() if k not in mine or mine[k] != norm(v))


def groups(names: list[str], profile_keys: list[str]) -> dict:
    g: dict[str, list[str]] = {"profile_env_keys": [], "virtual_env_and_uv": [], "m2_refusal_list": [], "kiro_chat_log_file": [], "d_env_names": [], "dropped_invalid": []}
    for n in names:
        if n in profile_keys:
            g["profile_env_keys"].append(n)
        elif n == "VIRTUAL_ENV" or n.startswith("UV_"):
            g["virtual_env_and_uv"].append(n)
        elif n in M2_REFUSAL:
            g["m2_refusal_list"].append(n)
        elif n == "KIRO_CHAT_LOG_FILE":
            g["kiro_chat_log_file"].append(n)
        elif VALID_NAME.match(n):
            g["d_env_names"].append(n)
        else:
            g["dropped_invalid"].append(n)
    return g


class Events:
    """Incremental reader of SB/org/.runtime/events/*/*.jsonl."""

    def __init__(self, org: str) -> None:
        self.pattern = os.path.join(org, ".runtime", "events", "*", "*.jsonl")
        self.offsets: dict[str, int] = {}
        self.items: list[dict] = []

    def poll(self) -> list[dict]:
        new: list[dict] = []
        for f in glob.glob(self.pattern):
            try:
                with open(f, "rb") as fh:
                    fh.seek(self.offsets.get(f, 0))
                    data = fh.read()
            except OSError:
                continue
            end = data.rfind(b"\n")
            if end < 0:
                continue
            self.offsets[f] = self.offsets.get(f, 0) + end + 1
            for line in data[: end + 1].splitlines():
                try:
                    new.append(json.loads(line))
                except ValueError:
                    pass
        self.items.extend(new)
        return new


def ev_epoch(ev: dict) -> float:
    return datetime.datetime.fromisoformat(ev["ts"]).timestamp()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sb", required=True)
    ap.add_argument("--attempt", required=True)
    ap.add_argument("--turn", required=True)
    ap.add_argument("--agent", required=True)
    ap.add_argument("--window", type=float, default=15.0)
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--d-out", action="store_true")
    ap.add_argument("--wt", default="/Volumes/workspace/hirearchy/.worktrees/org-growth-0a4")
    a = ap.parse_args()
    sb, base = a.sb, os.path.join(a.sb, "samples", f"{a.attempt}-turn{a.turn}")
    org = os.path.join(sb, "org")
    os.makedirs(os.path.dirname(base), exist_ok=True)
    meta: dict = {"sampler_started": utc_ms(), "sampler_env_kiro_names": sorted(k for k in os.environ if k.startswith("KIRO_")),
                  "ps_sess_note": "SESS reads 0 on macOS; sessions are inferred from pgid/ppid only (DR-0a4-10)"}
    profile_keys: list[str] = []
    try:
        prof = json.load(open(os.path.join(sb, "kiro-home", "agents", f"{a.agent}.json")))
        profile_keys = sorted(prof["mcpServers"]["hirearchy"].get("env", {}))
    except (OSError, ValueError, KeyError):
        pass
    meta["profile_env_keys"] = profile_keys

    def flush() -> None:
        with open(base + ".meta.json", "w") as fh:
            json.dump(meta, fh, indent=1, sort_keys=True)

    flush()
    events = Events(org)
    out = open(base + ".jsonl", "w")
    t0 = time.time()
    chat_first = chat_gone = None
    sched_pid = None
    run_pids: list[int] = []
    server_env: dict[str, str] | None = None  # VALUES: memory only
    sched_read = False
    dout_proc = None
    dout_done = False

    while time.time() - t0 < 900:
        now = time.time()
        rows = read_ps()
        # the topmost process that is the turn's chat call (argv0 is kiro-cli: the outer tool shell's own command line is not it)
        chats = [r for r in rows.values() if os.path.basename(r["cmd"].split(" ", 1)[0]).startswith("kiro-cli")
                 and " chat " in r["cmd"] + " " and f"--agent {a.agent}" in r["cmd"] and (" --resume" in r["cmd"]) == a.resume]
        top = [r for r in chats if r["ppid"] not in {c["pid"] for c in chats}]
        chat_pid = top[0]["pid"] if top else None
        if chat_pid is not None and chat_first is None:
            chat_first = now
            meta["chat_pid"] = chat_pid
            meta["chat_first_seen"] = utc_ms(now)
            flush()
        if chat_first is not None and chat_pid is None and chat_gone is None:
            chat_gone = now
            meta["chat_gone"] = utc_ms(now)
            meta["chat_gone_epoch"] = now
            flush()
        for ev in events.poll():
            if ev.get("kind") == "run.start" and isinstance(ev.get("child_pid"), int):
                run_pids.append(ev["child_pid"])
            if ev.get("kind") == "scheduler.start" and isinstance(ev.get("pid"), int):
                sched_pid = ev["pid"]
            if (a.d_out and not dout_done and chat_first is not None and ev.get("kind") == "tool.call" and ev.get("proc") == "mcp"
                    and ev.get("tool") == "progress" and ev_epoch(ev) >= chat_first - 1):
                dout_done = True
                dout_proc = start_dout(a, meta, server_env, profile_keys, sb)
                flush()
        try:
            txt = open(os.path.join(org, ".runtime", "scheduler.pid")).read().strip()
            sched_pid = int(txt) if txt.isdigit() else sched_pid
        except OSError:
            pass
        chat_tree = descendants(rows, [chat_pid]) if chat_pid else set()
        sched_tree = descendants(rows, [sched_pid]) if sched_pid else set()
        run_tree = descendants(rows, run_pids)
        # the changed names (names only), once per process
        if server_env is None and chat_tree:
            servers = [p for p in chat_tree if "hirearchy mcp" in rows[p]["cmd"]]
            if servers:
                deepest = max(servers, key=lambda p: _depth(rows, p, chat_pid))
                env = ps_env(deepest)
                if env:
                    server_env = env
                    names = changed_names(env)
                    meta["server_pid"] = deepest
                    meta["server_changed_names"] = groups(names, profile_keys)
                    meta["server_has_KIRO_API_KEY"] = "yes" if "KIRO_API_KEY" in env else "no"
                    flush()
        if not sched_read and sched_pid and sched_pid in rows:
            env = ps_env(sched_pid)
            if env:
                sched_read = True
                meta["scheduler_pid"] = sched_pid
                meta["scheduler_changed_names"] = groups(changed_names(env), profile_keys)
                meta["scheduler_has_KIRO_API_KEY"] = "yes" if "KIRO_API_KEY" in env else "no"
                flush()
        tracked: dict[int, str] = {}
        for p in chat_tree:
            tracked[p] = "chat" if p == chat_pid else "chat-tree"
        for p in sched_tree:
            tracked[p] = "scheduler" if p == sched_pid else "scheduler-tree"
        for p in run_tree:
            tracked[p] = "run" if p in run_pids else "run-tree"
        if server_env is not None and meta.get("server_pid") in tracked:
            tracked[meta["server_pid"]] = "server"
        procs = [{**{k: rows[p][k] for k in ("pid", "ppid", "pgid", "sess", "stat", "lstart")}, "cmd": rows[p]["cmd"][:140], "role": role}
                 for p, role in sorted(tracked.items())]
        # a tracked pid that is gone from ps is simply absent from this sample
        out.write(json.dumps({"t": utc_ms(now), "epoch": round(now, 3), "procs": procs}) + "\n")
        out.flush()
        if chat_gone is not None and now - chat_gone >= a.window:
            break
        time.sleep(max(0.0, 0.1 - (time.time() - now)))
    out.close()
    if dout_proc is not None:
        try:
            dout_proc.wait(timeout=20)
        except subprocess.TimeoutExpired:
            pass
        meta["d_out"]["returncode"] = dout_proc.returncode
        try:
            meta["d_out"]["output"] = open(os.path.join(sb, "out", f"{a.attempt}-dout.out")).read().strip()[:400]
        except OSError:
            pass
    meta["sampler_stopped"] = utc_ms()
    flush()
    open(base + ".done", "w").write(utc_ms() + "\n")
    return 0


def _depth(rows: dict[int, dict], pid: int, top: int | None) -> int:
    d = 0
    while pid in rows and pid != top and d < 50:
        pid = rows[pid]["ppid"]
        d += 1
    return d


def start_dout(a: argparse.Namespace, meta: dict, server_env: dict[str, str] | None, profile_keys: list[str], sb: str):
    """D-OUT (DR-0a4-3): the sampler starts the scheduler through Org(...).runtime.scheduler_control.start(None, True); values stay in memory."""
    env = dict(os.environ)
    env["HIREARCHY_STATE_DIR"] = os.path.join(sb, "kiro-state")
    env["HOME"] = os.path.join(sb, "home")
    excluded = set(profile_keys) | {"KIRO_HOME", "VIRTUAL_ENV", "PATH", "KIRO_CHAT_LOG_FILE"}
    names_set: list[str] = ["HIREARCHY_STATE_DIR", "HOME"]
    for k, v in (server_env or {}).items():
        if k in excluded or k.startswith("UV_"):
            if k not in ("HIREARCHY_STATE_DIR", "HOME"):
                env[k] = v
                names_set.append(k)
    code = "import sys; from hirearchy.app import Org; print(Org(sys.argv[1]).runtime.scheduler_control.start(None, True))"
    outf = open(os.path.join(sb, "out", f"{a.attempt}-dout.out"), "w")
    meta["d_out"] = {"trigger_time": utc_ms(), "names_set_by_the_sampler": sorted(set(names_set)),
                     "server_env_available": server_env is not None}
    return subprocess.Popen([os.path.join(a.wt, ".venv", "bin", "python"), "-I", "-c", code, os.path.join(sb, "org")], env=env,
                            stdout=outf, stderr=subprocess.STDOUT, cwd=sb)


if __name__ == "__main__":
    sys.exit(main())
