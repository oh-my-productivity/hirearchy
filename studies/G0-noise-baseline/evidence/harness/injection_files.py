#!/usr/bin/env python3
"""G0 injection files: injection/text-identity.txt and injection/window-runs.txt (E7 protocol 5.1 and 5.4). Read-only on everything it reads.

Source and what was generalized. E7 has two producers of these files: `s2|s3/harness/injection_files.py` (reads the sandbox's org; its output
format has RL1/RL3 labels and `ok=`/`killed=`) and a section of `harness/extract_mechanical.py` (reads the stream dir plus the org's git;
format `exit=`/`secs=`/`session=` and `P1`/`P3` labels). The files COMMITTED in E7's `s1|s2|s3/injection/` have the second format (their
first run line carries `exit=0 secs=.. session=..`), so this script writes the committed format: the text-identity check of the first
script and the window-runs section of the second, both read from the stream dir (events/, run-logs/, msgs/, injection/) instead of the
sandbox. No service folder, owner or run id is hard-coded: the owner is detected like extract_mechanical.py does.

Usage:  python3 -B injection_files.py <streamdir> <sandbox S or "-"> [--injected ID] [--memo1 ID] [--session-map FILE] [--out DIR]
  <streamdir>     the stream's evidence dir (needs injection/window.txt; injection/injection-log.txt gives the ids)
  S               the sandbox, only for the org git lines (the lead run's MEMORY.md diff). "-" or a missing org: those lines say
                  "not available" and every other line comes from the stream dir.
  --injected ID   the injected root task (default: `injected task id:` of injection/injection-log.txt)
  --memo1 ID      the root task it revised (default: the `revised task file:` line of the same log)
  --session-map   run-session-map.txt written by extract_mechanical.py (default: <streamdir>/run-session-map.txt); gives each run's session id
  --out DIR       where text-identity.txt and window-runs.txt go (default: <streamdir>/injection/); the stream dir is never written otherwise."""
import glob
import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import extract_mechanical as em  # noqa: E402  (pure helpers only; the product import happens inside run_extract, never here)

TITLE_MD5 = "849fe21b104be883af9b3c06367d4445"
NOTE_MD5 = "4cdbcb9b682f2f25dcb31c83d3743fec"
NOTE_LEN = 866


def session_map(path: Path) -> dict:
    """run id -> session id from run-session-map.txt ({} when absent)."""
    out = {}
    if path.exists():
        for ln in path.read_text().splitlines():
            m = re.match(r"^run (\S+)\s+\d{8}T\d+ model=\S+ exit=\S+ secs=\S+ -> session (sess_\S+)", ln)
            if m:
                out[m.group(1)] = m.group(2)
    return out


def commit_entry(D: Path, owner: str, stamp: str):
    """(short sha, log lines) of the commit whose subject names `<owner>/runs/<stamp>.log`, from the stream dir's org-git-log.txt (git log --stat), or None."""
    f = Path(D) / "org-git-log.txt"
    if not f.exists():
        return None
    blocks, cur = [], None
    for ln in f.read_text(errors="replace").splitlines():
        if re.match(r"commit \w{40}$", ln):
            cur = [ln]
            blocks.append(cur)
        elif cur is not None:
            cur.append(ln)
    for b in blocks:
        if f"[{owner}/runs/{stamp}.log]" in "\n".join(b):
            while b and not b[-1].strip():
                b = b[:-1]
            return b[0].split()[1][:7], b
    return None


def run_injection_files(D: Path, S_arg: str, OUT: Path, injected: str = None, memo1: str = None, smap: Path = None) -> dict:
    D, OUT = Path(D), Path(OUT)
    OUT.mkdir(parents=True, exist_ok=True)
    info = em.detect(D)
    owner, owner_dir = info["owner"], info["owner_dir"]
    log_f = D / "injection" / "injection-log.txt"
    log = log_f.read_text() if log_f.exists() else ""
    if injected is None:
        m = re.search(r"injected task id: (\S+)", log)
        injected = m.group(1) if m else "-"
    if memo1 is None:
        m = re.search(r"revised task file: .*/(\S+)\.md", log)
        memo1 = m.group(1) if m else "-"
    org = None
    if S_arg != "-" and (Path(S_arg) / "org").is_dir():
        org = Path(S_arg) / "org"

    def git(*a):
        return subprocess.run(["git", "-C", str(org), *a], capture_output=True, text=True).stdout if org else ""

    # ---- text identity (protocol 5.1)
    hdr, body, raw = em.read_msg(D / "msgs" / "sent" / f"{injected}.md")
    note = body.split("## Note from the requester\n", 1)[1]
    note = note.split("\n## ", 1)[0].rstrip("\n")
    title = hdr.get("title")
    ti = [f"title as stored: {title!r} md5 {em.md5b(title.encode())} (protocol 5.1: {TITLE_MD5}) match={em.md5b(title.encode()) == TITLE_MD5}",
          f"note as stored: {len(note)} chars md5 {em.md5b(note.encode())} (protocol 5.1: {NOTE_LEN} chars, {NOTE_MD5}) match={len(note) == NOTE_LEN and em.md5b(note.encode()) == NOTE_MD5}",
          f"stored headers: {json.dumps(hdr, ensure_ascii=False)}"]
    (OUT / "text-identity.txt").write_text("\n".join(ti) + "\n")
    # ---- window runs (protocol 5.4)
    w0, w1 = (D / "injection" / "window.txt").read_text().split()[:2]
    w0d, w1d = em.parse_ts(w0 + "Z"), em.parse_ts(w1 + "Z")
    events = []
    for f in sorted(glob.glob(str(D / "events" / "*" / "*.jsonl"))):
        for line in open(f):
            try:
                events.append(json.loads(line))
            except Exception:  # noqa: BLE001
                pass
    events.sort(key=lambda e: e["ts"])
    rp = [e for e in events if e["kind"] == "tool.call" and e.get("tool") == "revise_playbook"]
    P1 = re.compile(r"^\[tool\] @hirearchy/revise_playbook(?= |$)", re.M)
    P3 = re.compile(r"^\[tool\] @hirearchy/\w+", re.M)
    smp = session_map(smap or (D / "run-session-map.txt"))
    o = [f"# window runs (protocol 5.4): runs that started in the injection window {w0}Z .. {w1}Z; injected task {injected}; revised (memo 1) task {memo1}", ""]
    n = 0
    for lg in sorted(glob.glob(str(D / "run-logs" / "*" / "*.log")), key=lambda x: Path(x).stem):  # E7 sorted its runs by stamp
        stamp = Path(lg).stem
        agent_dir = Path(lg).parent.name
        dt = em.stamp_to_dt(stamp)
        if not (w0d <= dt <= w1d):
            continue
        txt = Path(lg).read_text(errors="replace")
        cmd = re.search(r"^# cmd: .*? --agent (\S+) --model (\S+)", txt, re.M)
        ex = re.search(r"^# exit (\S+) after (\d+)s", txt, re.M)
        se = next((e for e in events if e["kind"] == "run.start" and e.get("run", "").endswith("@" + stamp)), None)
        ee = next((e for e in events if e["kind"] == "run.end" and e.get("run", "").endswith("@" + stamp)), None)
        run_id = (se or {}).get("run") or ("?@" + stamp)
        n += 1
        o.append(f"## run {run_id} agent={agent_dir} model={cmd.group(2) if cmd else None} start={se and se['ts']} end={ee and ee['ts']} "
                 f"exit={ex.group(1) if ex else None} secs={int(ex.group(2)) if ex else None} session={smp.get(run_id)}")
        rpc = [e for e in rp if e.get("run") == run_id]
        o.append(f"revise_playbook calls in this run (events): {len(rpc)}")
        for e in rpc:
            o.append(f"  {e['ts']} ok={e.get('ok')} error={e.get('error')} args={json.dumps(e.get('args'))}")
        outp = txt.split("# ---- output ----", 1)[-1]
        o.append(f"run-log P1 lines: {len(P1.findall(outp))}; P3 lines: {len(P3.findall(outp))}")
        if agent_dir == owner_dir:
            t0, t1 = em.parse_ts(se["ts"]) if se else w0d, em.parse_ts(ee["ts"]) if ee else w1d
            for f in sorted(glob.glob(str(D / "msgs" / f"{owner_dir}-sent" / "*.md"))):
                h2, b2, _ = em.read_msg(f)
                try:
                    cr = em.parse_ts(h2.get("created", ""))
                except Exception:  # noqa: BLE001
                    continue
                if t0 <= cr <= t1:
                    les = re.search(r"## Lessons\n(.*?)(?=\n## |\Z)", b2, re.S)
                    o.append(f"  lead message {h2.get('id')} to={h2.get('to')} type={h2.get('type')} status={h2.get('status')} created={h2.get('created')}\n  ## Lessons: {les.group(1).strip() if les else '(none)'}")
            if org:
                for h in git("log", f"--grep={stamp}", "--format=%h").split():
                    o.append(f"  org-git commit {h} MEMORY.md diff:\n" + "\n".join("    " + x for x in git("show", h, "--", f"{owner}/MEMORY.md").splitlines()))
            else:
                entry = commit_entry(D, owner, stamp)
                if entry:
                    o.append(f"  org-git commit {entry[0]} (from org-git-log.txt; the MEMORY.md patch itself is in the org's git, which the stream dir does not hold):")
                    o.extend("    " + x for x in entry[1])
                else:
                    o.append("  org-git: not available (no sandbox, and org-git-log.txt has no commit for this run)")
        o.append("")
    (OUT / "window-runs.txt").write_text("\n".join(o) + "\n")
    return {"window_runs": n, "injected": injected, "memo1": memo1}


def main(argv):
    args = list(argv)
    opts = {}
    for flag in ("--out", "--injected", "--memo1", "--session-map"):
        if flag in args:
            i = args.index(flag)
            opts[flag] = args[i + 1]
            del args[i:i + 2]
    if len(args) != 2:
        print(__doc__)
        return 2
    D = Path(args[0])
    if not (D / "injection" / "window.txt").exists():
        print(f"no injection/window.txt in {D}", file=sys.stderr)
        return 2
    res = run_injection_files(D, args[1], Path(opts["--out"]) if "--out" in opts else D / "injection", opts.get("--injected"), opts.get("--memo1"),
                              Path(opts["--session-map"]) if "--session-map" in opts else None)
    print(f"written {res['window_runs']} window runs")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
