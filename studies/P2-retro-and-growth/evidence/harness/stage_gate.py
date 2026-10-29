#!/usr/bin/env python3
"""P2 stage-1 gate inputs (protocol 11; design 17.6's stop rule, exactly). Usage: stage_gate.py <EV> -> EV/stage-1-gate-inputs.json + text
                                                                            | --selfcheck <dir>
Item 1: each of R1's and C1's `stream total credits:` over 250.00 (a missing credits.txt: the item reads `unread`, listed under item 3).
Item 2: R1's retro 1 = the first ledger record at or after L0 (the CONDITION line's turn start; the written CONDITION, and the computed one
beside it: a disagreement is reported as a facilitator fact, H7); its items against the re-derivation as of its `at` alone
(rederive_p2.py --as-of): service_due without a `service` item, or checker_due without a `checker-add` item, holds the item. "X2 not
reached" is reported beside it and masks nothing (F20 of the review: K29's in-words VR-REJECT branch can fill a class).
Item 3: a harness check fails closed: every verdict of R1's and C1's p2/verdicts.txt and every value of their p2/gate_p1.json (`flat`,
P1's gate-able measures) whose reason starts `FAIL-CLOSED:`, and an unread verdicts.txt, gate_p1.json or credits.txt (F36 of review 2).
Self-check, view and P2-E/P2-S mismatches, and the judged keys' NOT DETERMINED (no prefix: judged.json is step 12's), are listed as
information, not as stop conditions. Its inputs come from `score_stream.sh R1` and `score_stream.sh C1`, run by the gate step first
(protocol 11, "The gate's inputs").
Item 4: validity.json (valid false), or before the scoring step stopped.txt and harness-failures/.
The gate step writes its prose from these and always asks the manager.
"""
import json
import re
import subprocess
import sys
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lena_lines as LL  # noqa: E402
import p2lib as L  # noqa: E402

H = Path(__file__).resolve().parent


def credits(d: Path):
    f = d / "credits.txt"
    m = re.search(r"^stream total credits: (\d+\.\d{2})", f.read_text(), re.M) if f.is_file() else None
    return Decimal(m.group(1)) if m else None


def gate(ev: Path, rederive=True) -> dict:
    res = {"item1": {}, "item2": None, "item3": [], "item4": {}, "information": [], "facts": []}
    for l in ("R1", "C1"):
        c = credits(ev / l)
        res["item1"][l] = {"credits": str(c) if c is not None else None, "over_250": None if c is None else c > Decimal("250.00")}
        if c is None:
            res["item3"].append(f"{l}: credits.txt unread (FAIL-CLOSED)")
        v = ev / l / "p2" / "verdicts.txt"
        if not v.is_file():
            res["item3"].append(f"{l}: p2/verdicts.txt unread (FAIL-CLOSED)")
        for ln in v.read_text().splitlines() if v.is_file() else []:
            if "FAIL-CLOSED:" in ln:
                res["item3"].append(f"{l}: {ln}")
            elif "MISMATCH" in ln:
                res["information"].append(f"{l}: {ln}")
        g = ev / l / "p2" / "gate_p1.json"
        try:
            flat = json.loads(g.read_text()).get("flat") or {}
        except Exception:
            flat = None
            res["item3"].append(f"{l}: p2/gate_p1.json unread (FAIL-CLOSED)")
        for k, val in (flat or {}).items():
            if "FAIL-CLOSED:" in str(val):
                res["item3"].append(f"{l}: gate_p1 {k}: {val}")
            elif str(val).startswith("NOT DETERMINED"):
                res["information"].append(f"{l}: gate_p1 {k}: {val}")
        for f in sorted((ev / l / "watch").glob("*/watch-mismatches.txt")):
            n = sum(1 for x in f.read_text().splitlines() if x.startswith("MISMATCH"))
            if n:
                res["information"].append(f"{l}: {n} view mismatch line(s) in {f.relative_to(ev)}")
        val = ev / l / "measures" / "validity.json"
        res["item4"][l] = json.loads(val.read_text()) if val.is_file() else {
            "stopped": (ev / l / "stopped.txt").read_text() if (ev / l / "stopped.txt").is_file() else None,
            "harness_failures": sorted(p.name for p in (ev / l / "harness-failures").glob("*"))}
    sc = ev / "harness-selfcheck" / "selfcheck-summary.txt"
    if sc.is_file() and "FAIL" in sc.read_text():
        res["information"].append("the self-check summary holds a FAIL line")
    d = ev / "R1"
    lena = LL.counts(str(d / "lena-lines.txt")) if (d / "lena-lines.txt").is_file() else {}
    if lena.get("condition_written") != lena.get("condition_turn"):
        res["facts"].append(f"H7 check: the written CONDITION is at turn {lena.get('condition_written')}, the computed one at turn {lena.get('condition_turn')}")
    starts = {}
    for ln in (d / "turn-times.txt").read_text().splitlines() if (d / "turn-times.txt").is_file() else []:
        m = re.match(r"^turn (\d+): .*utc (\S+) - ", ln)
        if m:
            starts[int(m.group(1))] = L.parse_time(m.group(2))
    l0 = lena.get("condition_written") or lena.get("condition_turn")
    recs = json.loads((d / "org-files" / "retros.json").read_text()).get("briefs", []) if (d / "org-files" / "retros.json").is_file() else []
    b = next((r for r in recs if l0 and starts.get(l0) and L.parse_time(r["at"]) >= starts[l0]), None)
    if b is None:
        res["item2"] = {"holds": None, "reason": "no retro 1 recorded in R1 at or after L0 (not determined: report it)"}
    else:
        out = d / "rederived" / "p2" / "gate-retro1"
        if rederive:
            subprocess.run([sys.executable, "-B", str(H / "rederive_p2.py"), str(d), "--out", str(out), "--as-of", b["at"]], capture_output=True)
        try:
            sig = json.loads((out / "signals.json").read_text())
        except Exception:
            res["item2"] = {"holds": None, "reason": "the re-derivation as of retro 1 is unread"}
            res["item3"].append("R1: rederived/p2/gate-retro1/signals.json unread (FAIL-CLOSED)")
            sig = None
        if sig is not None:
            kinds = {i["kind"] for i in b.get("items") or []}  # 17.6: the brief "lacks" an item it does not offer; held back is reported
            held = sorted({k.split("|", 1)[0] for k in b.get("held_back") or []})
            svc = bool(sig["service_due"]) and "service" not in kinds
            chk = bool(sig["checker_due"]) and "checker-add" not in kinds
            res["item2"] = {"brief": b["id"], "at": b["at"], "items": sorted(kinds), "service_due": sig["service_due"], "checker_due": sig["checker_due"],
                            "held_back (reported)": held, "x2_not_reached (reported)": lena.get("x2_not_reached"), "holds": bool(svc or chk),
                            "which": [x for x, y in (("service", svc), ("checker-add", chk)) if y]}
    stop = any(v.get("over_250") for v in res["item1"].values()) or bool((res["item2"] or {}).get("holds")) or bool(res["item3"]) \
        or any(v.get("valid") is False for v in res["item4"].values())
    res["stop"] = stop
    return res


def selfcheck(out: Path) -> int:
    """Constructed EV folders for each item of the stop rule (expectations from design 17.6)."""
    ok = []

    GP1 = {"G1(a)": "PASS", "G1(d)": "NOT DETERMINED (judged: measures/judged.json g1_d_judged)", "empty-argument calls": "PASS"}

    def mk(name, r1_credits="120.00", c1_credits="110.00", verdict_lines=("P2-X1: PASS",), items=("service", "checker-add"), due=(True, True),
           valid=True, cond=(12, 12), gp1=GP1):
        ev = out / name
        for l, c in (("R1", r1_credits), ("C1", c1_credits)):
            (ev / l / "p2").mkdir(parents=True, exist_ok=True)
            (ev / l / "measures").mkdir(parents=True, exist_ok=True)
            if c:
                (ev / l / "credits.txt").write_text(f"stream total credits: {c}\n")
            (ev / l / "p2" / "verdicts.txt").write_text("\n".join(verdict_lines) + "\n")
            (ev / l / "measures" / "validity.json").write_text(json.dumps({"valid": valid, "reason": ""}))
            if gp1 is not None:
                (ev / l / "p2" / "gate_p1.json").write_text(json.dumps({"flat": gp1}))
        d = ev / "R1"
        # F27 of review 2: L0 is the line that answers the third TRAP rejection's question (cond[1], computed); cond[0] is the written one
        (d / "lena-lines.txt").write_text(
            "turn 3 | rules TRAP-1@2026-10-12 | table rows none | facts: x\nturn 6 | rules TRAP-N@2026-10-19 | table rows none | facts: x\n"
            "turn 9 | rules TRAP-N@2026-10-26 | table rows none | facts: x\n"
            f"turn {cond[1]} | rules ANSWER{' + CONDITION' if cond[0] == cond[1] else ''} | table rows K29 | facts: answers TRAP-N@2026-10-26\n"
            + (f"turn {cond[0]} | rules CONDITION | table rows none | facts: x\n" if cond[0] != cond[1] else ""))
        (d / "turn-times.txt").write_text("\n".join(f"turn {n}: x  utc 2026-10-29T0{n % 10}:00:00+00:00 - x" for n in (3, 6, 9, cond[0], cond[1])) + "\n")
        (d / "org-files").mkdir(exist_ok=True)
        (d / "org-files" / "retros.json").write_text(json.dumps({"briefs": [{"id": "B1", "at": "2026-10-29T09:30:00+00:00", "since": "x",
                                                                             "items": [{"n": i + 1, "kind": k, "key": k} for i, k in enumerate(items)]}]}))
        (d / "rederived" / "p2" / "gate-retro1").mkdir(parents=True, exist_ok=True)
        (d / "rederived" / "p2" / "gate-retro1" / "signals.json").write_text(json.dumps({"service_due": due[0], "checker_due": due[1]}))
        return gate(ev, rederive=False)
    r = mk("pass")
    ok.append(("nothing holds: stage 2 on the manager's yes; the written CONDITION is the computed L0 (the answer line, F27)", (r["stop"], r["facts"]), (False, [])))
    ok.append(("item 1: a stream over 250.00", mk("credits", c1_credits="250.01")["stop"], True))
    ok.append(("item 1: exactly 250.00 does not exceed", mk("credits-eq", r1_credits="250.00")["stop"], False))
    ok.append(("item 2: checker_due without a checker-add item", mk("no-checker", items=("service",))["stop"], True))
    ok.append(("item 2: service_due without a service item", mk("no-service", items=("checker-add",))["stop"], True))
    ok.append(("item 2: no class due, no checker-add item: nothing holds", mk("not-due", items=("service",), due=(True, False))["stop"], False))
    ok.append(("item 3: a FAIL-CLOSED verdict", mk("fc", verdict_lines=("P2-X1: NOT DETERMINED (FAIL-CLOSED: the scripted repeats ...)",))["stop"], True))
    r = mk("nd-info", verdict_lines=("P2-X1: NOT DETERMINED (not reached: no brief recorded after the apply (step 8))", "P2-E: MISMATCH (1 section(s))"))
    ok.append(("item 3: a NOT DETERMINED that is no fail-closed rule, and a P2-E mismatch, are information only", (r["stop"], bool(r["information"])), (False, True)))
    ok.append(("item 3: an unread credits.txt fails closed", mk("unread", c1_credits=None)["stop"], True))
    ok.append(("item 4: an invalid stream", mk("invalid", valid=False)["stop"], True))
    r = mk("gp1-fc", gp1=dict(GP1, **{"empty-argument calls": "NOT DETERMINED (FAIL-CLOSED: no total in empty-calls.txt)"}))
    ok.append(("F36: item 3: a gate_p1.json measure that fails closed stops", (r["stop"], any("gate_p1 empty-argument calls" in x for x in r["item3"])), (True, True)))
    r = mk("gp1-judged")
    ok.append(("F36: item 3: a judged key's NOT DETERMINED (no prefix) is information, not a stop", (r["stop"], any("G1(d)" in x for x in r["information"])), (False, True)))
    ok.append(("F36: item 3: an unread gate_p1.json fails closed", mk("gp1-none", gp1=None)["stop"], True))
    r = mk("cond", cond=(14, 12))
    ok.append(("a written CONDITION that differs from the computed one is reported (H7)", bool(r["facts"]), True))
    lines = [f"{'ok' if g == w else 'MISMATCH'}  {c}: expected {w}, got {g}" for c, g, w in ok]
    lines.append(f"stage_gate selfcheck: {sum(g == w for _, g, w in ok)} of {len(ok)} ok")
    print("\n".join(lines))
    return 0 if all(g == w for _, g, w in ok) else 1


def main() -> int:
    if sys.argv[1:2] == ["--selfcheck"]:
        return selfcheck(Path(sys.argv[2]))
    ev = Path(sys.argv[1])
    res = gate(ev)
    (ev / "stage-1-gate-inputs.json").write_text(json.dumps(res, indent=1, default=str))
    print(json.dumps(res, indent=1, default=str))
    print("STAGE-1 STOP RULE: " + ("STOP AND REPORT" if res["stop"] else "PASSES (stage 2 on the manager's yes)"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
