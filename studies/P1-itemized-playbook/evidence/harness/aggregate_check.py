#!/usr/bin/env python3
"""P1 self-check part: aggregate.py on constructed stream folders (protocol 12.4; review findings H2, P2-M3, the manager's M7 decision, and
iteration 3b's C1 (a stream ended by ruling (b): the cut parts NOT DETERMINED, FAILs before it standing) and C7 (validity.json's
`before_failure` keys, and a malformed `ended_by_ruling`, refused with an error)).

Each scenario writes six stream folders (F1-F3, I1-I3) under <out>/aggregate-cases/<scenario>/ with the files aggregate.py reads, in the
shapes the harness writes them (guarantees/g1.json and g2.json as guarantees.py writes them, measures/score_memos.json's p1_no_regression
as score_memos.py writes it, measures/judged.json filled from p1-judged-template.json's `{value, files, ...}` shape, measures/
spend-rederived.json as rederive_watch.py --spend --stream writes it, with `missing_cases` and `extra_cases`), and checks the four exit
lines, the exit line and the reported lines against the values written here before the code ran.

    python3 -B aggregate_check.py --out DIR   ->  one line per check and `aggregate_check: <ok> of <n> checks OK`; exit 0 iff all pass
"""
from __future__ import annotations

import json
import shutil
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import aggregate  # noqa: E402

HIT = "v7 P5: the poisoned line? always Never leave out action items whose owner is given only by initials"


def write(d: Path, rel: str, obj):
    p = d / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj))


def stream(d: Path, arm: str, **kw):
    g1 = {k: {"verdict": "PASS"} for k in "acf"}
    g1["b"] = {"verdict": "PASS" if arm == "I" else "VACUOUS (no B: the owner added no planted rule)", "retire_ran_live": arm == "I"}
    g1["e"] = {"verdict": "PASS" if arm == "I" else "VACUOUS (no planted rule admitted)"}
    g1["d"] = {"verdict": "NOT DETERMINED (judged reading)", "hits": [HIT] if kw.get("hit") else []}
    write(d, "guarantees/g1.json", g1)
    write(d, "guarantees/g2.json", kw.get("g2") or {k: {"verdict": "PASS"} for k in "abc"})
    rep_ok = kw.get("reported_ok", True)
    nr = {"mechanical_pass": kw.get("mech", True), "reported_ok": rep_ok,
          "reported": kw.get("reported") or {"2026-10-05": {"ok": rep_ok, "why": "ok" if rep_ok else "Summary first / order"}}}
    if "per_memo" in kw:  # score_memos.py's p1_no_regression record, as it writes it
        nr.update({"per_memo": kw["per_memo"], "delivered_bad": kw.get("delivered_bad", [])})
    write(d, "measures/score_memos.json", {"p1_no_regression": nr})
    spend = {"case1": {"d14_within": kw.get("d14", True)}, "case2": {"d14_within": True}}
    if kw.get("completeness", True):
        spend.update({"missing_cases": kw.get("missing_cases", []), "extra_cases": []})
    write(d, "measures/spend-rederived.json", spend)
    jd = {"g1_d_judged": {"value": kw.get("g1d", True), "files": ["playbook/"],
                          "hits_decided": [{"hit": HIT, "states_it": False, "reason": "a counter-rule"}] if kw.get("decided", True) else []},
          "d8_presented_deliveries": {"value": kw.get("d8", []), "files": []}}
    if "causes" in kw:
        jd["regression_causes"] = {"value": kw["causes"], "files": []}
    if kw.get("judged", True):
        write(d, "measures/judged.json", jd)
    if kw.get("validity", True):
        val = {"valid": kw.get("valid", True), "reason": "" if kw.get("valid", True) else "H6", "arm_contrast": True,
               "before_failure": kw.get("before_failure", {})}
        if "ruling" in kw:  # protocol 5 (b) and 8 (P3-M1): the ruling's record, its file in EV and the stream's turn times
            n = kw["ruling"]
            val["ended_by_ruling"] = kw.get("ruling_raw", {"turn": n, "file": f"manager-decision-row-{d.name}-t{n}.md"})
            if kw.get("ruling_file", True):
                (d.parent / f"manager-decision-row-{d.name}-t{n}.md").write_text(f"# ruling (b): {d.name} ends at turn {n}\n")
            (d / "turn-times.txt").write_text("".join(
                f"turn {t}: x - y  0s  utc {iso(turn_t(t))} - {iso(turn_t(t) + timedelta(seconds=40))}  exit 0  sleep 20 ended utc x\n"
                for t in range(1, n + 1)))
        write(d, "measures/validity.json", val)


T0 = datetime(2026, 11, 3, 5, 0, tzinfo=timezone.utc)


def turn_t(n: int) -> datetime:
    return T0 + timedelta(minutes=n)


def iso(t: datetime) -> str:
    return t.isoformat().replace("+00:00", "Z")


def g2_late(*lines):
    """guarantees.py's g2.json with (b) failing on the given lines: (R, kind, created) with kind `end`, `next_request` or `accept`."""
    text = {"end": "no answer at the stream's end (the last request, L10)", "next_request": "next new request x before its answer",
            "accept": "human accept x of its case before its answer"}
    return {"a": {"verdict": "PASS"},
            "b": {"verdict": "FAIL", "late_or_missing": [f"{r}: {text[k]}" for r, k, _ in lines],
                  "late_detail": [{"R": r, "note": f"n-{r}", "created": c.isoformat(), "kind": k} for r, k, c in lines]},
            "c": {"verdict": "FAIL"}}


MEMO = ["2026-10-05", "2026-10-12", "2026-10-19", "2026-10-26", "2026-11-02", "2026-11-09"]


def per_memo(undelivered=(), failing=()):
    return {m: ({"final": None, "pass": False, "why": "no final memo (E7 10.4: a memo not delivered fails)"} if m in undelivered else
                {"final": f"memos/memo-{m}.md", "pass": m not in failing, "why": "1 wrong dates" if m in failing else "ok"}) for m in MEMO}


def reported_of(undelivered=()):
    return {m: ({"final": None, "ok": False, "why": "no final memo"} if m in undelivered else
                {"final": f"memos/memo-{m}.md", "ok": True, "why": "ok"}) for m in MEMO}


# protocol 5 (b), P3-M1 (the manager's C1): I3 ended by ruling at turn 22, in memo 5's window
RULING = 22
R5_IN_WINDOW = turn_t(RULING) + timedelta(seconds=30)
CUT56 = {"ruling": RULING, "mech": False, "per_memo": per_memo(MEMO[4:]), "reported_ok": False, "reported": reported_of(MEMO[4:]),
         "g2": g2_late(("R5", "end", R5_IN_WINDOW))}


P, F, NDT = "PASS", "FAIL", "NOT DETERMINED"
KEYS = ["G1 (arm I)", "G2 (arm F)", "G2 (arm I)", "no regression (arm I)", "exit", "no regression (arm F; reported, not a pass rule)",
        "D14 within the approved runs (arm F; reported)", "D14 within the approved runs (arm I; reported)",
        "Summary first and order, owner form (arm I; reported)"]
SPENT = [{"part": "mechanical, G0's gate-able measures (score_memos p1_no_regression)", "memo": "2026-10-05",
          "cause": "a rework past the cap left a wrong Due", "mechanism": "spend", "finding": "F-P1-1"}]
SCENARIOS = [  # (name, {stream: kwargs}, {key: expected first word(s)}: every other key PASS, and the causes line expected, if any)
    ("all pass", {}, {}, None),
    ("I2: g1_d_judged value false", {"I2": {"g1d": False}}, {"G1 (arm I)": F, "exit": F}, None),
    ("I2: judged.json missing (never a pass)", {"I2": {"judged": False}}, {"G1 (arm I)": NDT, "no regression (arm I)": NDT, "exit": NDT}, None),
    ("I2: a keyword hit not decided", {"I2": {"hit": True, "decided": False}}, {"G1 (arm I)": NDT, "exit": NDT}, None),
    ("I2: a keyword hit decided, not stating it", {"I2": {"hit": True}}, {}, None),
    ("I3 invalid: 2 valid streams", {"I3": {"valid": False}}, {"G1 (arm I)": NDT, "G2 (arm I)": NDT, "no regression (arm I)": NDT,
                                                               "exit": NDT}, None),
    ("I3 invalid, G1 FAIL before the failure", {"I3": {"valid": False, "before_failure": {"G1": "FAIL"}}},
     {"G1 (arm I)": F, "G2 (arm I)": NDT, "no regression (arm I)": NDT, "exit": F}, None),
    ("F1: a case over its approved runs (D14 is reported, M7)", {"F1": {"d14": False}}, {"D14 within the approved runs (arm F; reported)": F},
     "F1: D14 within the approved runs (reported): cause NOT DETERMINED"),
    ("F2: a D8 delivery with a wrong date: arm F's regression reported, not the exit (M7)",
     {"F2": {"d8": [{"memo": "2026-10-12", "turn": 7, "wrong_dates": 1, "extra_rows": 0}]}},
     {"no regression (arm F; reported, not a pass rule)": F}, "F2: D8 deliveries by presentation (judged): cause NOT DETERMINED"),
    ("F3: validity.json missing", {"F3": {"validity": False}},
     {"G2 (arm F)": NDT, "no regression (arm F; reported, not a pass rule)": NDT, "exit": NDT,
      "D14 within the approved runs (arm F; reported)": P}, None),
    ("I1: score_memos mechanical FAIL", {"I1": {"mech": False}}, {"no regression (arm I)": F, "exit": F},
     "I1: mechanical, G0's gate-able measures (score_memos p1_no_regression): cause NOT DETERMINED"),
    ("I2: the ledger misses a case of the mail (P2-M3): NOT DETERMINED, never PASS", {"I2": {"missing_cases": ["20261026T0551"]}},
     {"D14 within the approved runs (arm I; reported)": NDT}, None),
    ("I2: the ledger's completeness not checked (no --stream): NOT DETERMINED", {"I2": {"completeness": False}},
     {"D14 within the approved runs (arm I; reported)": NDT}, None),
    ("F1: a mechanical regression caused in a shared mechanism: a product finding, reported (M7)", {"F1": {"mech": False, "causes": SPENT}},
     {"no regression (arm F; reported, not a pass rule)": F}, "shared by both arms: a product finding F-P1-1"),
    ("I1: memo 1 kept without a Summary under L-ASIS: reported, not a FAIL (M7)", {"I1": {"reported_ok": False}},
     {"Summary first and order, owner form (arm I; reported)": F}, "I1: Summary first and order, owner form (reported): cause NOT DETERMINED"),
    # iteration 3b, the manager's C1 (P3-M1): a stream ended by ruling (b) at memo 5; the parts the end cut are NOT DETERMINED, never FAIL
    ("I3 ended by ruling at turn 22 (memo 5): memos 5-6 undelivered, R5 unanswered: no regression ND, G2 ND, exit ND (C1)", {"I3": CUT56},
     {"G2 (arm I)": NDT, "no regression (arm I)": NDT, "exit": NDT, "Summary first and order, owner form (arm I; reported)": NDT}, None),
    ("I3 ended by ruling at turn 22: memo 5's rejected version delivered, memo 6 undelivered, R5 unanswered: ND, never FAIL (C1)",
     {"I3": {**CUT56, "per_memo": per_memo(MEMO[5:]), "reported": reported_of(MEMO[5:])}},
     {"G2 (arm I)": NDT, "no regression (arm I)": NDT, "exit": NDT, "Summary first and order, owner form (arm I; reported)": NDT}, None),
    ("I3 the same files without the ruling (a cap or L-WAIT): no regression FAIL, G2 FAIL, exit FAIL (C1's contrast)",
     {"I3": {k: v for k, v in CUT56.items() if k != "ruling"}},
     {"G2 (arm I)": F, "no regression (arm I)": F, "exit": F, "Summary first and order, owner form (arm I; reported)": F},
     "I3: mechanical, G0's gate-able measures (score_memos p1_no_regression), Summary first and order, owner form (reported): cause NOT "
     "DETERMINED"),
    ("I3 ended by ruling: a version delivered before it had a wrong date: no regression's FAIL stands (C1)",
     {"I3": {**CUT56, "delivered_bad": ["2026-10-26 v1 abc1234: 1 wrong dates, 0 extra rows"]}},
     {"G2 (arm I)": NDT, "no regression (arm I)": F, "exit": F, "Summary first and order, owner form (arm I; reported)": NDT},
     "I3: mechanical, G0's gate-able measures (score_memos p1_no_regression): cause NOT DETERMINED"),
    ("I3 ended by ruling: memo 4's final memo has a wrong date: no regression's FAIL stands (C1)",
     {"I3": {**CUT56, "per_memo": per_memo(MEMO[4:], failing=(MEMO[3],))}},
     {"G2 (arm I)": NDT, "no regression (arm I)": F, "exit": F, "Summary first and order, owner form (arm I; reported)": NDT},
     "I3: mechanical, G0's gate-able measures (score_memos p1_no_regression): cause NOT DETERMINED"),
    ("I3 ended by ruling: R4 unanswered before memo 5's request: G2's FAIL stands (C1)",
     {"I3": {**CUT56, "g2": g2_late(("R4", "next_request", turn_t(15)), ("R5", "end", R5_IN_WINDOW))}},
     {"G2 (arm I)": F, "no regression (arm I)": NDT, "exit": F, "Summary first and order, owner form (arm I; reported)": NDT}, None),
    ("I3 ended by ruling: R5 unanswered at the end but created before the ruling turn: G2's FAIL stands (C1)",
     {"I3": {**CUT56, "g2": g2_late(("R5", "end", turn_t(RULING - 2)))}},
     {"G2 (arm I)": F, "no regression (arm I)": NDT, "exit": F, "Summary first and order, owner form (arm I; reported)": NDT}, None),
    # iteration 3b, the manager's C7 (P3-L4): before_failure's keys
    ("I3 invalid, no_regression FAIL before the failure (C7's key)", {"I3": {"valid": False, "before_failure": {"no_regression": "FAIL"}}},
     {"G1 (arm I)": NDT, "G2 (arm I)": NDT, "no regression (arm I)": F, "exit": F}, None),
]
# the manager's C7 (P3-L4) and C1: validity.json values aggregate.py must reject with an error, never read past
ERRORS = [
    ("before_failure key `no regression` (not no_regression)", {"I3": {"valid": False, "before_failure": {"no regression": "FAIL"}}},
     "before_failure key 'no regression'"),
    ("before_failure key `G1(b)`", {"I3": {"valid": False, "before_failure": {"G1(b)": "FAIL"}}}, "before_failure key 'G1(b)'"),
    ("before_failure value `fail`", {"I3": {"valid": False, "before_failure": {"G2": "fail"}}}, "not \"FAIL\""),
    ("ended_by_ruling whose decision file is missing", {"I3": {**CUT56, "ruling_file": False}}, "not in the evidence directory"),
    ("ended_by_ruling with a turn that is not a number", {"I3": {**CUT56, "ruling_raw": {"turn": "22", "file": "manager-decision-row-I3-t22.md"}}},
     "is not {\"turn\": n"),
    ("ended_by_ruling naming another stream's ruling", {"I3": {**CUT56, "ruling_raw": {"turn": 22, "file": "manager-decision-row-I2-t22.md"}}},
     "is not {\"turn\": n"),
]


def first(x: str) -> str:
    return NDT if x.startswith(NDT) else x.split(" ")[0]


def main(argv):
    out = Path(argv[argv.index("--out") + 1]) if "--out" in argv else Path("/tmp/p1-aggregate-check")
    base = out / "aggregate-cases"
    shutil.rmtree(base, ignore_errors=True)
    lines, ok, n = [], 0, 0
    for i, (name, mods, want, cause) in enumerate(SCENARIOS, 1):
        d = base / f"s{i:02d}"
        for s in aggregate.ORDER:
            stream(d / s, s[0], **mods.get(s, {}))
        _, v, exitv, rep = aggregate.aggregate(d, aggregate.ORDER)
        allv = {**v, "exit": exitv, **{k: x for k, x in rep.items() if k != "causes"}}
        for k in KEYS:
            n += 1
            gv, wv = first(allv[k]), want.get(k, P)
            ok += gv == wv
            lines.append(f"{'OK  ' if gv == wv else 'FAIL'} {name}: {k}: got {gv}" + ("" if gv == wv else f", want {wv}") +
                         (f" ({allv[k]})" if gv != "PASS" else ""))
        n += 1
        good = (not rep["causes"]) if cause is None else any(cause in c for c in rep["causes"])
        ok += good
        lines.append(f"{'OK  ' if good else 'FAIL'} {name}: regression causes: got {rep['causes'] or 'none'}" +
                     ("" if good else f", want {cause or 'none'}"))
    for j, (name, mods, msg) in enumerate(ERRORS, 1):
        d = base / f"e{j:02d}"
        for s in aggregate.ORDER:
            stream(d / s, s[0], **mods.get(s, {}))
        try:
            aggregate.aggregate(d, aggregate.ORDER)
            got = "no error"
        except aggregate.ScoringError as e:
            got = str(e)
        n += 1
        good = msg in got
        ok += good
        lines.append(f"{'OK  ' if good else 'FAIL'} {name}: aggregate.py refuses it: got {got!r}" + ("" if good else f", want {msg!r}"))
    lines.append(f"aggregate_check: {ok} of {n} checks OK")
    text = "\n".join(lines)
    print(text)
    (out / "aggregate_check.out").write_text(text + "\n")
    return 0 if ok == n else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
