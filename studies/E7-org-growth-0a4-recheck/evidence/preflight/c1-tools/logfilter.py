#!/usr/bin/env python3
"""C1 log filter (stdlib only; DR-0a4-4 fallback). Streams --file line by line and prints ONLY lines that are stamped within [start, end] AND carry
the pid, the session id, or one of: signal, kill, shutdown, terminate. Lines without a parseable leading timestamp are skipped. Nothing else of the
file is printed, kept or copied. A naive timestamp is read as UTC.
"""
from __future__ import annotations

import argparse
import datetime
import re
import sys

STAMP = re.compile(r"^\W{0,3}(\d{4}-\d{2}-\d{2})[T ](\d{2}:\d{2}:\d{2})(\.\d+)?(Z|[+-]\d{2}:?\d{2})?")
WORDS = ("signal", "kill", "shutdown", "terminate")


def parse(ts: str) -> datetime.datetime:
    d = datetime.datetime.fromisoformat(ts.replace("Z", "+00:00"))
    return d if d.tzinfo else d.replace(tzinfo=datetime.timezone.utc)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", required=True)
    ap.add_argument("--start", required=True)
    ap.add_argument("--end", required=True)
    ap.add_argument("--pid", required=True)
    ap.add_argument("--session", required=True)
    a = ap.parse_args()
    start, end = parse(a.start), parse(a.end)
    pid_re = re.compile(r"(?<!\d)" + re.escape(a.pid) + r"(?!\d)")
    n = 0
    try:
        fh = open(a.file, errors="replace")
    except OSError as e:
        print(f"cannot open: {e.strerror}")
        return 0
    with fh:
        for line in fh:
            m = STAMP.match(line)
            if not m:
                continue
            try:
                t = parse(m.group(1) + "T" + m.group(2) + (m.group(3) or "") + (m.group(4) or ""))
            except ValueError:
                continue
            if not (start <= t <= end):
                continue
            low = line.lower()
            if pid_re.search(line) or (a.session and a.session in line) or any(w in low for w in WORDS):
                print(line.rstrip("\n")[:600])
                n += 1
    print(f"# {n} line(s) selected")
    return 0


if __name__ == "__main__":
    sys.exit(main())
