#!/usr/bin/env python3
"""P2's call of P1's extract_mechanical.py, for effort-stopped runs (protocol 3.5; protocol amendment 1 item 5 (B)).

    python3 -B extract_mechanical_p2.py <streamdir> <S or "-"> [--product-src SRC] [--out DIR]     (the arguments of extract_mechanical.py)

**Why.** An effort-stopped org run (batch 1.1: the product stops a run whose effort was not set and relaunches it uncharged; its run log
carries `# kiro: effort not set`) leaves a kiro session folder with `session.json` and no `messages.jsonl`. P1's `extract_mechanical.py`
already reads such a session as 0 credits where it sums credits (a `FileNotFoundError` caught), but its revise_playbook section opens the
matched session's `messages.jsonl` unguarded, so it crashed and wrote no `cost.txt` (R1 v1's finish:
`R1/harness-failures/finish-r1-v1-findings.md` item 2). `extract_mechanical.py` is P1's file, pinned byte-identical to P1's harness
(protocol 2.1, 10; `CHANGES.md`), so it is NOT edited.

**What this does.** It runs P1's `main(argv)` unchanged in this process, with one name bound in that module only: `open`, so that opening
a `messages.jsonl` that does not exist, in a folder whose `session.json` does exist, reads as an empty file (what the module's own credit
loop already does for it) and is recorded. Every other `open` is the builtin. Then it checks every recorded session against
`run-session-map.txt` (which the extract wrote): each must be matched to a run whose log under `<streamdir>/run-logs/` has a line starting
`# kiro: effort not set`. If all are, it appends one line to `cost.txt` (no line `cost_total.py` reads is touched):
    effort stops read as empty sessions (no messages.jsonl; '# kiro: effort not set' in the run log; relaunched uncharged, 0 credits): <k> (<run id> -> <session id>, ...)
If one is not (no run, or a run without the mark), it fails closed: `cost.txt` is renamed `cost.txt.unverified` with a `FAIL-CLOSED:` line
naming the session(s), it exits 1, and the finish's `credits` step then has no figure (protocol 11: a missing figure is never low).
Exit codes: P1's (2 on bad arguments), 1 when it failed closed, else 0.
"""
from __future__ import annotations

import builtins
import io
import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import extract_mechanical as em  # noqa: E402  (P1's file, byte-identical to its pin; nothing in it is changed)

MARK = re.compile(r"^# kiro: effort not set", re.M)
LINE = "effort stops read as empty sessions (no messages.jsonl; '# kiro: effort not set' in the run log; relaunched uncharged, 0 credits)"
_empty: dict[str, str] = {}  # session id -> the folder that has session.json and no messages.jsonl


def _open(file, *a, **k):
    p = Path(file) if isinstance(file, (str, Path)) else None
    if p is not None and p.name == "messages.jsonl" and not p.exists() and (p.parent / "session.json").exists():
        _empty.setdefault(p.parent.name, str(p.parent))
        return io.StringIO("")
    return builtins.open(file, *a, **k)


def out_dir(argv: list[str]) -> Path:
    return Path(argv[argv.index("--out") + 1]) if "--out" in argv else Path(argv[0])


def verify(D: Path, OUT: Path) -> tuple[list[str], list[str]]:
    """(counted `<run id> -> <session id>`, failures) for the recorded empty sessions, from run-session-map.txt and the run logs."""
    smap = (OUT / "run-session-map.txt").read_text() if (OUT / "run-session-map.txt").exists() else ""
    by_sess: dict[str, list[tuple[str, str]]] = {}
    for ln in smap.splitlines():
        m = re.match(r"^run (\S+)\s+(\d{8}T\d+) model=\S+ exit=\S+ secs=\S+ -> session (sess_\S+) credits", ln)
        if m:
            by_sess.setdefault(m.group(3), []).append((m.group(1), m.group(2)))
    counted, bad = [], []
    for sid in sorted(_empty):
        runs = by_sess.get(sid, [])
        if len(runs) != 1:
            bad.append(f"{sid}: {len(runs)} runs matched (run-session-map.txt)")
            continue
        run_id, stamp = runs[0]
        logs = sorted(D.glob(f"run-logs/*/{stamp}.log"))
        if len(logs) != 1:
            bad.append(f"{sid}: run {run_id}: {len(logs)} run logs named {stamp}.log")
        elif not MARK.search(logs[0].read_text(errors="replace")):
            bad.append(f"{sid}: run {run_id}: its log has no '# kiro: effort not set' line (not an effort stop)")
        else:
            counted.append(f"{run_id} -> {sid}")
    return counted, bad


def main(argv: list[str]) -> int:
    em.open = _open  # module-global name: shadows the builtin inside extract_mechanical only
    try:
        rc = em.main(argv)
    finally:
        del em.open
    if rc != 0:
        return rc
    D, OUT = Path(argv[0]), out_dir(argv)
    cost = OUT / "cost.txt"
    counted, bad = verify(D, OUT)
    if bad:
        unv = OUT / "cost.txt.unverified"
        text = cost.read_text() if cost.exists() else ""
        unv.write_text(text + "FAIL-CLOSED: session folder(s) without messages.jsonl that are no effort stop: " + "; ".join(bad) + "\n")
        cost.unlink(missing_ok=True)
        print(f"FAIL-CLOSED: {len(bad)} session folder(s) without messages.jsonl are no effort stop: {'; '.join(bad)}; cost.txt -> {unv.name}")
        return 1
    with builtins.open(cost, "a") as f:
        f.write(f"{LINE}: {len(counted)} ({', '.join(counted) or 'none'})\n")
    print(f"{LINE}: {len(counted)} ({', '.join(counted) or 'none'})")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
