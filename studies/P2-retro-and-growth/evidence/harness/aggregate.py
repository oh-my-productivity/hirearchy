#!/usr/bin/env python3
"""P2 aggregation and the exit verdict (protocol 12.5). Usage: aggregate.py <EV> [--out EV/aggregate.md] | --selfcheck <dir>

Per stream: each pass rule's verdict from <label>/p2/verdicts.txt (P2-X1, P2-X2, P2-X3, P2-L, P2-B, P2-W); P1's gate-able measures from
<label>/p2/gate_p1.json (`flat`: one verdict per measure); validity from <label>/measures/validity.json (keys valid, reason, arm_contrast,
before_failure, ended_by_ruling, stopped; any other key, or a before_failure key outside the six rules or a value other than "FAIL", is an
error: exit 2). A missing file or line is NOT DETERMINED, never PASS.
Per arm R, each pass rule: PASS (n of n valid streams) with at least 3 valid streams and every one PASS; FAIL (in <streams>) when a valid
stream FAILs or a before_failure says FAIL; else NOT DETERMINED (P2-X2 names the streams where it was not reached).
P1's gate-able measures (design 17.4 and 18.1's last item; F1 of the review): each measure, over every valid stream of BOTH arms: PASS when
it reads PASS (or VACUOUS where protocol 12.3 pre-registers it: G1(b)) in every one; FAIL (in <streams>) when one reads FAIL; else NOT
DETERMINED. A valid stream without gate_p1.json makes every measure NOT DETERMINED.
The exit criterion: PASS iff the six rules and every gate-able measure read PASS; FAIL iff one reads FAIL; else NOT DETERMINED.
"""
import json
import re
import sys
from pathlib import Path

RULES = ["P2-X1", "P2-X2", "P2-X3", "P2-L", "P2-B", "P2-W"]
KEYS = {"valid", "reason", "arm_contrast", "before_failure", "ended_by_ruling", "stopped"}
LABELS = ["R1", "R1r", "R2", "R2r", "R3", "R3r", "C1", "C1r", "C2", "C2r", "C3", "C3r"]
GATE = ["G1(a)", "G1(b)", "G1(c)", "G1(d)", "G1(e)", "G1(f)", "G2(a)", "G2(b)", "G2(c)", "escapes typed by the user's answer",
        "relayed reworks sent by the assistant (the injection excepted)", "hand edits", "injected lessons", "empty-argument calls",
        "delivered versions (P2's form)", "deliveries by copy"]
VACUOUS_OK = {"G1(b)"}


class ScoringError(Exception):
    pass


def stream_verdicts(d: Path) -> dict:
    out = {r: "NOT DETERMINED (no verdict line)" for r in RULES}
    f = d / "p2" / "verdicts.txt"
    for ln in f.read_text().splitlines() if f.is_file() else []:
        m = re.match(r"^(P2-X1|P2-X2|P2-X3|P2-L|P2-B|P2-W|P2-E|P2-S): (.*)$", ln)
        if m:
            out[m.group(1)] = m.group(2)
    return out


def gate_verdicts(d: Path) -> dict:
    f = d / "p2" / "gate_p1.json"
    try:
        fl = json.loads(f.read_text())["flat"]
    except Exception:
        return {g: "NOT DETERMINED (no gate_p1.json)" for g in GATE}
    return {g: str(fl.get(g, "NOT DETERMINED (no line)")) for g in GATE}


def validity(d: Path) -> dict:
    f = d / "measures" / "validity.json"
    if not f.is_file():
        return {"valid": None}
    v = json.loads(f.read_text())
    if set(v) - KEYS:
        raise ScoringError(f"{f}: unknown keys {sorted(set(v) - KEYS)}")
    for k, x in (v.get("before_failure") or {}).items():
        if k not in RULES or x != "FAIL":
            raise ScoringError(f"{f}: before_failure {k}: {x}")
    return v


def arm_line(rule: str, streams: dict) -> str:
    valid = [l for l, s in streams.items() if s["validity"].get("valid") is True]
    fails = [l for l, s in streams.items() if (l in valid and s["v"][rule].startswith("FAIL")) or (s["validity"].get("before_failure") or {}).get(rule) == "FAIL"]
    if fails:
        return f"FAIL (in {', '.join(fails)})"
    if len(valid) >= 3 and all(streams[l]["v"][rule].startswith("PASS") for l in valid):
        return f"PASS ({len(valid)} of {len(valid)} valid streams)"
    nr = [l for l in valid if streams[l]["v"][rule].startswith("NOT REACHED")]
    why = f"X2 not reached in {', '.join(nr)}" if nr else f"{len(valid)} valid stream(s); " + "; ".join(f"{l}: {streams[l]['v'][rule][:60]}" for l in valid if not streams[l]["v"][rule].startswith("PASS"))
    return f"NOT DETERMINED ({why})"


def gate_line(g: str, streams: dict) -> str:
    valid = [l for l, s in streams.items() if s["validity"].get("valid") is True]
    if not valid:
        return "NOT DETERMINED (no valid stream)"
    ok = lambda v: v.startswith("PASS") or (g in VACUOUS_OK and v.startswith("VACUOUS"))  # noqa: E731
    fails = [l for l in valid if streams[l]["g"][g].startswith("FAIL")]
    if fails:
        return f"FAIL (in {', '.join(fails)})"
    if all(ok(streams[l]["g"][g]) for l in valid):
        return f"PASS ({len(valid)} of {len(valid)} valid streams of both arms)"
    return "NOT DETERMINED (" + "; ".join(f"{l}: {streams[l]['g'][g][:60]}" for l in valid if not ok(streams[l]["g"][g])) + ")"


def aggregate(ev: Path) -> str:
    streams = {l: {"v": stream_verdicts(ev / l), "g": gate_verdicts(ev / l), "validity": validity(ev / l)} for l in LABELS if (ev / l).is_dir()}
    R = {l: s for l, s in streams.items() if l.startswith("R")}
    lines = ["# P2 aggregate (protocol 12.5)", "", "## The pass rules (arm R)"]
    parts = {}
    for rule in RULES:
        parts[rule] = arm_line(rule, R)
        lines.append(f"- `{rule} (arm R)`: {parts[rule]}")
    lines += ["", "## P1's gate-able measures (every valid stream of both arms)"]
    for g in GATE:
        parts[g] = gate_line(g, streams)
        lines.append(f"- `{g}`: {parts[g]}")
    ex = "FAIL" if any(v.startswith("FAIL") for v in parts.values()) else ("PASS" if all(v.startswith("PASS") for v in parts.values()) else "NOT DETERMINED")
    why = [k for k, v in parts.items() if not v.startswith("PASS")]
    lines += ["", f"**Phase 2's exit criterion: {ex}**" + (f" (not PASS: {', '.join(why)})" if why else ""), "", "## Per stream"]
    for l, s in streams.items():
        lines.append(f"- {l} (valid {s['validity'].get('valid')}): " + "; ".join(f"{k} {v[:80]}" for k, v in s["v"].items()))
        lines.append("  - gate-able: " + "; ".join(f"{k} {v[:50]}" for k, v in s["g"].items()))
        lines.append("  - " + product_findings(ev / l, l))
    return "\n".join(lines) + "\n"


def product_findings(d: Path, label: str) -> str:
    """Protocol 12.6 (4): the known product findings PF-0 and PF-1 and the new P2-E findings, counted per stream (p2/P2-E.json counts)."""
    if label.startswith("C"):
        return "product findings (P2-E): n/a (arm C has no brief)"
    try:
        c = json.loads((d / "p2" / "P2-E.json").read_text())["counts"]
        return f"product findings (P2-E): PF-0 {c.get('PF-0', 0)}, PF-1 {c.get('PF-1', 0)}, new {c.get('new', 0)}"
    except Exception:
        return "product findings (P2-E): NOT DETERMINED (no p2/P2-E.json counts)"


def selfcheck(out: Path) -> int:
    ok = []
    gpass = {g: "PASS" for g in GATE} | {"G1(b)": "VACUOUS (no item reached `retire due`)"}
    for case, verdicts, valid, gate, want in (
            ("three PASS and every gate-able measure PASS (G1(b) VACUOUS)", {l: "PASS" for l in RULES}, True, {}, "PASS"),
            ("one FAIL", {**{l: "PASS" for l in RULES}, "P2-X3": "FAIL (edits)"}, True, {}, "FAIL"),
            ("X2 not reached", {**{l: "PASS" for l in RULES}, "P2-X2": "NOT REACHED (x)"}, True, {}, "NOT DETERMINED"),
            ("two valid streams only", {l: "PASS" for l in RULES}, "two", {}, "NOT DETERMINED"),
            ("F1: a gate-able FAIL in an arm-C stream fails the exit", {l: "PASS" for l in RULES}, True, {"C1": {"hand edits": "FAIL (1 of 6)"}}, "FAIL"),
            ("F1: a judged key missing leaves the exit NOT DETERMINED", {l: "PASS" for l in RULES}, True, {"R2": {"G1(d)": "NOT DETERMINED (judged)"}}, "NOT DETERMINED"),
            ("F1: VACUOUS is not PASS outside G1(b)", {l: "PASS" for l in RULES}, True, {"R1": {"G1(e)": "VACUOUS"}}, "NOT DETERMINED"),
            ("F1: a stream without gate_p1.json", {l: "PASS" for l in RULES}, True, {"C2": None}, "NOT DETERMINED")):
        ev = out / re.sub(r"\W+", "-", case)[:60]
        for i, l in enumerate(["R1", "R2", "R3", "C1", "C2", "C3"]):
            (ev / l / "p2").mkdir(parents=True, exist_ok=True)
            (ev / l / "measures").mkdir(parents=True, exist_ok=True)
            (ev / l / "p2" / "verdicts.txt").write_text("\n".join(f"{k}: {v}" for k, v in verdicts.items()) + "\n")
            (ev / l / "measures" / "validity.json").write_text(json.dumps({"valid": (i % 3 < 2) if valid == "two" else True, "reason": ""}))
            g = gate.get(l, {})
            if g is None:
                (ev / l / "p2" / "gate_p1.json").unlink(missing_ok=True)
            else:
                (ev / l / "p2" / "gate_p1.json").write_text(json.dumps({"flat": {**gpass, **g}}))
        got = re.search(r"exit criterion: (\w+(?: \w+)?)\*\*", aggregate(ev)).group(1)
        ok.append((case, want, got))
    ev = out / "pf-counts"
    for l in ("R1", "C1"):
        (ev / l / "p2").mkdir(parents=True, exist_ok=True)
        (ev / l / "measures").mkdir(parents=True, exist_ok=True)
        (ev / l / "measures" / "validity.json").write_text(json.dumps({"valid": True, "reason": ""}))
    (ev / "R1" / "p2" / "P2-E.json").write_text(json.dumps({"verdict": "MISMATCH", "counts": {"PF-0": 0, "PF-1": 2, "new": 1}}))
    t = aggregate(ev)
    ok.append(("12.6 (4): PF-0, PF-1 and new findings counted per stream (arm C n/a)", "yes",
               "yes" if "PF-0 0, PF-1 2, new 1" in t and "n/a (arm C has no brief)" in t else "no"))
    ev = out / "bad-key"
    (ev / "R1" / "measures").mkdir(parents=True, exist_ok=True)
    (ev / "R1" / "measures" / "validity.json").write_text(json.dumps({"valid": True, "before_failure": {"no regression": "FAIL"}}))
    try:
        aggregate(ev)
        ok.append(("a bad before_failure key is refused", "error", "no error"))
    except ScoringError:
        ok.append(("a bad before_failure key is refused", "error", "error"))
    lines = [f"{'ok' if w == g else 'MISMATCH'}  {c}: expected {w}, got {g}" for c, w, g in ok]
    lines.append(f"aggregate selfcheck: {sum(w == g for _, w, g in ok)} of {len(ok)} ok")
    print("\n".join(lines))
    return 0 if all(w == g for _, w, g in ok) else 1


def main() -> int:
    if sys.argv[1:2] == ["--selfcheck"]:
        return selfcheck(Path(sys.argv[2]))
    ev = Path(sys.argv[1])
    out = Path(sys.argv[sys.argv.index("--out") + 1]) if "--out" in sys.argv else ev / "aggregate.md"
    try:
        text = aggregate(ev)
    except ScoringError as e:
        print(f"aggregate.py: {e}", file=sys.stderr)
        return 2
    out.write_text(text)
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
