#!/usr/bin/env python3
"""P1 failed empty-argument call count (design 18.3 item 3; f-g0-7 section 1's definition; protocol 8).

An empty-argument failed call is a session-store `tool_call` record whose `toolName` is `tool_call` or `tool_load`, with `args` `{}` and
`status` `failed` (its `tool_result` reads `Tool "tool_call" is not available.`). The validity label and the probe's stop use this count;
the stderr grep (`is not available` in turn-*.stderr.txt) is reported beside it.

    python3 -B empty_calls.py <session-messages.jsonl>          prints `session-store empty-argument failed calls: N (tool_call a, tool_load b)`
    python3 -B empty_calls.py --selfcheck --out DIR             G0's six kept session stores against f-g0-7 section 1's counts (15/19/16, 0/0/0)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

G0 = Path("/Volumes/workspace/hirearchy/studies/G0-noise-baseline/evidence")
F_G0_7 = {"m0-s1": 15, "m0-s2": 19, "m0-s3": 16, "m1-s1": 0, "m1-s2": 0, "m1-s3": 0}  # f-g0-7 section 1


def count(path: Path) -> dict:
    n = {"tool_call": 0, "tool_load": 0}
    if not path.exists():
        return n
    for line in path.read_text(errors="replace").splitlines():
        try:
            r = json.loads(line)
        except json.JSONDecodeError:
            continue
        p = r.get("payload")
        p = json.loads(p) if isinstance(p, str) else (p or {})
        if p.get("type") == "tool_call" and p.get("toolName") in n and p.get("args") == {} and p.get("status") == "failed":
            n[p["toolName"]] += 1
    return n


def line(n: dict) -> str:
    return f"session-store empty-argument failed calls: {sum(n.values())} (tool_call {n['tool_call']}, tool_load {n['tool_load']})"


def main(argv):
    if "--selfcheck" in argv:
        out = Path(argv[argv.index("--out") + 1])
        lines, ok = [], 0
        for lab, want in F_G0_7.items():
            got = sum(count(G0 / lab / "assistant-session-messages.jsonl").values())
            ok += got == want
            lines.append(f"{'OK  ' if got == want else 'FAIL'} G0 {lab}: {got} (f-g0-7 section 1: {want})")
        lines.append(f"empty_calls: {ok} of {len(F_G0_7)} checks OK")
        text = "\n".join(lines)
        print(text)
        out.mkdir(parents=True, exist_ok=True)
        (out / "empty_calls.out").write_text(text + "\n")
        return 0 if ok == len(F_G0_7) else 1
    print(line(count(Path(argv[0]))))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
