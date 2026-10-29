#!/usr/bin/env python3
"""P2: write the injection's window.txt from E7's injection log (protocol 3.4, E7 5.3's last bullet; protocol amendment 1 item 5 (C)).

    python3 -B injection_window.py <S>/injection

E7 5.3: "After the window the stream step writes S/injection/window.txt: `<request time> <final progress time>`". In R1 v1 the facilitator
did not write it, so the finish's `injection_files` step exited 2 (`R1/harness-failures/finish-r1-v1-findings.md` item 1). injection.sh now
runs this right after E7's script returns, so no facilitator step is needed. The times are the log's own lines, written by E7's script:
the last `window start (request): <UTC>Z ...` and the first `window end (final progress): <UTC>Z ...` after it, each written without its
`Z`, one line, as P1's streams kept it (`2026-10-28T02:17:34 2026-10-28T02:21:05`). Prints one line:
  `window.txt written: <start> <end>`                     (exit 0)
  `window.txt kept: <start> <end> (already written)`      (exit 0; the same content)
  `NOTE: ... window.txt not written ...`                  (exit 1; no log, no window start, or no window end after it: the step reports it)
  `STOP: window.txt holds <x>, the log says <y> ...`      (exit 1; an existing different file is never overwritten)
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

START = re.compile(r"^window start \(request\): (\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})Z\b", re.M)
END = re.compile(r"^window end \(final progress\): (\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})Z\b", re.M)


def window(log: str) -> tuple[str, str] | None:
    starts = list(START.finditer(log))
    if not starts:
        return None
    s = starts[-1]
    e = END.search(log, s.end())
    return (s.group(1), e.group(1)) if e else None


def main(argv: list[str]) -> int:
    if len(argv) != 1:
        print("usage: injection_window.py <S>/injection", file=sys.stderr)
        return 2
    d = Path(argv[0])
    lf = d / "injection-log.txt"
    if not lf.exists():
        print(f"NOTE: no {lf}: window.txt not written (protocol 3.4)")
        return 1
    w = window(lf.read_text(errors="replace"))
    if w is None:
        print(f"NOTE: {lf} has no window start with a window end after it: window.txt not written (protocol 3.4; report it)")
        return 1
    want = f"{w[0]} {w[1]}\n"
    wf = d / "window.txt"
    if wf.exists():
        have = wf.read_text()
        if have == want:
            print(f"window.txt kept: {want.strip()} (already written)")
            return 0
        print(f"STOP: {wf} holds {have.strip()!r}, the log says {want.strip()!r}: not overwritten (protocol 3.4)")
        return 1
    wf.write_text(want)
    print(f"window.txt written: {want.strip()} ({wf})")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
