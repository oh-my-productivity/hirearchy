#!/usr/bin/env python3
"""P1 self-check part: probe_compare.py on constructed probe folders (design 18.3 item 2; review finding M10).

The four sessions are written in the session-store shape of the kept G0 evidence (`payload` records `session_start`, `tool_call` with
`toolName`/`args`/`status`, `tool_result` with `content`; a `tool_load` result's `loaded` list of {tool_id, description, input_schema}).
Expected outcomes are 18.3's: a different load order or an extra tool is not a stop; a different description, a failed empty-argument
call, a failed positive control or a different non-[tool] stderr line is.

    python3 -B probe_check.py --out DIR   ->  one line per case and `probe_check: <ok> of <n> checks OK`
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

H = Path(__file__).resolve().parent
TOOLS = {"hirearchy::whoami": "Your address, role, budget.", "hirearchy::services": "The standing services.",
         "hirearchy::observe": "What ran or failed."}


def session(d: Path, arm: str, loads=(("hirearchy::whoami", "hirearchy::services"),), desc=None, empty=False, contract=None,
            stderr="[tool] whoami\n"):
    d.mkdir(parents=True)
    (d / "sandbox-path.txt").write_text(f"/tmp/hirearchy-p1-probe-{d.name}-1792000000\n")
    recs = [{"type": "session_start", "content": {"memories": "the owner's index", "cwd": f"/tmp/hirearchy-p1-probe-{d.name}-1792000000"}}]
    n = 0
    for ids in loads:
        n += 1
        recs.append({"type": "tool_call", "toolCallId": f"c{n}", "toolName": "tool_load", "args": {"tool_ids": list(ids)}, "status": "completed"})
        loaded = [{"tool_id": t, "description": (desc or {}).get(t, TOOLS[t]), "input_schema": {"type": "object", "properties": {}}}
                  for t in ids]
        recs.append({"type": "tool_result", "toolCallId": f"c{n}", "content": json.dumps({"loaded": loaded, "note": "These tools are now loaded."})})
    if empty:
        recs.append({"type": "tool_call", "toolCallId": "e1", "toolName": "tool_call", "args": {}, "status": "failed"})
        recs.append({"type": "tool_result", "toolCallId": "e1", "content": 'Tool "tool_call" is not available.'})
    v = contract or ("2" if arm == "F" else "1")
    recs.append({"type": "tool_call", "toolCallId": "s1", "toolName": "tool_call", "args": {"tool_id": "hirearchy::services"}, "status": "completed"})
    recs.append({"type": "tool_result", "toolCallId": "s1", "content": f"- probe-memo (offered by lead; contract v{v}, playbook v1)"})
    (d / "session-messages.jsonl").write_text("\n".join(json.dumps({"payload": r}) for r in recs) + "\n")
    (d / "turn-01.stderr.txt").write_text(stderr)
    if arm == "F":
        (d / "lock-checks.txt").write_text("check 1 (reply): yes\ncheck 2 (locked: true, version = before + 1): yes\ncheck 3 (the owner's quiet note): yes\n")


CASES = [  # (name, per-session kwargs, expected end)
    ("equal sessions, another load order and split in F1", {"F1": {"loads": (("hirearchy::services",), ("hirearchy::whoami",))}}, "PROBE: PASS"),
    ("F2 loads one more tool", {"F2": {"loads": (("hirearchy::whoami", "hirearchy::services"), ("hirearchy::observe",))}}, "PROBE: PASS"),
    ("I2's services description differs", {"I2": {"desc": {"hirearchy::services": "Another text."}}}, "PROBE: STOP"),
    ("a failed empty-argument call in F1", {"F1": {"empty": True}}, "PROBE: STOP"),
    ("the positive control fails in F2 (contract v1)", {"F2": {"contract": "1"}}, "PROBE: STOP"),
    ("a different non-[tool] stderr line in I1", {"I1": {"stderr": "[tool] whoami\nWarning: something else 3\n"}}, "PROBE: STOP"),
]


def main(argv):
    out = Path(argv[argv.index("--out") + 1]) if "--out" in argv else Path("/tmp/p1-probe-check")
    base = out / "probe-cases"
    shutil.rmtree(base, ignore_errors=True)
    lines, ok = [], 0
    for n, (name, mods, want) in enumerate(CASES, 1):
        pr = base / f"{n:02d}"
        for s in ("F1", "I1", "I2", "F2"):
            session(pr / s, s[0], **mods.get(s, {}))
        r = subprocess.run([sys.executable, "-B", str(H / "probe_compare.py"), str(pr)], capture_output=True, text=True)
        last = (r.stdout.strip().splitlines() or [""])[-1]
        good = last.startswith(want)
        ok += good
        lines.append(f"{'OK  ' if good else 'FAIL'} {name}: {last[:200]}" + ("" if good else f" (want {want})"))
    lines.append(f"probe_check: {ok} of {len(CASES)} checks OK")
    text = "\n".join(lines)
    print(text)
    (out / "probe_check.out").write_text(text + "\n")
    return 0 if ok == len(CASES) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
