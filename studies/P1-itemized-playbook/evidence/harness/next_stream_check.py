#!/usr/bin/env python3
"""P1 self-check part: next_stream.sh on constructed evidence trees (protocol 1, 8, 11; review findings H1 and M13), the memories gate
between two streams (memories_gate.py, protocol 8; P2-M6) and its place in setup_stream.sh (before anything is created).

Each case writes a throwaway evidence tree under <out>/next-stream-cases/<n>/ (finish-steps.txt, memories-db.txt, credits.txt and the
manager's decision files, as the stream steps and the manager write them) and runs next_stream.sh on it (P1_NEXT_STREAM_EV points the
script at the tree; the stream steps never set it); the memories-gate cases (m<n>/) write memories-md5-after.txt files and run
memories_gate.py with a given current md5 (setup_stream.sh passes the md5 of ~/.kiro/memories/memories.db). The expected first output
line and exit code are written here from protocol 1, 8 and 11.

    python3 -B next_stream_check.py --out DIR   ->  one line per case and `next_stream_check: <ok> of <n> checks OK`
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

H = Path(__file__).resolve().parent


def done(ev: Path, label: str, credits: str | None = "150.00", memories="unchanged"):
    d = ev / label
    d.mkdir(parents=True, exist_ok=True)
    (d / "finish-steps.txt").write_text("... ended 2026-11-01T00:00:00Z\n")
    (d / "memories-db.txt").write_text(f"memories.db {memories.upper() if memories != 'unchanged' else 'unchanged'} during {label}\n")
    if credits is not None:
        (d / "credits.txt").write_text(f"stream total credits: {credits} (assistant 60.00 + org runs 90.00)\n")


def touch(ev: Path, name: str):
    (ev / name).write_text("the manager's record\n")


GATE = ("stage-1-gate.md", "manager-decision-stage-2.md")
CASES = [  # (name, setup(ev), expected first line, or its start)
    ("nothing done yet", lambda ev: None, "F1"),
    ("F1 done", lambda ev: done(ev, "F1"), "I1"),
    ("stage 1 done, no gate", lambda ev: [done(ev, "F1"), done(ev, "I1")], "REFUSED: stage 2 needs"),
    ("stage 1 done, gate and the manager's yes", lambda ev: [done(ev, "F1"), done(ev, "I1"), *[touch(ev, g) for g in GATE]], "I2"),
    ("a stage-1 stream over 185: the gate decides, not next_stream", lambda ev: [done(ev, "F1", "190.00")], "I1"),
    ("I2 at 185.00 (not over)", lambda ev: [done(ev, "F1"), done(ev, "I1"), *[touch(ev, g) for g in GATE], done(ev, "I2", "185.00")], "F2"),
    ("I2 at 185.01 (over): the study pauses", lambda ev: [done(ev, "F1"), done(ev, "I1"), *[touch(ev, g) for g in GATE],
                                                          done(ev, "I2", "185.01")], "REFUSED: I2 cost 185.01"),
    ("I2 over 185, the manager's cost decision recorded", lambda ev: [done(ev, "F1"), done(ev, "I1"), *[touch(ev, g) for g in GATE],
                                                                      done(ev, "I2", "190.00"), touch(ev, "manager-decision-cost-I2.md")], "F2"),
    ("F1 done without credits.txt", lambda ev: done(ev, "F1", None), "REFUSED: F1 has no 'stream total credits:'"),
    ("memories.db changed during F1", lambda ev: done(ev, "F1", memories="changed"), "REFUSED: memories.db changed during F1"),
    ("memories.db changed, the manager decided", lambda ev: [done(ev, "F1", memories="changed"),
                                                            touch(ev, "manager-decision-memories-F1.md")], "I1"),
    ("F1's replacement approved: it runs next", lambda ev: [done(ev, "F1"), touch(ev, "manager-decision-replacement-F1.md")], "F1r"),
    ("F1r done: back to the order", lambda ev: [done(ev, "F1"), touch(ev, "manager-decision-replacement-F1.md"), done(ev, "F1r")], "I1"),
    ("a replacement in stage 2 over 185 pauses too", lambda ev: [done(ev, "F1"), done(ev, "I1"), *[touch(ev, g) for g in GATE],
                                                                 done(ev, "I2"), touch(ev, "manager-decision-replacement-I2.md"),
                                                                 done(ev, "I2r", "200.00")], "REFUSED: I2r cost 200.00"),
    ("two replacement approvals in arm F", lambda ev: [touch(ev, "manager-decision-replacement-F1.md"),
                                                       touch(ev, "manager-decision-replacement-F2.md")], "REFUSED: 2 replacement approvals in arm F"),
]


def mem_after(ev: Path, label: str, md5: str):
    d = ev / label
    d.mkdir(parents=True, exist_ok=True)
    (d / "memories-md5-after.txt").write_text(md5 + "\n")


MEM_CASES = [  # (name, setup(ev), label, current md5, expected exit, expected first-line start) for memories_gate.py (protocol 8, P2-M6)
    ("F1: no previous stream", lambda ev: None, "F1", "aaa", 0, "memories gate: no previous stream"),
    ("I1: unchanged since F1's end", lambda ev: mem_after(ev, "F1", "aaa"), "I1", "aaa", 0, "memories gate: memories.db unchanged since F1"),
    ("I1: changed since F1's end: STOP before anything is created", lambda ev: mem_after(ev, "F1", "aaa"), "I1", "bbb", 4,
     "STOP: memories.db changed between F1 and I1: aaa -> bbb"),
    ("I1: changed, the manager's decision recorded", lambda ev: [mem_after(ev, "F1", "aaa"), touch(ev, "manager-decision-memories-before-I1.md")],
     "I1", "bbb", 0, "memories gate: memories.db changed between F1 and I1"),
    ("F1r: compared with F1 (the stream it replaces runs just before)", lambda ev: [mem_after(ev, "F1", "aaa"),
                                                                                     touch(ev, "manager-decision-replacement-F1.md")],
     "F1r", "bbb", 4, "STOP: memories.db changed between F1 and F1r"),
    ("I1 after F1r: compared with F1r's end", lambda ev: [mem_after(ev, "F1", "aaa"), mem_after(ev, "F1r", "ccc"),
                                                          touch(ev, "manager-decision-replacement-F1.md")], "I1", "ccc", 0,
     "memories gate: memories.db unchanged since F1r"),
    ("I2: compared with I1, the latest stream before it", lambda ev: [mem_after(ev, "F1", "aaa"), mem_after(ev, "I1", "ddd")], "I2", "aaa", 4,
     "STOP: memories.db changed between I1 and I2: ddd -> aaa"),
]


def setup_order_check() -> tuple[bool, str]:
    """setup_stream.sh runs the memories gate after its gates and refusals and before anything is created (P2-M6): the gate's call and its
    `exit 4` come before the first `mkdir -p $STREAM` (the stream folder), the sandbox and the profile."""
    lines = (H / "setup_stream.sh").read_text().splitlines()
    code = [(i, ln) for i, ln in enumerate(lines) if not ln.lstrip().startswith("#")]
    call = next((i for i, ln in code if "memories_gate.py" in ln), None)
    stop = next((i for i, ln in code if call is not None and i > call and "exit 4" in ln), None)
    mk = next((i for i, ln in code if ln.lstrip().startswith("mkdir -p $STREAM")), None)
    sandbox = next((i for i, ln in code if ln.lstrip().startswith("mkdir -p $S/notes")), None)
    prof = next((i for i, ln in code if "profile-template.json >" in ln), None)
    good = None not in (call, stop, mk, sandbox, prof) and call < stop < mk < sandbox and stop < prof
    return good, f"gate call line {call and call + 1}, its exit 4 line {stop and stop + 1}, stream folder {mk and mk + 1}, sandbox " \
                 f"{sandbox and sandbox + 1}, profile {prof and prof + 1}"


def main(argv):
    out = Path(argv[argv.index("--out") + 1]) if "--out" in argv else Path("/tmp/p1-next-stream-check")
    base = out / "next-stream-cases"
    shutil.rmtree(base, ignore_errors=True)
    lines, ok = [], 0
    for n, (name, setup, want) in enumerate(CASES, 1):
        ev = base / f"{n:02d}"
        ev.mkdir(parents=True)
        setup(ev)
        r = subprocess.run(["zsh", str(H / "next_stream.sh")], capture_output=True, text=True,
                           env={**os.environ, "P1_NEXT_STREAM_EV": str(ev)})
        first = (r.stdout.strip().splitlines() or [""])[0]
        good = first.startswith(want) and (first == want if not want.startswith("REFUSED") else r.returncode == 3)
        ok += good
        lines.append(f"{'OK  ' if good else 'FAIL'} {name}: `{first}` (exit {r.returncode})" + ("" if good else f", want `{want}...`"))
    total = len(CASES)
    for n, (name, setup, label, cur, rc_want, want) in enumerate(MEM_CASES, 1):
        ev = base / f"m{n:02d}"
        ev.mkdir(parents=True)
        setup(ev)
        r = subprocess.run([sys.executable, "-B", str(H / "memories_gate.py"), "--ev", str(ev), "--label", label, "--current", cur],
                           capture_output=True, text=True)
        first = (r.stdout.strip().splitlines() or [""])[0]
        good = first.startswith(want) and r.returncode == rc_want
        ok += good
        total += 1
        lines.append(f"{'OK  ' if good else 'FAIL'} memories gate, {name}: `{first[:150]}` (exit {r.returncode})"
                     + ("" if good else f", want exit {rc_want} and `{want}...`"))
    good, detail = setup_order_check()
    ok += good
    total += 1
    lines.append(f"{'OK  ' if good else 'FAIL'} setup_stream.sh runs the memories gate before anything is created: {detail}")
    lines.append(f"next_stream_check: {ok} of {total} checks OK")
    text = "\n".join(lines)
    print(text)
    (out / "next_stream_check.out").write_text(text + "\n")
    return 0 if ok == total else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
