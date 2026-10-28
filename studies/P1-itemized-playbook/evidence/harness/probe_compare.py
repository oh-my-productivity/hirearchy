#!/usr/bin/env python3
"""P1 probe comparison (design 18.3 item 2; F-G0-7 section 4 item 2). Usage: probe_compare.py <probe dir with F1/ I1/ I2/ F2/>

Compares the four probe sessions, after masking only what the sessions' own names explain (the sandbox path -> <S>, the probe label ->
<L>, ISO times -> <T>, UUIDs -> <U>):
  1. the whole `session_start` content (the memories block included: equal in both arms), by md5;
  2. every `tool_load` result by md5, per loaded tool: a map tool id -> md5 of its masked entry (description and input_schema) of the
     result's `loaded` list (plus the reply's other text); a tool loaded in both arms with different hashes stops the study; a tool loaded
     in some sessions only is reported, not a stop (the assistant chooses what to load and in which order);
  3. the stderr lines that do not start with `[tool]`, every digit masked, as multisets;
  4. the failed empty-argument calls: the session-store count of f-g0-7 section 1 (empty_calls.py: a `tool_call`/`tool_load` record with
     `args {}`, `status failed`); any > 0 in either arm stops the study; the stderr grep `is not available` is reported beside it;
  5. the positive control, the one expected difference: root's turn-2 `services` result names the service with `contract v2` in arm F and
     `contract v1` in arm I (`- {name} (offered by {owner}; contract v{n}, playbook v{m})`); arm F's lock checks (lock-checks.txt) all yes.
`tool_call` results are not compared otherwise. Prints one line per check and ends `PROBE: PASS`, or `PROBE: STOP: <each difference>`."""
import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import empty_calls  # noqa: E402

UUID = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", re.I)
TIME = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?")


def md5(s: str) -> str:
    return hashlib.md5(s.encode()).hexdigest()


def rows(d: Path):
    for line in (d / "session-messages.jsonl").read_text().splitlines():
        r = json.loads(line)
        p = r["payload"]
        yield json.loads(p) if isinstance(p, str) else p


def mask(s: str, d: Path) -> str:
    P = (d / "sandbox-path.txt").read_text().strip()
    s = s.replace(P, "<S>").replace("/private" + "<S>", "<S>").replace(f"probe-{d.name}", "<L>")
    return UUID.sub("<U>", TIME.sub("<T>", s))


def facts(d: Path) -> dict:
    ss, loads, calls, results = None, {}, {}, []
    for p in rows(d):
        t = p.get("type")
        if t == "session_start" and ss is None:
            ss = mask(json.dumps(p.get("content"), sort_keys=True), d)
        elif t == "tool_call":
            calls[p.get("toolCallId")] = p
        elif t == "tool_result":
            c = p.get("content")
            c = c if isinstance(c, str) else json.dumps(c, sort_keys=True)
            call = calls.get(p.get("toolCallId")) or {}
            name = call.get("toolName", "?")
            if name == "tool_load":
                try:
                    j = json.loads(c)
                except json.JSONDecodeError:
                    j = None
                if isinstance(j, dict) and isinstance(j.get("loaded"), list):
                    for e in j["loaded"]:
                        tid = str(e.get("tool_id"))
                        loads.setdefault(tid, md5(mask(json.dumps({k: v for k, v in e.items() if k != "tool_id"}, sort_keys=True), d)))
                    loads.setdefault("(the reply's other text)", md5(mask(json.dumps({k: v for k, v in j.items() if k != "loaded"},
                                                                                     sort_keys=True), d)))
                else:
                    ids = ",".join(sorted(str(x) for x in ((call.get("args") or {}).get("tool_ids") or [])))
                    loads.setdefault(f"(unparsed reply for {ids})", md5(mask(c, d)))
            results.append((name, c))
    err, grep = [], 0
    for f in sorted(d.glob("turn-*.stderr.txt")):
        for ln in f.read_text(errors="replace").splitlines():
            if "is not available" in ln:
                grep += 1
            if ln.strip() and not ln.startswith("[tool]"):
                err.append(re.sub(r"\d", "#", mask(ln, d)))
    services = [c for n, c in results if n == "tool_call" and "offered by" in c]
    empty = sum(empty_calls.count(d / "session-messages.jsonl").values())
    return {"session_start": md5(ss or ""), "tool_loads": loads, "stderr": Counter(err), "empty": empty, "grep": grep, "services": services}


def main(argv):
    pr = Path(argv[0])
    F = {s: facts(pr / s) for s in ("F1", "F2", "I1", "I2") if (pr / s / "session-messages.jsonl").exists()}
    stops, out = [], []
    if len(F) != 4:
        stops.append(f"sessions found: {sorted(F)} (need F1, F2, I1, I2)")
    else:
        same = len({F[s]["session_start"] for s in F}) == 1
        out.append(f"session_start: {'equal in all four sessions' if same else 'DIFFERS: ' + json.dumps({s: F[s]['session_start'] for s in F})}")
        if not same:
            stops.append("session_start differs")
        for tid in sorted({k for s in F for k in F[s]["tool_loads"]}):
            got = {s: F[s]["tool_loads"][tid] for s in F if tid in F[s]["tool_loads"]}
            if len(set(got.values())) > 1:
                out.append(f"tool_load {tid}: DIFFERS {json.dumps(got)}")
                stops.append(f"the tool_load result of {tid} differs")
            elif len(got) < 4:
                out.append(f"tool_load {tid}: equal where loaded; loaded in {', '.join(sorted(got))} only (reported, not a stop)")
            else:
                out.append(f"tool_load {tid}: equal in all four sessions")
        base = F["I1"]["stderr"]
        for s in F:
            if F[s]["stderr"] != base:
                stops.append(f"non-[tool] stderr of {s} differs from I1's: {dict(F[s]['stderr'] - base)} / {dict(base - F[s]['stderr'])}")
        out.append("non-[tool] stderr lines (digits masked): " + ("equal" if not any("stderr" in x for x in stops) else "DIFFER"))
        for s in F:
            out.append(f"failed empty-argument calls {s}: {F[s]['empty']} (session store, f-g0-7 section 1); "
                       f"'is not available' in stderr: {F[s]['grep']} (reported)")
            if F[s]["empty"]:
                stops.append(f"{s} has {F[s]['empty']} failed empty-argument call(s)")
        for s in F:
            want = "contract v2" if s.startswith("F") else "contract v1"
            other = "contract v1" if s.startswith("F") else "contract v2"
            got = any(want in c and "probe-memo" in c for c in F[s]["services"]) and not any(other in c and "probe-memo" in c for c in F[s]["services"])
            out.append(f"positive control {s}: root's services names probe-memo with {want}: {'yes' if got else 'NO'}")
            if not got:
                stops.append(f"positive control failed in {s} (want {want})")
        for s in ("F1", "F2"):
            lc = (pr / s / "lock-checks.txt")
            ok = lc.exists() and lc.read_text().count(": yes") == 3
            out.append(f"lock checks {s}: {'3 of 3 yes' if ok else 'NOT all yes'}")
            if not ok:
                stops.append(f"the lock checks of {s} failed")
    print("\n".join(out))
    print("PROBE: PASS" if not stops else "PROBE: STOP: " + "; ".join(stops))
    return 0 if not stops else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
