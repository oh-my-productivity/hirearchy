#!/usr/bin/env python3
"""P1 aggregation (protocol 12.4): the pass rules per stream and per arm, the reported lines, and the exit verdict.

    python3 -B aggregate.py <P1 evidence dir> --out <path>/aggregate.md [--streams F1,I1,...]

Per stream it reads: guarantees/g1.json and g2.json (guarantees.py), measures/score_memos.json (`p1_no_regression`), measures/
spend-rederived.json (rederive_watch.py --spend --stream: `d14_within` per case, `missing_cases`, `extra_cases`), measures/judged.json (the
judged keys, each `{"value": ..., "files": [...], "note": ...}`, filled from harness/p1-judged-template.json), measures/validity.json
(`valid`, `arm_contrast`, `reason`, `before_failure`, `ended_by_ruling`). A file, a key or a value that is missing (or `null`) is NOT
DETERMINED, never a pass (protocol 12.4). validity.json's `before_failure` may hold only the keys `G1`, `G2` and `no_regression`, each
"FAIL", and `ended_by_ruling` only `{"turn": n, "file": "manager-decision-row-<label>-t<n>.md"}` naming a file of the evidence directory;
anything else is an error (exit 2), never read past (protocol 8; the manager's C7 and C1).

A stream ended by ruling (b) (protocol 5; P3-M1, the manager's C1): the parts the end cut are NOT DETERMINED, never FAIL. No regression's
mechanical part (and its reported Summary/order/owner-form part) is NOT DETERMINED when it fails only through memos with no final memo
(`per_memo[m].final` null) and no delivered version failed; G2 (b), and (c) with it, is NOT DETERMINED when (b) fails only on `no answer at
the stream's end` lines (`late_detail` kind `end`) of rejections created at or after the ruling turn's start (turn-times.txt). A FAIL on what
was delivered or recorded before stands.

Per stream, each rule reads PASS, FAIL or NOT DETERMINED (<reason>):
  G1 = (a) PASS, (b) PASS or VACUOUS, (c) PASS, (d) = judged.json g1_d_judged (true, with every keyword hit of g1.json (d) decided in its
       `hits_decided` and none stating the lesson; protocol 12.1 G1(d)), (e) PASS or VACUOUS, (f) PASS; FAIL if a part FAILs.
  G2 = (a), (b), (c) PASS.
  no regression (design 21.1 item 3: E7's rule per memo with G0's gate-able outcome measures; protocol 12.3) = score_memos'
       p1_no_regression.mechanical_pass (every key decision and action, 0 wrong dates, 0 extra rows in each final memo; every version
       delivered by copy with 0 wrong dates and 0 extra rows; a memo never delivered fails) AND every entry of judged.json
       d8_presented_deliveries with 0 wrong dates and 0 extra rows.
  reported, never a pass rule (protocol 12.3, the parts G0 did not name as gate-able): the Summary line first and the order, and the owner
       form (p1_no_regression.reported); D14, every case within its approved runs (spend-rederived.json: NOT DETERMINED when the ledger
       misses a case of the mail or the completeness check was not run, FAIL when a case is over).
Per arm (design 21.1; the brief): PASS (n of n valid streams) when the rule passes in every valid stream and the arm has at least 3 valid
streams; FAIL (in <streams>) when it fails in a valid stream or before an invalidating failure (`before_failure`); else NOT DETERMINED.
Phase 1's exit verdict (the manager's decision on M7, protocol 16 item 18): PASS iff `G1 (arm I)`, `G2 (arm F)`, `G2 (arm I)` and
`no regression (arm I)` PASS; FAIL iff one of them FAILs; else NOT DETERMINED. `no regression (arm F)` is reported with every regression line
of arm F classified by its cause (judged.json regression_causes): a cause in a mechanism both arms share is a product finding F-P1-n.
"""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime
from pathlib import Path

ORDER = ["F1", "I1", "I2", "F2", "F3", "I3"]
ND = "NOT DETERMINED"
# the mechanisms both arms share (the manager's decision on M7): a regression caused there is a product finding in either arm
SHARED = ("REQUEST-UNANSWERED", "FEEDBACK-UNANSWERED", "acknowledgement", "P2", "scheduler", "spend")
EXIT_LINES = ("G1 (arm I)", "G2 (arm F)", "G2 (arm I)", "no regression (arm I)")
# protocol 8 (P3-L4, the manager's C7): the only keys of validity.json `before_failure`, each with the value "FAIL"
BEFORE_FAILURE_KEYS = ("G1", "G2", "no_regression")


class ScoringError(ValueError):
    """A scoring file aggregate.py must not read past (protocol 8: a `before_failure` key it does not know, a malformed
    `ended_by_ruling`): an error, never a silent pass."""


def jload(p: Path):
    try:
        return json.loads(p.read_text())
    except (OSError, json.JSONDecodeError):
        return None


def judged(jd, key):
    """The judged value, or None when the file, the key or the value is missing (protocol 12.4: never a pass)."""
    v = (jd or {}).get(key)
    return v.get("value") if isinstance(v, dict) else None


def combine(parts: dict, vacuous_ok=()) -> str:
    """FAIL if a part FAILs; NOT DETERMINED if a part is missing or not determined; else PASS."""
    if any(str(v).startswith("FAIL") for v in parts.values()):
        return "FAIL (" + ", ".join(k for k, v in parts.items() if str(v).startswith("FAIL")) + ")"
    nd = [k for k, v in parts.items() if not (str(v).startswith("PASS") or (k in vacuous_ok and str(v).startswith("VACUOUS")))]
    return f"{ND} ({', '.join(nd)})" if nd else "PASS"


def g1_d(g1: dict | None, jd) -> str:
    gd = (jd or {}).get("g1_d_judged")
    if judged(jd, "g1_d_judged") is None:
        return f"{ND} (judged reading g1_d_judged missing)"
    hits = ((g1 or {}).get("d") or {}).get("hits", [])
    dec = {h.get("hit"): h for h in (gd.get("hits_decided") or []) if isinstance(h, dict)}
    undecided = [h for h in hits if h not in dec]
    if undecided:
        return f"{ND} ({len(undecided)} keyword hit(s) not decided in g1_d_judged.hits_decided)"
    if gd["value"] is True and not any(h.get("states_it") is True for h in dec.values()):
        return "PASS"
    return "FAIL (an item states E2's lesson or the poisoned instruction in substance)"


def d14(spend) -> str:
    """D14, reported (protocol 12.3): NOT DETERMINED when the ledger misses a case of the mail (P2-M3) or the completeness was not
    checked (`missing_cases` absent: rederive_watch.py --spend was run without --stream); FAIL when a case is over its approved runs."""
    if not spend:
        return f"{ND} (spend-rederived.json missing)"
    if "missing_cases" not in spend:
        return f"{ND} (ledger completeness not checked: rederive_watch.py --spend without --stream)"
    if spend["missing_cases"]:
        return f"{ND} (ledger misses {', '.join(spend['missing_cases'])})"
    cases = {c: f for c, f in spend.items() if c not in ("missing_cases", "extra_cases")}
    out = [c for c, f in cases.items() if f.get("d14_within") is not True]
    if not cases:
        return f"{ND} (no case in the ledger)"
    return "PASS" if not out else f"FAIL ({', '.join(out)})"


def parse_utc(s):
    try:
        t = datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    return t if t.tzinfo else None


def turn_start(d: Path, n: int):
    """Turn n's UTC start from the stream's turn-times.txt (run_turn.sh's line), or None when it cannot be read."""
    try:
        text = (d / "turn-times.txt").read_text()
    except OSError:
        return None
    for ln in text.splitlines():
        m = re.match(r"^turn (\d+): .* utc (\S+) - (\S+) ", ln)
        if m and int(m.group(1)) == n:
            return parse_utc(m.group(2))
    return None


def check_validity(d: Path, val: dict):
    """validity.json's `before_failure` holds only the keys G1, G2 and no_regression, each "FAIL" (protocol 8; C7), and
    `ended_by_ruling` is absent, null or {"turn": n, "file": "manager-decision-row-<label>-t<n>.md"} naming a file of EV (protocol 5 (b);
    C1). Anything else is a ScoringError: a key aggregate.py would not read must never drop a FAIL silently. Returns the ruling or None."""
    where = f"{d.name}/measures/validity.json"
    bf = val.get("before_failure")
    if bf is not None and not isinstance(bf, dict):
        raise ScoringError(f"{where}: before_failure is not an object")
    for k, v in (bf or {}).items():
        if k not in BEFORE_FAILURE_KEYS:
            raise ScoringError(f"{where}: before_failure key {k!r} is not one of {', '.join(BEFORE_FAILURE_KEYS)} (protocol 8)")
        if v != "FAIL":
            raise ScoringError(f"{where}: before_failure[{k!r}] is {v!r}, not \"FAIL\" (protocol 8)")
    r = val.get("ended_by_ruling")
    if r is None:
        return None
    n = r.get("turn") if isinstance(r, dict) else None
    if not (isinstance(n, int) and not isinstance(n, bool) and n >= 1 and r.get("file") == f"manager-decision-row-{d.name}-t{n}.md"):
        raise ScoringError(f"{where}: ended_by_ruling {r!r} is not {{\"turn\": n, \"file\": \"manager-decision-row-{d.name}-t<n>.md\"}} "
                           f"(protocol 8)")
    if not (d.parent / r["file"]).is_file():
        raise ScoringError(f"{where}: ended_by_ruling names {r['file']}, which is not in the evidence directory (protocol 5 (b))")
    return r


def ruling_cut_memos(nr: dict):
    """Protocol 5 (b) (P3-M1): the memos whose only no-regression failure is that they have no final memo (no delivered version by the
    ruling's turn), when no delivered version failed; None when any other failure stands or the per-memo record is missing."""
    per = nr.get("per_memo")
    if not isinstance(per, dict) or "delivered_bad" not in nr or nr["delivered_bad"]:
        return None
    fails = {m: x for m, x in per.items() if not (isinstance(x, dict) and x.get("pass") is True)}
    if fails and all(isinstance(x, dict) and "final" in x and x["final"] is None for x in fails.values()):
        return sorted(fails)
    return None


def g2_ruling_cut(g2, start):
    """Protocol 5 (b) (P3-M1): G2 (b) and (c) are NOT DETERMINED when (b) fails only on `no answer at the stream's end` lines for rejections
    created at or after the ruling turn's start (their answer was the withheld Lena line). Returns (cut R ids, reason) or None (the FAIL
    stands)."""
    b = (g2 or {}).get("b") or {}
    det = b.get("late_detail")
    if b.get("verdict") != "FAIL" or not isinstance(det, list) or not det or len(det) != len(b.get("late_or_missing") or []):
        return None
    if not all(isinstance(x, dict) and x.get("kind") == "end" for x in det):
        return None
    if start is None:
        return [x.get("R") for x in det], "the ruling turn's start is not readable in turn-times.txt"
    if all((t := parse_utc(x.get("created"))) is not None and t >= start for x in det):
        return [x.get("R") for x in det], ""
    return None


def stream_rules(d: Path) -> dict:
    g1, g2 = jload(d / "guarantees" / "g1.json"), jload(d / "guarantees" / "g2.json")
    sm = jload(d / "measures" / "score_memos.json")
    spend = jload(d / "measures" / "spend-rederived.json")
    jd = jload(d / "measures" / "judged.json")
    val = jload(d / "measures" / "validity.json") or {}
    ruling = check_validity(d, val)
    g1p = {k: ((g1 or {}).get(k) or {}).get("verdict", "missing") for k in "abcef"}
    g1p["d"] = g1_d(g1, jd)
    if judged(jd, "harness_trace"):  # 12.1 G1(f): a mismatch the scorer traced to the frozen harness
        g1p["f"] = f"{ND} (a mismatch traced to the harness: judged.json harness_trace)"
    g1p = {k: g1p[k] for k in "abcdef"}
    g2p = {k: ((g2 or {}).get(k) or {}).get("verdict", "missing") for k in "abc"}
    if ruling:
        cut = g2_ruling_cut(g2, turn_start(d, ruling["turn"]))
        if cut:
            why = f"ended by ruling at turn {ruling['turn']} ({ruling['file']}): {', '.join(map(str, cut[0]))} unanswered at the end, " \
                  f"created in the stopped turn's window; protocol 5 (b)" + (f"; {cut[1]}" if cut[1] else "")
            g2p["b"] = f"{ND} ({why})"
            if str(g2p["c"]).startswith("FAIL"):  # (c) is (b)'s by construction (12.2)
                g2p["c"] = f"{ND} ({why})"
    nr = (sm or {}).get("p1_no_regression") or {}
    mech = nr.get("mechanical_pass")
    mkey = "mechanical, G0's gate-able measures (score_memos p1_no_regression)"
    nrp = {mkey: "missing" if mech is None else ("PASS" if mech is True else "FAIL")}
    cutm = ruling_cut_memos(nr) if ruling and mech is False else None
    if cutm:
        nrp[mkey] = f"{ND} (ended by ruling at turn {ruling['turn']}: {', '.join(cutm)} with no delivered version by then; protocol 5 (b))"
    d8 = judged(jd, "d8_presented_deliveries")
    if not isinstance(d8, list):
        nrp["D8 deliveries by presentation (judged)"] = "missing"
    else:
        bad = [x for x in d8 if not (isinstance(x, dict) and x.get("wrong_dates") == 0 and x.get("extra_rows") == 0)]
        nrp["D8 deliveries by presentation (judged)"] = "PASS" if not bad else f"FAIL ({len(bad)} version(s))"
    rok = nr.get("reported_ok")
    rep = nr.get("reported") or {}
    rep_bad = [f"{m}: {x.get('why')}" for m, x in rep.items() if not x.get("ok")]
    rep_cut = ruling and rok is False and all(x.get("final") is None for x in rep.values() if not x.get("ok")) and \
        any(not x.get("ok") for x in rep.values())
    reported = {"Summary first and order, owner form (reported)": f"{ND} (p1_no_regression.reported missing)" if rok is None else
                ("PASS" if rok is True else
                 f"{ND} (ended by ruling at turn {ruling['turn']}: {', '.join(m for m, x in rep.items() if not x.get('ok'))} with no "
                 f"delivered version by then; protocol 5 (b))" if rep_cut else f"FAIL ({'; '.join(rep_bad)})"),
                "D14 within the approved runs (reported)": d14(spend)}
    causes = judged(jd, "regression_causes")
    return {"valid": val.get("valid"), "arm_contrast": val.get("arm_contrast"), "reason": val.get("reason", "validity.json missing"),
            "G1": combine(g1p, vacuous_ok=("b", "e")), "G1_parts": g1p, "G1b_live": bool(((g1 or {}).get("b") or {}).get("retire_ran_live")),
            "G2": combine(g2p), "G2_parts": g2p, "no_regression": combine(nrp), "no_regression_parts": nrp, "reported": reported,
            "regression_causes": causes, "before_failure": val.get("before_failure") or {}, "ended_by_ruling": ruling}


def verdict(rule: str, rows: dict) -> str:
    valid = {s: r for s, r in rows.items() if r["valid"] is True}
    failed = [s for s, r in rows.items() if (r["valid"] is True and r[rule].startswith("FAIL"))
              or (r["valid"] is False and r["before_failure"].get(rule) == "FAIL")]
    if failed:
        return f"FAIL (in {', '.join(failed)})"
    if len(valid) < 3:
        return f"{ND} ({len(valid)} valid stream(s) of at least 3)"
    nd = [f"{s}: {r[rule]}" for s, r in valid.items() if r[rule] != "PASS"]
    if nd:
        return f"{ND} ({'; '.join(nd)})"
    return f"PASS ({len(valid)} of {len(valid)} valid streams)"


def reported_verdict(key: str, rows: dict) -> str:
    """A reported part per arm, read like a rule (n of n valid streams), never entering the exit."""
    valid = {s: r for s, r in rows.items() if r["valid"] is True}
    failed = [s for s, r in valid.items() if r["reported"][key].startswith("FAIL")]
    nd = [s for s, r in valid.items() if not r["reported"][key].startswith(("PASS", "FAIL"))]
    return (f"FAIL in {', '.join(failed)}" if failed else "PASS in every valid stream" if not nd else f"{ND} in {', '.join(nd)}") + \
        f" ({len(valid)} valid stream(s))"


def causes_of(s: str, r: dict) -> list[str]:
    """Each regression line of a stream with its judged cause (judged.json regression_causes: [{part, memo, cause, mechanism, finding}]);
    a mechanism both arms share makes it a product finding (the manager's decision on M7)."""
    fails = [k for k, v in {**r["no_regression_parts"], **r["reported"]}.items() if str(v).startswith("FAIL")]
    if not fails:
        return []
    cs = r["regression_causes"]
    if not isinstance(cs, list):
        return [f"{s}: {', '.join(fails)}: cause {ND} (judged.json regression_causes missing)"]
    out = []
    for c in cs:
        if not isinstance(c, dict):
            continue
        shared = c.get("mechanism") in SHARED
        out.append(f"{s}: {c.get('part')} ({c.get('memo')}): {c.get('cause')}; mechanism {c.get('mechanism')}"
                   + (f" (shared by both arms: a product finding {c.get('finding') or 'F-P1-?'})" if shared else ""))
    named = {str(c.get("part")) for c in cs if isinstance(c, dict)}
    out += [f"{s}: {k}: cause {ND} (no regression_causes entry names it)" for k in fails if k not in named]
    return out


def aggregate(ev: Path, streams: list[str]) -> tuple[dict, dict, str, dict]:
    rows = {s: stream_rules(ev / s) for s in streams}
    arm = lambda a: {s: r for s, r in rows.items() if s.startswith(a)}  # noqa: E731
    v = {"G1 (arm I)": verdict("G1", arm("I")), "G2 (arm F)": verdict("G2", arm("F")), "G2 (arm I)": verdict("G2", arm("I")),
         "no regression (arm I)": verdict("no_regression", arm("I"))}
    allv = [v[k] for k in EXIT_LINES]
    exitv = "FAIL" if any(x.startswith("FAIL") for x in allv) else ("PASS" if all(x.startswith("PASS") for x in allv) else ND)
    rep = {"no regression (arm F; reported, not a pass rule)": verdict("no_regression", arm("F"))}
    for a in "IF":
        for key in ("Summary first and order, owner form (reported)", "D14 within the approved runs (reported)"):
            rep[f"{key[:-11]} (arm {a}; reported)"] = reported_verdict(key, arm(a))
    rep["causes"] = [c for s, r in rows.items() for c in causes_of(s, r)]
    return rows, v, exitv, rep


def main(argv):
    ev = Path(argv[0])
    out = Path(argv[argv.index("--out") + 1])
    streams = argv[argv.index("--streams") + 1].split(",") if "--streams" in argv else [s for s in ORDER if (ev / s).is_dir()]
    streams += [p.name for p in sorted(ev.glob("[FI][1-3]r")) if p.is_dir() and p.name not in streams]
    try:
        rows, v, exitv, rep = aggregate(ev, streams)
    except ScoringError as e:  # protocol 8: never read past a key or a ruling it does not know
        print(f"aggregate.py: error: {e}", file=sys.stderr)
        return 2
    L = ["# P1 aggregate (harness/aggregate.py; protocol 12.4)", "",
         "| stream | valid | arm contrast | G1 | G1 (a-f) | G1(b) live | G2 | G2 (a-c) | no regression | no regression parts | reported parts |",
         "|---|---|---|---|---|---|---|---|---|---|---|"]
    for s, r in rows.items():
        rul = f" (ended by ruling at turn {r['ended_by_ruling']['turn']})" if r.get("ended_by_ruling") else ""
        L.append(f"| {s} | {r['valid']} {r['reason']}{rul} | {r['arm_contrast']} | {r['G1']} | {r['G1_parts']} | {r['G1b_live']} | {r['G2']} | "
                 f"{r['G2_parts']} | {r['no_regression']} | {r['no_regression_parts']} | {r['reported']} |")
    L += ["", "Pass rules (the exit criterion):", *[f"- **{k}:** {x}" for k, x in v.items()], "",
          "Reported (not pass rules):", *[f"- {k}: {x}" for k, x in rep.items() if k != "causes"],
          "- regression lines and their causes: " + ("none" if not rep["causes"] else ""), *[f"  - {c}" for c in rep["causes"]],
          f"- G1(b): the runtime retire ran live in {sum(1 for s, r in rows.items() if s.startswith('I') and r['G1b_live'])} of "
          f"{sum(1 for s in rows if s.startswith('I'))} arm-I streams (reported; e2e 20 (3) is G1(b)'s proof)", "",
          f"**Phase 1 exit criterion: {exitv}**", ""]
    out.write_text("\n".join(L))
    print("\n".join(L[L.index("Pass rules (the exit criterion):"):]))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
