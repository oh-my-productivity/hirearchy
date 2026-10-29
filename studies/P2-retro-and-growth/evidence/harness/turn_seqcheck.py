#!/usr/bin/env python3
"""P2 turn.sh's sequence check (protocol 3.2; protocol amendment 1 item 5 (A)). Usage: turn_seqcheck.py <evidence dir D> <turn n>

Prints ONE line, which turn.sh appends to turn-NN.wrapper.txt:
  `after_turn sequential: checked (turn end <t> + <b> s <= first snapshot <s>)`  the first snapshot started at or after the boundary;
  `after_turn sequential: checked (no snapshot taken: no org yet)`              the snapshot's own record `turn-NN <utc>: no org yet ...`;
  `STOP: ...`                                                                    anything else: a snapshot before the boundary, an
      unparseable time (in turn-times.txt or quality/calls.txt), no turn-times.txt line, or no snapshot record of this turn at all.
The frozen check (inline in turn.sh before amendment 1) parsed times with two strptime forms that reject a `+00:00` offset, which
snapshot_cli.sh writes (`datetime.isoformat()`), and read any unparsed time as "no snapshot", so it passed every turn from the first org on
(`R1/harness-failures/turn-sh-sequence-check-vacuous.md`). This check parses ISO 8601 with `Z`, `+HH:MM`/`-HH:MM` or no offset (UTC) and
up to 6 fraction digits, and fails closed on any other time.
"""
from __future__ import annotations

import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ISO = re.compile(r"^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})(\.\d{1,6})?(Z|[+-]\d{2}:\d{2})?$")


def parse(s: str) -> datetime | None:
    """An ISO 8601 time as written by the harness (date -u +%FT%TZ, %6N, or Python's isoformat), as an aware datetime; None if not one."""
    m = ISO.match(s or "")
    if not m:
        return None
    off = m.group(3)
    txt = m.group(1) + (m.group(2) or "") + ("+00:00" if off in (None, "Z") else off)
    try:
        return datetime.fromisoformat(txt).astimezone(timezone.utc)
    except ValueError:
        return None


def check(D: Path, T: int) -> str:
    end_s = bound = None
    tt = D / "turn-times.txt"
    for ln in (tt.read_text(errors="replace").splitlines() if tt.exists() else []):
        m = re.match(rf"^turn {T}: .*utc \S+ - (\S+)\s+exit \S+\s+sleep (\d+) ended utc (\S+)", ln)
        if m:
            end_s, bound = m.group(1), int(m.group(2))
    if end_s is None:
        return f"STOP: turn {T} has no turn-times.txt line"
    end = parse(end_s)
    if end is None:
        return f"STOP: unparseable turn end {end_s!r} in turn-times.txt (turn {T}; the sequence check fails closed)"
    calls = D / "quality" / "calls.txt"
    if not calls.exists():
        return f"STOP: no snapshot record of turn {T} (quality/calls.txt is missing; the sequence check fails closed)"
    first_s = noorg = None
    for ln in calls.read_text(errors="replace").splitlines():
        m = re.match(rf"^turn-{T:02d} start (\S+)", ln)
        if m:
            first_s = m.group(1)
            break
        if noorg is None and re.match(rf"^turn-{T:02d} \S+: no org yet, quality not run$", ln):
            noorg = ln
    if first_s is None:
        if noorg is not None:
            return "after_turn sequential: checked (no snapshot taken: no org yet)"
        return f"STOP: no snapshot record of turn {T} in quality/calls.txt (the sequence check fails closed)"
    first = parse(first_s)
    if first is None:
        return f"STOP: unparseable first snapshot time {first_s!r} in quality/calls.txt (turn {T}; the sequence check fails closed)"
    if first >= end + timedelta(seconds=bound):
        return f"after_turn sequential: checked (turn end {end.isoformat()} + {bound} s <= first snapshot {first.isoformat()})"
    return f"STOP: snapshot before the boundary (turn end {end.isoformat()} + {bound} s > first snapshot {first.isoformat()})"


if __name__ == "__main__":
    if len(sys.argv) != 3 or not sys.argv[2].isdigit():
        print("usage: turn_seqcheck.py <evidence dir> <turn n>", file=sys.stderr)
        sys.exit(2)
    print(check(Path(sys.argv[1]), int(sys.argv[2])))
