#!/usr/bin/env python3
"""P2 `lena-lines.txt` parser and the facilitator's mechanical counts (protocol 4.8, 4.2, 4.6, 6.6). Standard library only.

Line form: `turn <n> | rules <ids joined by " + "> | table rows <K-ids, or none> | facts: <...>`. The rules are a list (one entry per
rule; two rejections of one rule in a line are two entries). Used by the stream step to check each line as written (read-only):
    python3 -B -c "import sys; sys.path.insert(0,'<H>'); import lena_lines as L; print(L.parse_line(open('<file>').read().splitlines()[-1]))"
and by extract_p2.py. Also: python3 -B lena_lines.py <lena-lines.txt> (prints the counts) | --selfcheck.
"""
from __future__ import annotations

import re
import sys

LINE = re.compile(r"^turn (\d+) \| rules (.*?) \| table rows (.*?) \| facts: ?(.*)$")
RULE = re.compile(r"^(H1|H2|A-W|A-W-UNASKED|L-REVIEW|H4|H5|H6|L-INF|L-VAGUE|L-SONNET|L-FIRST|L-FUND|L-DECLINE|L-INJ|L-BASE|L-WAIT|L-KEEP|"
                  r"WEEK-LIST|WEEK-NOTES|RETRO-NOT-NOW|RETRO-YES|RETRO-ASK|ITEM-SERVICE|ITEM-DELIVERABLE|PLAN-APPROVE|ITEM-CHECKER|"
                  r"ITEM-CLARIFY-W|ITEM-NOT-NOW|ITEM-CAUSE|L-NOTHANKS|EXT-NO|ANSWER|CONDITION|"
                  r"(?:ACCEPT|VR-REJECT|TRAP-1|TRAP-N|L-ASIS|ACT-REQ|NEXT)@\d{4}-\d{2}-\d{2}|A-M@2026-11-09|LIST-KEEP@\S+)$")
TRAP_MEMOS = ("2026-10-12", "2026-10-19", "2026-10-26", "2026-11-02")
JUDGING = ("ACCEPT", "VR-REJECT", "TRAP-1", "TRAP-N", "L-ASIS", "A-M")


def parse_line(s: str) -> dict | None:
    m = LINE.match(s.strip())
    if not m:
        return None
    rules = [r.strip() for r in m.group(2).split(" + ") if r.strip()]
    rows = [r.strip() for r in re.split(r",\s*", m.group(3)) if r.strip() and r.strip() != "none"]
    return {"turn": int(m.group(1)), "rules": rules, "rows": rows, "facts": m.group(4), "unknown_rules": [r for r in rules if not RULE.match(r)]}


def parse(path: str) -> dict:
    raw = [ln for ln in open(path, errors="replace").read().splitlines() if ln.startswith("turn ")]
    lines = [parse_line(ln) for ln in raw]
    return {"raw": len(raw), "lines": [x for x in lines if x], "unread": [raw[i] for i, x in enumerate(lines) if x is None]}


def memo_of(rule: str) -> str | None:
    m = re.search(r"@(\d{4}-\d{2}-\d{2})$", rule)
    return m.group(1) if m else None


def trap_memos(lines: list[dict]) -> dict[str, list[int]]:
    out: dict[str, list[int]] = {}
    for x in lines:
        for r in x["rules"]:
            if r.startswith(("TRAP-1@", "TRAP-N@")):
                out.setdefault(memo_of(r), []).append(x["turn"])
    return out


def judged_memos(lines: list[dict]) -> set[str]:
    """Memos with a Lena verdict on a delivered version (a JUDGING rule naming the memo)."""
    return {memo_of(r) for x in lines for r in x["rules"] if r.split("@")[0] in JUDGING and memo_of(r)}


def passed_trap(lines: list[dict]) -> list[str]:
    """Memos 2-5 judged by Lena (a delivered version had her verdict) with no TRAP rule in any line (protocol 4.2: "the team passed the
    trap"; F2 of the review: a memo the stream never reached is not passed)."""
    t = trap_memos(lines)
    j = judged_memos(lines)
    return [m for m in TRAP_MEMOS if m not in t and m in j]


def trap_unreached(lines: list[dict]) -> list[str]:
    """Memos 2-5 with no verdict of Lena at all (the stream ended before them, or never delivered them)."""
    t = trap_memos(lines)
    j = judged_memos(lines)
    return [m for m in TRAP_MEMOS if m not in t and m not in j]


def x2_not_reached(lines: list[dict]) -> bool:
    return len(passed_trap(lines)) >= 2


ANSWER_ROWS = ("K29", "K30", "K30c", "K47a")
ANSWERS = re.compile(r"\banswers ((?:TRAP-1|TRAP-N)@\d{4}-\d{2}-\d{2})")


def third_trap(lines: list[dict]) -> tuple[int | None, str | None]:
    """The first line with a TRAP rule for a third distinct memo, and that rule."""
    seen: set = set()
    for x in lines:
        for r in x["rules"]:
            if r.startswith(("TRAP-1@", "TRAP-N@")) and memo_of(r) not in seen:
                seen.add(memo_of(r))
                if len(seen) == 3:
                    return x["turn"], r
    return None, None


def condition_turn(lines: list[dict]) -> int | None:
    """Retro 1's waiting condition (protocol 4.6, 6.6; F27 of review 2). L0 is the earlier of:
    (a) the line that answers the third TRAP rejection's one question: the first line after the third TRAP rule for a third distinct memo
        whose rows hold K29, K30, K30c or K47a and whose facts say `answers <that TRAP rule>` (7.2 counts a rejection only once it is
        answered); when a line that judges a delivered version comes after the TRAP line before any such answer (root asked no question for
        that rejection before its next delivery), that judging line;
    (b) the first line that judges a delivered version of memo 5, unless that line is the third TRAP line itself (then (a) decides)."""
    t3, rule3 = third_trap(lines)
    a = None
    if t3 is not None:
        for x in lines:
            if x["turn"] <= t3:
                continue
            if any(r.split(" ")[0] in ANSWER_ROWS for r in x["rows"]) and rule3 in ANSWERS.findall(x["facts"]):
                a = x["turn"]
                break
            if any(r.split("@")[0] in JUDGING for r in x["rules"]):
                a = x["turn"]
                break
    b = None
    for x in lines:
        if any(r.split("@")[0] in JUDGING and memo_of(r) == "2026-11-02" for r in x["rules"]):
            b = x["turn"] if x["turn"] != t3 else None
            break
    c = [v for v in (a, b) if v is not None]
    return min(c) if c else None


def retro_places(lines: list[dict]) -> dict:
    """Where the retro lines may stand (protocol 4.6, rows K40, K41, K41a; F28 of review 2; both arms, C3 of the closing decision). Retro 1:
    the RETRO-YES line in L1 or L2, or the RETRO-ASK line at L3 (in arm C, the arm-C turn). Retro 2's place: the week list's LIST-KEEP line when it carries RETRO-YES (the reply delivering the
    week list offered one), else the next line. RETRO-NOT-NOW stands only at or before L0 (an offer made before the condition held), or
    after retro 1 and before retro 2's place; RETRO-YES and RETRO-ASK only at retro 1 and at retro 2's place. Others are listed as
    `misplaced` (an H7 check for the scoring step)."""
    l0 = condition_turn(lines)
    after = [x for x in lines if l0 is not None and x["turn"] > l0][:3]
    # C3 (F40 of review 3): one rule for both arms: retro 1's RETRO-YES stands in L1 or L2, its RETRO-ASK in L3 only (4.6)
    r1 = next((x["turn"] for i, x in enumerate(after) if ("RETRO-YES" in x["rules"] and i < 2) or ("RETRO-ASK" in x["rules"] and i == 2)), None)
    wl = next((x["turn"] for x in lines if "WEEK-LIST" in x["rules"]), None)
    wk = next((x for x in lines if wl is not None and x["turn"] > wl and any(r.startswith("LIST-KEEP@") for r in x["rules"])), None)
    r2 = None
    if wk is not None:
        r2 = wk["turn"] if "RETRO-YES" in wk["rules"] else next((x["turn"] for x in lines if x["turn"] > wk["turn"]), None)
    bad = []
    for x in lines:
        t = x["turn"]
        if "RETRO-NOT-NOW" in x["rules"] and not ((l0 is None or t <= l0) or (r1 is not None and t > r1 and (r2 is None or t < r2))):
            bad.append(f"turn {t}: RETRO-NOT-NOW")
        bad += [f"turn {t}: {k}" for k in ("RETRO-YES", "RETRO-ASK") if k in x["rules"] and t not in (r1, r2)]
    return {"L0": l0, "retro1": r1, "retro2": r2, "misplaced": bad}


REJECTING = ("H6", "VR-REJECT", "TRAP-1", "TRAP-N", "A-M")


def retro1_expected(lines: list[dict], offers: set[int]) -> dict:
    """Retro 1's lines, the same rule in both arms (protocol 4.6, K40, K41, K41a; C3 of the closing decision, on F40 of review 3).
    `offers`: the turns of the Lena lines whose preceding assistant reply offered a retro or a review (D-RETRO-OFFER, `retro-offers.txt`;
    in arm C the assistant's own offer). An offer answered at or before L0 gets RETRO-NOT-NOW (K40); an offer before L1 or L2 gets
    RETRO-YES (K41) in the first such line, which is then retro 1 (in arm C, the arm-C turn) and L3 carries no RETRO-ASK; with no such
    offer, L3 carries RETRO-ASK (the fallback, also when the reply before L3 offers one). Later offers before retro 2's place are K41a's."""
    l0 = condition_turn(lines)
    after = [x["turn"] for x in lines if l0 is not None and x["turn"] > l0][:3]
    yes = next((t for t in after[:2] if t in offers), None)
    ask = after[2] if yes is None and len(after) == 3 else None
    return {"L0": l0, "RETRO-NOT-NOW": sorted(t for t in offers if l0 is None or t <= l0), "RETRO-YES": yes, "RETRO-ASK": ask,
            "turn": yes if yes is not None else ask}


def verdict_after(lines: list[dict], memo: str, turn: int | None) -> str | None:
    """Lena's verdict on a version of `memo` delivered in turn `turn` (a reply of that turn, or a commit in its window): the first later
    line that judges `memo`, read as `rejected` (H6 for memo 1, VR-REJECT, TRAP-1, TRAP-N, A-M), `accepted` (ACCEPT), `as-is` (L-ASIS),
    or None when no later line judges it (protocol 12.3, F26 of review 2)."""
    for x in sorted(lines, key=lambda x: x["turn"]):
        if turn is not None and x["turn"] <= turn:
            continue
        for r in x["rules"]:
            k = r.split("@")[0]
            m = "2026-10-05" if r == "H6" else memo_of(r)
            if m == memo and (k in JUDGING or r == "H6"):
                return "rejected" if k in REJECTING else ("as-is" if k == "L-ASIS" else "accepted")
    return None


def written_condition(lines: list[dict]) -> int | None:
    return next((x["turn"] for x in lines if "CONDITION" in x["rules"]), None)


def ext_no_not_first(lines: list[dict]) -> list[int]:
    """Protocol amendment 1 item 3 (the composition rule): in a line that answers a reply announcing or proposing an unnominated structural
    change AND asking questions, EXT-NO (K48) comes first among the answers, then the answers in the order asked. The rows are recorded in
    the line's order (4.8), so a line whose rows hold K48 after another row breaks the rule. Returns those turns (an H7 check for step 12)."""
    return [x["turn"] for x in lines if "K48" in [r.split(" ")[0] for r in x["rows"]] and x["rows"][0].split(" ")[0] != "K48"]


def counts(path: str) -> dict:
    p = parse(path)
    ls = p["lines"]
    return {"lines": len(ls), "raw": p["raw"], "unread": p["unread"], "unknown_rules": [r for x in ls for r in x["unknown_rules"]],
            "trap_memos": trap_memos(ls), "passed_trap": passed_trap(ls), "x2_not_reached": x2_not_reached(ls),
            "condition_turn": condition_turn(ls), "condition_written": written_condition(ls),
            "ext_no": sum(x["rules"].count("EXT-NO") for x in ls),
            "item_lines": {k: [x["turn"] for x in ls if k in x["rules"]] for k in ("ITEM-SERVICE", "ITEM-CHECKER", "ITEM-CLARIFY-W", "PLAN-APPROVE", "RETRO-YES", "RETRO-ASK", "ITEM-NOT-NOW", "ITEM-CAUSE", "EXT-NO")},
            "act_req": [(x["turn"], memo_of(r)) for x in ls for r in x["rules"] if r.startswith("ACT-REQ@")],
            "week_list": [x["turn"] for x in ls if "WEEK-LIST" in x["rules"]],
            "list_bounds": [x["turn"] for x in ls if any(r.startswith(("LIST-KEEP@", "ACT-REQ@", "NEXT@")) or r == "WEEK-LIST" for r in x["rules"])],
            "trap_unreached": trap_unreached(ls), "retro_places": retro_places(ls), "ext_no_not_first": ext_no_not_first(ls),
            "rows_by_turn": {x["turn"]: x["rows"] for x in ls}}


def selfcheck() -> int:
    import tempfile
    rows = ["turn 1 | rules H1 | table rows none | facts: opening",
            "turn 2 | rules H2 + L-VAGUE + L-REVIEW + A-W-UNASKED | table rows K2, K38 | facts: x",
            "turn 6 | rules ACCEPT@2026-10-05 + ACT-REQ@2026-10-05 | table rows none | facts: x",
            "turn 9 | rules TRAP-1@2026-10-12 | table rows none | facts: trap: fails",
            "turn 12 | rules TRAP-N@2026-10-19 + RETRO-NOT-NOW | table rows K40 | facts: x",
            "turn 15 | rules ACCEPT@2026-10-26 + NEXT@2026-10-26 | table rows none | facts: trap: passes",
            "turn 17 | rules TRAP-N@2026-11-02 | table rows none | facts: x",
            "turn 18 | rules ANSWER + CONDITION | table rows K29 | facts: answers TRAP-N@2026-11-02; Same as R2",
            "turn 19 | rules RETRO-YES | table rows K41 | facts: x",
            "turn 20 rules broken line"]
    ok = []
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, dir="/tmp") as f:
        f.write("\n".join(rows) + "\n")
    c = counts(f.name)
    ok.append(("9 of 10 lines read, 1 unread", c["lines"] == 9 and len(c["unread"]) == 1))
    ok.append(("trap memos 3 (10-12, 10-19, 11-02)", sorted(c["trap_memos"]) == ["2026-10-12", "2026-10-19", "2026-11-02"]))
    ok.append(("passed the trap in 10-26 only: X2 reachable", c["passed_trap"] == ["2026-10-26"] and not c["x2_not_reached"]))
    ok.append(("F27: the third TRAP rule is memo 5's (turn 17): L0 is the line answering its question (turn 18, K29, `answers TRAP-N@2026-11-02`), "
               "not the TRAP line", c["condition_turn"] == 18 and c["condition_written"] == 18))
    P = lambda *xs: [parse_line(x) for x in xs]  # noqa: E731
    T3 = ("turn 3 | rules TRAP-1@2026-10-12 | table rows none | facts: x", "turn 6 | rules TRAP-N@2026-10-19 | table rows none | facts: x",
          "turn 9 | rules TRAP-N@2026-10-26 | table rows none | facts: x")
    ok.append(("F27: L0 = the K30c line answering the third trap rejection (turn 10)",
               condition_turn(P(*T3, "turn 10 | rules ANSWER | table rows K30c | facts: answers TRAP-N@2026-10-26; No: it is the same as R2")) == 10))
    ok.append(("F27: an answer to another rejection (its facts name TRAP-N@2026-10-19) is not L0; the K30 answer after it is",
               condition_turn(P(*T3, "turn 10 | rules ANSWER | table rows K29 | facts: answers TRAP-N@2026-10-19",
                                "turn 11 | rules ANSWER | table rows K30 | facts: answers TRAP-N@2026-10-26")) == 11))
    ok.append(("F27: no question for the third rejection before its next delivery: L0 = the line judging that delivery (turn 10)",
               condition_turn(P(*T3, "turn 10 | rules VR-REJECT@2026-10-26 | table rows none | facts: x")) == 10))
    ok.append(("F27: the answer given as a brief's `answer` item (K47a) is L0",
               condition_turn(P(*T3, "turn 10 | rules RETRO-NOT-NOW | table rows K40 | facts: x",
                                "turn 11 | rules ANSWER + ITEM-NOT-NOW | table rows K47a, K47 | facts: answers TRAP-N@2026-10-26")) == 11))
    ok.append(("F27: the third TRAP line with nothing after it: the condition has not held", condition_turn(P(*T3)) is None))
    # F28: the retro lines' places
    R1 = (*T3, "turn 10 | rules ANSWER + CONDITION + RETRO-NOT-NOW | table rows K29, K40 | facts: answers TRAP-N@2026-10-26",
          "turn 11 | rules RETRO-YES | table rows K41 | facts: x", "turn 12 | rules ITEM-SERVICE + ITEM-CHECKER | table rows K42, K45 | facts: x",
          "turn 14 | rules PLAN-APPROVE | table rows K44 | facts: x")
    W = ("turn 20 | rules ACCEPT@2026-11-09 + WEEK-LIST | table rows none | facts: x",)
    rp = retro_places(P(*R1, "turn 16 | rules ACCEPT@2026-11-02 + NEXT@2026-11-02 + RETRO-NOT-NOW | table rows K41a | facts: x", *W,
                        "turn 21 | rules LIST-KEEP@t9 | table rows none | facts: x", "turn 22 | rules RETRO-ASK | table rows none | facts: x"))
    ok.append(("F28: RETRO-NOT-NOW at L0 and between retro 1 and retro 2's place (K41a); retro 2 at the line after the week list's LIST-KEEP",
               (rp["L0"], rp["retro1"], rp["retro2"], rp["misplaced"]) == (10, 11, 22, [])))
    rp = retro_places(P(*R1, "turn 16 | rules ACCEPT@2026-11-02 + NEXT@2026-11-02 + RETRO-YES | table rows K41 | facts: x", *W,
                        "turn 21 | rules LIST-KEEP@t9 + RETRO-YES | table rows K41 | facts: an offer in the delivering reply"))
    ok.append(("F28: RETRO-YES between the retros is misplaced; the week list's LIST-KEEP with RETRO-YES is retro 2's place",
               (rp["retro2"], rp["misplaced"]) == (21, ["turn 16: RETRO-YES"])))
    rp = retro_places(P(*T3, "turn 10 | rules ANSWER + CONDITION | table rows K29 | facts: answers TRAP-N@2026-10-26",
                        "turn 11 | rules ACCEPT@2026-10-26 + NEXT@2026-10-26 + RETRO-NOT-NOW | table rows K40 | facts: x"))
    ok.append(("F28: RETRO-NOT-NOW in L1 (after the condition held, before retro 1) is misplaced", rp["misplaced"] == ["turn 11: RETRO-NOT-NOW"]))
    c2 = {"lines": [parse_line(rows[3]), parse_line("turn 14 | rules ACCEPT@2026-11-02 | table rows none | facts: x")]}
    ok.append(("memo 5's verdict makes the condition", condition_turn(c2["lines"]) == 14))
    ok.append(("two memos passed (judged, no TRAP rule): X2 not reached",
               x2_not_reached([parse_line("turn 9 | rules ACCEPT@2026-10-12 | table rows none | facts: trap: passes"),
                               parse_line("turn 11 | rules ACCEPT@2026-10-19 | table rows none | facts: trap: passes")])))
    ok.append(("F2: memos the stream never reached are not passed (one TRAP memo, nothing after): X2 reachable",
               not x2_not_reached([parse_line(rows[3])]) and trap_unreached([parse_line(rows[3])]) == ["2026-10-19", "2026-10-26", "2026-11-02"]))
    ok.append(("F2: a VR-REJECT with no TRAP rule counts as passed", passed_trap([parse_line("turn 9 | rules VR-REJECT@2026-10-12 | table rows none | facts: trap: passes")]) == ["2026-10-12"]))
    ok.append(("the list bounds are LIST-KEEP, ACT-REQ, NEXT and WEEK-LIST lines", counts(f.name)["list_bounds"] == [6, 15]))
    ok.append(("the new rule ids are known", parse_line("turn 3 | rules ITEM-CAUSE + L-NOTHANKS + ITEM-NOT-NOW | table rows K47b, K57 | facts: x")["unknown_rules"] == []))
    V3 = P("turn 1 | rules H6 | table rows none | facts: x", "turn 4 | rules TRAP-1@2026-10-12 | table rows none | facts: x",
           "turn 7 | rules ACCEPT@2026-10-12 + ACT-REQ@2026-10-12 | table rows none | facts: x", "turn 9 | rules L-ASIS@2026-10-19 | table rows none | facts: x")
    ok.append(("F26: Lena's verdict on a delivered version: memo 1 in turn 0 rejected (H6); memo 2 in turn 3 rejected, in turn 5 accepted; "
               "memo 3 as-is; memo 4 never judged", (verdict_after(V3, "2026-10-05", 0), verdict_after(V3, "2026-10-12", 3), verdict_after(V3, "2026-10-12", 5),
                                                     verdict_after(V3, "2026-10-19", 8), verdict_after(V3, "2026-10-26", 8)) == ("rejected", "rejected", "accepted", "as-is", None)))
    ok.append(("an unknown rule is listed", parse_line("turn 3 | rules H9 | table rows none | facts: x")["unknown_rules"] == ["H9"]))
    # C3 (F40 of review 3): an arm-C offer is answered by the same rows as arm R's (K40 before L0; K41 in L1 or L2, after which that line
    # is the arm-C turn and L3 carries no RETRO-ASK; K41a after it); RETRO-ASK at L3 stays the fallback when no offer came
    C0 = (*T3, "turn 10 | rules ANSWER + CONDITION | table rows K29 | facts: answers TRAP-N@2026-10-26")
    L13 = ("turn 12 | rules ACCEPT@2026-11-02 + NEXT@2026-11-02 | table rows none | facts: x", "turn 13 | rules ACCEPT@2026-11-02 | table rows none | facts: x")
    try:
        e1 = retro1_expected(P(*C0, "turn 11 | rules RETRO-YES | table rows K41 | facts: x", *L13), {11})
        rp = retro_places(P(*C0, "turn 11 | rules RETRO-YES | table rows K41 | facts: an arm-C offer of a review",
                            "turn 12 | rules ACCEPT@2026-11-02 | table rows none | facts: x", "turn 13 | rules RETRO-ASK | table rows none | facts: x"))
        ok.append(("C3: an arm-C offer before L1 gets RETRO-YES at L1 (the arm-C turn) and no RETRO-ASK at L3; a RETRO-ASK there is misplaced",
                   (e1["RETRO-YES"], e1["RETRO-ASK"], e1["turn"], rp["retro1"], rp["misplaced"]) == (11, None, 11, 11, ["turn 13: RETRO-ASK"])))
        e2 = retro1_expected(P(*C0, "turn 11 | rules ACCEPT@2026-11-02 | table rows none | facts: x", *L13), set())
        rp = retro_places(P(*C0, "turn 11 | rules RETRO-ASK | table rows none | facts: x", *L13))
        ok.append(("C3: no offer: RETRO-ASK at L3 (turn 13), and a RETRO-ASK at L1 is misplaced",
                   (e2["RETRO-YES"], e2["RETRO-ASK"], e2["turn"], rp["misplaced"]) == (None, 13, 13, ["turn 11: RETRO-ASK"])))
        e3 = retro1_expected(P(*T3[:2], "turn 7 | rules RETRO-NOT-NOW | table rows K40 | facts: x", *C0[2:], "turn 11 | rules ACCEPT@2026-11-02 | table rows none | facts: x", *L13), {7})
        ok.append(("C3: an arm-C offer before L0 gets RETRO-NOT-NOW (K40), and retro 1 then falls back to RETRO-ASK at L3",
                   (e3["RETRO-NOT-NOW"], e3["RETRO-YES"], e3["RETRO-ASK"]) == ([7], None, 13)))
    except NameError as e:
        ok.append((f"C3: retro1_expected ({e})", False))
    ok.append(("C2: the row record `K33 (arm C open form)` reads as one row, K33, with rule ANSWER known",
               (lambda x: (x["rows"], x["unknown_rules"], [r.split(" ")[0] for r in x["rows"]]))(
                   parse_line("turn 30 | rules ANSWER | table rows K33 (arm C open form) | facts: x")) == (["K33 (arm C open form)"], [], ["K33"])))
    # Protocol amendment 1 (`../protocol-amendment-1.md` items 2-4): the action-list rows K62-K66, their forms, and the composition rule
    # (EXT-NO first, then the answers in the order asked)
    for row in ("K62", "K62 (yes/no form)", "K63", "K63 (yes/no form)", "K64", "K64 (yes/no form)", "K65 (open form)", "K65 (yes/no form)",
                "K66", "K66 (yes/no form)"):
        x = parse_line(f"turn 8 | rules ANSWER | table rows {row} | facts: x")
        ok.append((f"amendment 1: the row record `{row}` reads as one row, {row.split(' ')[0]}, rule ANSWER known",
                   x is not None and x["rows"] == [row] and x["unknown_rules"] == []))
    A1 = ("turn 7 | rules ACCEPT@2026-10-05 + L-INJ + ACT-REQ@2026-10-05 | table rows K10 | facts: x",
          "turn 8 | rules EXT-NO + L-INJ + ANSWER | table rows K48, K10, K62, K63, K64, K66, K66 (yes/no form), K66 | facts: R1 v1's turn-7 reply, amendment 1 item 4",
          "turn 9 | rules ANSWER | table rows K65 (yes/no form) | facts: x",
          "turn 10 | rules LIST-KEEP@20261029T110000000000-root-abcd + NEXT@2026-10-12 | table rows none | facts: x")
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, dir="/tmp") as f2:
        f2.write("\n".join(A1) + "\n")
    ca = counts(f2.name)
    ok.append(("amendment 1: the composed line of R1 v1's turn-7 mapping (EXT-NO + L-INJ + ANSWER; K48, K10, then K62-K66) is read, EXT-NO counted once, and it bounds no one-off window "
               "(ACT-REQ at 7 runs to the LIST-KEEP at 10)",
               ca["unknown_rules"] == [] and ca["ext_no"] == 1 and ca["act_req"] == [(7, "2026-10-05")] and ca["list_bounds"] == [7, 10]
               and ca["rows_by_turn"][8][0] == "K48"))
    try:
        ok.append(("amendment 1 item 3: EXT-NO first: the composed line passes; K48 after an answer row is listed; a line without K48 passes",
                   (ca["ext_no_not_first"], ext_no_not_first(P("turn 8 | rules ANSWER + EXT-NO | table rows K62, K48 | facts: x",
                                                               "turn 9 | rules ANSWER | table rows K62, K63 | facts: x")))
                   == ([], [8])))
    except (NameError, KeyError) as e:
        ok.append((f"amendment 1 item 3: ext_no_not_first ({type(e).__name__}: {e})", False))
    ok.append(("amendment 1: K62-K66 are no trap-answer rows (L0 is not moved by an action-list answer after the third TRAP line)",
               condition_turn(P(*T3, "turn 10 | rules ANSWER | table rows K62, K63 | facts: answers TRAP-N@2026-10-26",
                                "turn 11 | rules ANSWER | table rows K29 | facts: answers TRAP-N@2026-10-26")) == 11))
    # The manager's rulings on amendment 1's review (`../manager-decision-row-R1-t7.md`, last section): K67 and K68, A1's composition record
    # `K48, K6n (open form)`, A3 (iii)'s record `K65 (either/or of existing agents)`. lena_lines reads no line text, so A9's numbering has no
    # case here (it is a rule on the line's text, checked by the step against the amendment, not by the parser)
    for row in ("K67", "K68", "K68 (yes/no form)", "K65 (either/or of existing agents)"):
        x = parse_line(f"turn 9 | rules ANSWER | table rows {row} | facts: x")
        ok.append((f"rulings: the row record `{row}` reads as one row, {row.split(' ')[0]}, rule ANSWER known",
                   x is not None and x["rows"] == [row] and x["unknown_rules"] == [] and [r.split(" ")[0] for r in x["rows"]] == [row.split(" ")[0]]))
    A1c = P("turn 9 | rules EXT-NO + ANSWER | table rows K48, K65 (open form) | facts: \"The lead, or shall I hire a list writer?\" (A1)",
            "turn 10 | rules EXT-NO + ANSWER | table rows K48, K64 (open form) | facts: \"Just this list, or shall I set up a weekly list service?\" (A1)",
            "turn 11 | rules ANSWER + EXT-NO | table rows K65 (open form), K48 | facts: x")
    ok.append(("rulings A1: the either/or composition `K48, K65 (open form)` and `K48, K64 (open form)` read with EXT-NO first; K48 after the open line is listed",
               all(x["unknown_rules"] == [] for x in A1c) and [x["rows"] for x in A1c[:2]] == [["K48", "K65 (open form)"], ["K48", "K64 (open form)"]]
               and ext_no_not_first(A1c) == [11]))
    A6r = ("turn 7 | rules ACCEPT@2026-10-05 + ACT-REQ@2026-10-05 | table rows none | facts: x",
           "turn 8 | rules EXT-NO + ANSWER + ANSWER | table rows K48, K67, K68 (yes/no form) | facts: x",
           "turn 9 | rules LIST-KEEP@20261029T110000000000-root-abcd + NEXT@2026-10-12 | table rows none | facts: x")
    A6c = P(*A6r)
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, dir="/tmp") as f3:
        f3.write("\n".join(A6r) + "\n")
    cr = counts(f3.name)
    ok.append(("rulings: a K67 and K68 answer line bounds no one-off window (ACT-REQ at 7 runs to the LIST-KEEP at 9), EXT-NO counted once, "
               "and K67/K68 are no trap-answer rows", cr["list_bounds"] == [7, 9] and cr["ext_no"] == 1 and cr["ext_no_not_first"] == []
               and condition_turn(P(*T3, "turn 10 | rules ANSWER | table rows K67, K68 | facts: answers TRAP-N@2026-10-26")) is None
               and all(x["unknown_rules"] == [] for x in A6c)))
    lines = [f"{'ok' if v else 'MISMATCH'}  {n}" for n, v in ok] + [f"lena_lines selfcheck: {sum(v for _, v in ok)} of {len(ok)} ok"]
    print("\n".join(lines))
    return 0 if all(v for _, v in ok) else 1


if __name__ == "__main__":
    if sys.argv[1:2] == ["--selfcheck"]:
        sys.exit(selfcheck())
    import json
    print(json.dumps(counts(sys.argv[1]), indent=1))
