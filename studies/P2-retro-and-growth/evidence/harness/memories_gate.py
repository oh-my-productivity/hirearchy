#!/usr/bin/env python3
"""P2 (P1's memories gate with P2's order) memories gate between two streams (protocol 3 and 8; design 18.2; the brief: "If it changed, send a warning before the next stream
and wait"). Called by setup_stream.sh before anything of the stream is created (no folder, sandbox or profile yet).

    python3 -B memories_gate.py --ev <EV> --label <label> --current <md5 of ~/.kiro/memories/memories.db, or "absent">

It compares <current> with the `memories-md5-after.txt` of the previous stream in the pre-registered order (R1, C1, R2, C2, R3, C3, each
followed by its replacement <label>r when evidence/manager-decision-replacement-<label>.md exists): the latest stream before <label> in
that order that has the file. It reads md5 values only (never the store). Exit and first line:
  0  `memories gate: ...` (no previous stream, unchanged, or changed with the manager's decision
     <EV>/manager-decision-memories-before-<label>.md recorded);
  4  `STOP: memories.db changed between <prev> and <label>: <a> -> <b> ...` (a change between two streams stops the study before the next
     one exactly as a change during a stream does: both arms read the same memory index, 18.2);
  2  usage.
"""
from __future__ import annotations

import sys
from pathlib import Path

ORDER = ["R1", "C1", "R2", "C2", "R3", "C3"]


def sequence(ev: Path, label: str) -> list[str]:
    seq = []
    for lab in ORDER:
        seq.append(lab)
        if (ev / f"manager-decision-replacement-{lab}.md").exists() or label == f"{lab}r":
            seq.append(f"{lab}r")
    return seq


def gate(ev: Path, label: str, current: str) -> tuple[int, str]:
    seq = sequence(ev, label)
    if label not in seq:
        return 2, f"memories gate: {label} is not a P1 stream label"
    prev = next((p for p in reversed(seq[:seq.index(label)]) if (ev / p / "memories-md5-after.txt").exists()), None)
    if prev is None:
        return 0, f"memories gate: no previous stream before {label}: nothing to compare (memories.db {current})"
    before = (ev / prev / "memories-md5-after.txt").read_text().strip()
    if before == current:
        return 0, f"memories gate: memories.db unchanged since {prev}'s end ({current})"
    dec = ev / f"manager-decision-memories-before-{label}.md"
    if dec.exists():
        return 0, (f"memories gate: memories.db changed between {prev} and {label} ({before} -> {current}); the manager decided "
                   f"({dec.name}): {label} may start")
    return 4, (f"STOP: memories.db changed between {prev} and {label}: {before} -> {current}. Send a warning and wait: {label} starts only "
               f"after the manager's decision is recorded in {dec.name} (protocol 8; the store is never restored or edited)")


def main(argv):
    args = list(argv)
    try:
        ev = Path(args[args.index("--ev") + 1])
        label = args[args.index("--label") + 1]
        current = args[args.index("--current") + 1].strip()
    except (ValueError, IndexError):
        print(__doc__)
        return 2
    rc, line = gate(ev, label, current)
    print(line)
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
