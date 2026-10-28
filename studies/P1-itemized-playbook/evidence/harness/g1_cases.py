#!/usr/bin/env python3
"""P1 self-check part: guarantees.py's G1 logic on 18.4.1's flows (protocol 12.1's table of orders and states; design 18.4, 18.4.1, 21.1).

Each case builds the script's flow on constructed mail (watch_cases.flow, every order O1-O10 and the variants 12.1's table names), plays the
product's settler (8.5: after every recorded answer, the runtime retire of every item with `retire due` is written, restoring the text the
item had before its watch when it had one), and takes the product's `watch` list at every record time to equal the re-derivation (a product
that follows the design). guarantees.g1 then reads that stream. The expected verdicts and end states below are protocol 12.1's table, written
before the code ran (protocol 13.4 item 6): a mismatch is a harness bug to fix, never an expectation to move. Negative cases check that a
product departing from the design fails: no runtime retire, a retire outside the call, a wrong `restores`, a spurious retire, a `kept`
shown with a related rejection. Iteration 3b (the manager's C3, C2, C1): guarantees.g2's G2(a), one reject note per rejection of a Lena turn on
the case of the memo it judges (rules parsed as a list, `VR-REJECT@<memo date>`), M3-VERDICT + L-ASIS as an accept, and G2(b)'s
`late_detail`, which aggregate.py reads for a stream ended by ruling.

    python3 -B g1_cases.py [--out DIR]   ->  one line per check and `g1_cases: <ok> of <n> checks OK`; exit 0 iff all pass
"""
from __future__ import annotations

import copy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import guarantees as g  # noqa: E402
import rederive_watch as rw  # noqa: E402
import watch_cases as wc  # noqa: E402

HALF = rw.timedelta(microseconds=500000)
CHECKS: list[tuple[str, str, object, object]] = []


def settler(enabled=True, restore_a=False, wrong_restores=False):
    def settle(b: wc.B):
        if not enabled:
            return
        for r in rw.Derivation(b.w).states(None):
            iid = r["item"]
            if not (r["retire_due"] and iid in b.items):
                continue
            if restore_a and iid == "P3":  # O9 edit-other: A (P3) carries B's watch; its own kept text (its add) comes back (8.5)
                addv = next(p for p in b.w.playbooks if p.op == "add" and p.item == "P3")
                b.items[iid], b.why[iid] = addv.live()["P3"], tuple(addv.why.get("P3", ()))
                b.pb("watch", iid, by="runtime (watch)", admitted="watch", related=r["related"], restores=addv.version)
            else:
                b.watch_retire(iid, r["related"], restores=1 if wrong_restores else 0)
    return settle


def stream_of(b: wc.B, ids: dict, replies="", product_edit=None, unread=None) -> g.Stream:
    der = rw.Derivation(b.w)
    times = sorted(set(b.w.record_times()))
    snaps, product = [], {}
    for n, t in enumerate(times, 1):
        tag = f"turn-{n:02d}"
        snaps.append((tag, t + HALF, t + HALF))
        product[tag] = copy.deepcopy(der.states(t + HALF))
    snaps.append(("end", times[-1] + HALF, times[-1] + HALF))
    product["end"] = copy.deepcopy(der.states(None))
    if product_edit:
        product_edit(product)
    for (kind, tag) in (unread or {}):
        if kind == "quality":
            product[tag] = None  # load_stream gives an unread snapshot no product view (protocol 12.1)
    mail = rw.Mail(b.w)
    tt = {}
    for n, v in enumerate(mail.rejections, 1):
        a = mail.answer_time(v.id)
        if a:
            tt[n] = (a - HALF, a + HALF)
    memo_case = {g.MEMOS[i]: ids[f"m{i + 1}"] for i in range(6)} if ids else {}
    if callable(replies):
        replies = replies(b, ids)
    return g.Stream(b.w, memo_case, snaps, product, [], tt, replies, "I", [], {}, dict(unread or {}))


def run(name: str, variant: dict, want: dict, settle=None, replies="", product_edit=None, after=None, unread=None):
    b = wc.B(name)
    v = dict(variant)
    v["settle"] = settle or settler()
    ids = wc.flow(b, v)
    if after:
        after(b, ids)
    res = g.g1(stream_of(b, ids, replies, product_edit, unread))
    got = {"b": res["b"]["verdict"].split(" (")[0], "e": res["e"]["verdict"].split(" (")[0], "f": res["f"]["verdict"].split(" (")[0],
           "a": res["a"]["verdict"].split(" (")[0], "c": res["c"]["verdict"], "d": res["d"]["verdict"].split(" (")[0]}
    for k, x in want.items():
        if k in got:
            CHECKS.append((name, f"G1({k})", got[k], x))
        elif k in ("A", "B", "B_carrier"):
            e = res["expected"].get(k) or {}
            CHECKS.append((name, f"12.1's expected end state of {k}", e.get("want"), x))
        elif k == "reason":
            CHECKS.append((name, "G1(b)'s vacuity reason", x in res["b"]["verdict"], True))
        elif k == "carrier":
            CHECKS.append((name, "B's carrier", res["roles"]["B_carrier"] is not None, x))
        elif k == "hits":
            CHECKS.append((name, "G1(d) keyword hits listed", len(res["d"]["hits"]) >= 1, x))
        elif k == "explained":
            CHECKS.append((name, f"G1(a) explained step listed ({x})", any(x in e for e in res["a"]["explained_steps"]), True))
        elif k == "defect":
            CHECKS.append((name, "G1(f) lists the unread snapshot's traceback as a product defect", bool(res["f"]["product_defects_unread"]), x))
    if res["f"].get("expected_state_fails"):
        CHECKS.append((name, "G1(f) expected-state notes (listed when G1(f) is expected to FAIL)", bool(want.get("f") == "FAIL"), True))
    return res


def unread_entry(tag, reasons, traceback=False):
    return {("quality", tag): {"kind": "quality", "tag": tag, "reasons": reasons, "traceback": traceback,
                               "files": [f"quality/{tag}.json", f"quality/{tag}.stderr.txt", "quality/calls.txt"]}}


def reply_at(offset_s: float, text="The watch could not retire {B} of weekly-memo yet (retire due: R2 and R4 are related); it retries at "
             "the next recorded answer."):
    """A tool result in extract_tool_calls.py's form, recorded `offset_s` seconds after R5's answer (the second related answer of B)."""
    def make(b, ids):
        t = rw.Mail(b.w).answer_time(ids["r5"]) + rw.timedelta(seconds=offset_s)
        ts = t.strftime("%Y-%m-%dT%H:%M:%S.") + f"{t.microsecond // 1000:03d}Z"
        return (f"[{ts}] CALL #9 turn=20 define_service (toolId=@hirearchy/define_service) status=completed args={{}}\n"
                f"    RESULT [{ts}] (5 ms): {text.format(B=ids['B'])}\n")
    return make


LIVE = {"a": "PASS", "b": "PASS", "c": "PASS", "d": "NOT DETERMINED", "e": "PASS", "f": "PASS", "A": "kept", "B": "retired"}


def cases():
    # the base and every order O1-O10 whose expected state is A kept, B retired by runtime (watch) at R5's answer (G1(b) live)
    for name, var in (("O1(a) base", {}), ("O1(b)", {"o1": "b"}), ("O1(c)", {"o1": "c"}), ("O2 feedback(confirms=)", {"o2": "confirms"}),
                      ("O3", {"o3": True}), ("O4", {"o4": True}), ("O5 (memo 3's human accept after R5)", {"o1": "o5"}),
                      ("O6 (memo 4's rework accepted after R5's answer)", {"o6": True}), ("O7 B in memo 3's run", {"b_at": "memo3-run"}),
                      ("O7 B in memo 4's run before its first delivery", {"b_at": "memo4-before"}), ("O8 B edited after R4", {"o8": True}),
                      ("O10 C6's text re-added", {"o10": True})):
        run(name, var, LIVE)
    run("O7 B added after memo 4's first delivery", {"b_at": "memo4-after"},
        {**LIVE, "b": "VACUOUS", "B": "warning", "reason": "O7"})
    run("O9 B retired by its owner after R4, re-added", {"o9": "readd"}, {**LIVE, "B": "retired", "B_carrier": "retired", "carrier": True})
    run("O9 B retired by its owner after R4, restored", {"o9": "restore"}, {**LIVE, "B": None, "B_carrier": "retired", "carrier": True})
    run("O9 B retired, then A edited into B's text (B2)", {"o9": "edit-other"},
        {**LIVE, "A": "as B's carrier", "B": "retired", "B_carrier": "restored", "carrier": True}, settle=settler(restore_a=True))
    for name, var in (("O9 B retired by its owner after R4, nothing after", {"o9": "none"}),
                      ("O9 B retired, then an unrelated add (H3: memo 5's item is no carry)", {"o9": "none-then-other-add"}),
                      ("O9 B retired by its owner before R4", {"o9_early": True})):
        run(name, var, {**LIVE, "b": "VACUOUS", "B": "retired", "carrier": False, "reason": "O9"})
    run("memo 5's answer unrelated to B (18.4)", {"r5_unrelated": True}, {**LIVE, "b": "VACUOUS", "B": "warning", "reason": "memo 5"})
    run("O2's variant: memo 4's answer unrelated to B", {"r4_unrelated": True},
        {**LIVE, "b": "VACUOUS", "e": "FAIL", "B": "rederived", "reason": "memos 4 and 5"})
    run("O5's reported variant: R5's answer names A's criterion", {"o1": "o5", "r5_about_A": True},
        {**LIVE, "b": "VACUOUS", "A": "warning", "B": "warning", "reason": "memo 5"})
    run("an unscripted rejection relates to B early (M5)", {"extra_m2": True}, {**LIVE, "B": "rederived"})
    # negative cases: a product that departs from the design
    run("NEGATIVE no runtime retire written", {}, {**LIVE, "b": "FAIL", "f": "FAIL"}, settle=settler(enabled=False))
    run("NEGATIVE the retire written after the call, no `could not retire` reply", {"late_retire": True}, {**LIVE, "b": "FAIL"})
    run("the retire written after a `The watch could not retire` reply (recorded after the second answer)", {"late_retire": True}, LIVE,
        replies=reply_at(1))
    run("NEGATIVE a `could not retire` reply recorded before the second answer does not excuse a late retire (L5)", {"late_retire": True},
        {**LIVE, "b": "FAIL"}, replies=reply_at(-30))
    run("NEGATIVE the retire of an added rule claims a restore", {}, {**LIVE, "b": "FAIL"}, settle=settler(wrong_restores=True))

    def spurious(b, ids):
        b.watch_retire(ids["A"], [])
    run("NEGATIVE a spurious runtime retire of A", {}, {**LIVE, "b": "FAIL", "f": "FAIL"}, after=spurious)

    def kept_shown(product):
        for tag in [t for t in product if t != "end"]:
            for r in product[tag]:
                if r["item"] == "P4" and r["state"] == "warning":
                    r["state"] = "kept"
    run("NEGATIVE the product shows B kept while it has a related rejection", {}, {**LIVE, "a": "FAIL"}, product_edit=kept_shown)

    def counter_rule(b, ids):
        b.add("Never leave out action items whose owner is given only by initials; write the initials and '(full name not in the notes)'.",
              ["R4", "C13"])
    run("a correct counter-rule matches the keyword screen: listed, not a FAIL (M2)", {}, {**LIVE, "hits": True}, after=counter_rule)
    # iteration 3, P2-M1: the legal 8.1 steps out of `retired` and `warning` into `kept` (two that pass, one that must fail)
    def retire_restore_v1(b, ids):
        it = b.items["P1"]  # v1's "Read the request.", written by root (the client): never watched, `kept`
        b.retire("P1")
        b.restore("P1", it, version=1)  # an exempt restore of a client-written text: the item is live and never watched again
    run("retired -> kept: an exempt restore of a client-written text between the snapshots (P2-M1)", {},
        {**LIVE, "explained": "an exempt restore of a client-written text", "a": "PASS"}, after=retire_restore_v1)

    def retired_shown(product):
        tags = [t for t in product if t != "end"]
        for r in product[tags[len(tags) // 2]]:
            if r["item"] == "P1":
                r["state"] = "retired"
    run("NEGATIVE retired -> kept with no restore between the snapshots (P2-M1)", {}, {**LIVE, "a": "FAIL"}, product_edit=retired_shown)
    corrected_to_kept()
    # iteration 3, P2-M2: an unread snapshot is listed and never read as a pass or as a product state
    run("a turn snapshot unread (empty turn-05.json): G1(a) and G1(f) NOT DETERMINED (P2-M2)", {},
        {**LIVE, "a": "NOT DETERMINED", "f": "NOT DETERMINED", "defect": False}, unread=unread_entry("turn-05", ["empty output"]))
    run("the end view unread (empty end.json): G1(e) NOT DETERMINED, never PASS, and G1(f) no product FAIL (P2-M2)", {},
        {**LIVE, "a": "NOT DETERMINED", "e": "NOT DETERMINED", "f": "NOT DETERMINED"}, unread=unread_entry("end", ["empty output"]))
    run("a turn snapshot unread with a traceback through the product: a product defect, G1(f) FAIL (P2-M2)", {},
        {**LIVE, "a": "NOT DETERMINED", "f": "FAIL", "defect": True},
        unread=unread_entry("turn-05", ["exit 1", "empty output"], traceback=True))
    unread_rule()
    comparisons()
    g2_cases()


def g2_cases():
    """Iteration 3b, the manager's C3 (P3-M3) and C2 (P3-M2): G2(a) needs one human-tier reject note per rejection of a Lena turn, on the
    case of the memo that rejection judges; lena-lines.txt's rules are parsed as a list (`VR-REJECT@<memo date>`). The lines are parsed
    from a constructed lena-lines.txt line by guarantees.lena_line (lena_turns' parser). Expected verdicts written from protocol 12.2 G2(a)
    before the code ran."""

    def one(name, rules, notes_on, want, want_rules=None):
        b = wc.B(name)
        heads = {}
        for m in g.MEMOS[2:]:  # memos 3-6: each a request (the head of its case) with a delivered result
            heads[m] = b.request(m)
            b.done(heads[m])
        start = b.t0 + rw.timedelta(seconds=b.n, microseconds=500000)  # the Lena turn's start, after the deliveries
        for m in notes_on:  # root records the turn's rejections, one note per entry
            b.reject(heads[m])
        end = b.t0 + rw.timedelta(seconds=b.n + 1)
        turns = [g.lena_line(f"turn 7 | rules {rules} | table rows none | facts: constructed (protocol 12.2 G2(a))")]
        s = g.Stream(b.w, dict(heads), [], {}, turns, {7: (start, end)}, "", "I", [], {}, {})
        out = g.g2(s)
        res = dict(out["a"], _b=out["b"])
        CHECKS.append((name, "G2(a)", res["verdict"].split(" (")[0], want))
        if want_rules is not None:
            CHECKS.append((name, "lena-lines.txt rules parsed as a list, in order", turns[0]["rules"], want_rules))
        return res

    m3, m4, m5, m6 = g.MEMOS[2:]
    one("M3-VERDICT + M3-MARTA + L-MIND with one note (memo 4's) (C3)", "M3-VERDICT + M3-MARTA + L-MIND", [m4], "FAIL",
        ["M3-VERDICT", "M3-MARTA", "L-MIND"])
    r = one("M3-VERDICT + M3-MARTA + L-MIND with two notes, on memo 3's and memo 4's cases (C3)", "M3-VERDICT + M3-MARTA + L-MIND",
            [m3, m4], "PASS")
    # C1's input: g2.json (b) carries each late line's kind and the rejection's creation time, which aggregate.py reads for a ruling end
    CHECKS.append(("G2(b) late_detail for aggregate.py (C1)", "two rejections unanswered at the end, no later request: kinds and R ids",
                   [(x["R"], x["kind"]) for x in r["_b"]["late_detail"]], [("R1", "end"), ("R2", "end")]))
    one("NEGATIVE M3-VERDICT + M3-MARTA + L-MIND with two notes, both on memo 4's case (C3)", "M3-VERDICT + M3-MARTA + L-MIND", [m4, m4],
        "FAIL")
    one("M3-VERDICT + VR-REJECT@2026-10-19 + L-MIND with two notes on the two cases (C3)", "M3-VERDICT + VR-REJECT@2026-10-19 + L-MIND",
        [m3, m4], "PASS", ["M3-VERDICT", "VR-REJECT@2026-10-19", "L-MIND"])
    one("VR-REJECT@2026-11-02 + VR-REJECT@2026-11-09 with one note: the second rejection unrecorded (C3; a set kept one)",
        "VR-REJECT@2026-11-02 + VR-REJECT@2026-11-09", [m5], "FAIL", ["VR-REJECT@2026-11-02", "VR-REJECT@2026-11-09"])
    one("VR-REJECT@2026-11-02 + VR-REJECT@2026-11-09 with two notes on the two cases (C3)", "VR-REJECT@2026-11-02 + VR-REJECT@2026-11-09",
        [m5, m6], "PASS")
    one("a VR-REJECT without its memo: NOT DETERMINED, never PASS (C3)", "VR-REJECT", [m5], "NOT DETERMINED")
    one("M3-VERDICT + L-ASIS (Lena declined memo 3's spend): an accept, no reject note expected (C2)", "M3-VERDICT + L-ASIS", [], "PASS",
        ["M3-VERDICT", "L-ASIS"])


def corrected_to_kept():
    """P2-M1: warning -> kept between two snapshots through a corrected link (8.1's exception: the link unrelates the only related
    rejection after D, so K is the link), read by guarantees.g1_a on the product's states (equal to the re-derivation)."""
    b = wc.B("corrected link to kept")
    p, _ = wc.base_rule(b, wc.SUMMARY)
    c1 = b.request(); b.done(c1); r = b.reject(c1); b.link(r, ["C10"])
    c2 = b.request(); b.done(c2); b.accept(c2)
    c3 = b.request(); b.done(c3); b.accept(c3)
    b.link(r, ["none"])  # the corrected link
    s = stream_of(b, {})
    res = g.g1_a(s, rw.Derivation(b.w), rw.Mail(b.w))
    name = "warning -> kept: a corrected link between the snapshots (P2-M1)"
    CHECKS.append((name, "G1(a)", res["verdict"], "PASS"))
    CHECKS.append((name, "G1(a) explained step listed (warning -> kept, a corrected link)",
                   any(f"{p}: warning at" in e and "-> kept at" in e and "corrected link" in e for e in res["explained_steps"]), True))
    b2 = copy.deepcopy(b)
    b2.w.links = b2.w.links[:-1]  # the same product states over files without the corrected link: no exception explains the step
    s2 = g.Stream(b2.w, {}, s.snaps, s.product, [], {}, "", "I", [], {}, {})
    res2 = g.g1_a(s2, rw.Derivation(b2.w), rw.Mail(b2.w))
    CHECKS.append(("NEGATIVE warning -> kept with no corrected link (P2-M1)", "G1(a)", res2["verdict"], "FAIL"))


def unread_rule():
    """P2-M2: rederive_watch.unread_snapshots on constructed calls.txt files (exit, size, JSON, a missing line, a traceback)."""
    import shutil
    import tempfile
    d = Path(tempfile.mkdtemp(prefix="p1-unread-"))
    try:
        (d / "quality").mkdir()
        (d / "services").mkdir()
        (d / "turn-times.txt").write_text("".join(f"turn {n}: 05:00:00 - 05:01:00  utc x - y  exit 0\n" for n in range(1, 6)))
        q = ["turn-01 2026-11-01T05:00:00Z: no org yet, quality not run"]
        for n, (rc, body) in enumerate([(0, '{"services": []}'), (1, ""), (0, ""), (0, "{not json")], 2):
            q.append(f"turn-{n:02d} start 2026-11-01T05:0{n}:00.000001+00:00 end 2026-11-01T05:0{n}:00.500000+00:00 exit {rc}")
            (d / "quality" / f"turn-{n:02d}.json").write_text(body)
        (d / "quality" / "turn-03.stderr.txt").write_text('Traceback (most recent call last):\n  File "/Volumes/workspace/hirearchy/src/'
                                                         'hirearchy/cli.py", line 9, in main\nKeyError: x\n')
        (d / "quality" / "calls.txt").write_text("\n".join(q) + "\n")  # the end: no line at all
        s = ["turn-01 2026-11-01T05:00:00Z: no org yet, services not run"]
        for n in range(2, 6):
            s.append(f"turn-{n:02d} start 2026-11-01T05:0{n}:00.000001+00:00 end 2026-11-01T05:0{n}:00.500000+00:00 exit 0")
            (d / "services" / f"turn-{n:02d}.txt").write_text("- weekly-memo (offered by lead; contract v1, playbook v1)\n")
        s.append("end start 2026-11-01T05:09:00.000001+00:00 end 2026-11-01T05:09:00.500000+00:00 exit 0")
        (d / "services" / "end.txt").write_text("")
        (d / "services" / "calls.txt").write_text("\n".join(s) + "\n")
        u = rw.unread_snapshots(d)
        got = {f"{k} {t}": (u[(k, t)]["reasons"][0].split(" (")[0], u[(k, t)]["traceback"]) for (k, t) in sorted(u)}
        want = {"quality end": ("no snapshot recorded in calls.txt", False), "quality turn-03": ("exit 1", True),
                "quality turn-04": ("empty output", False), "quality turn-05": ("not valid JSON", False),
                "services end": ("empty output", False)}
        CHECKS.append(("the unread rule (P2-M2)", "unread snapshots by exit, size, JSON and a missing line; a traceback through the product",
                       got, want))
    finally:
        shutil.rmtree(d, ignore_errors=True)


def comparisons():
    """rederive_watch's per-snapshot comparison (12.1 G1(f), M4): the race rule, pinned and unpinned keys, root's `services` suffix."""
    b = wc.B("comparisons")
    p = "P3"
    wc.base_rule(b, wc.SUMMARY)
    c1 = b.request(); b.done(c1); r = b.reject(c1)
    t0 = b.w.record_times()[-1] + HALF
    b.link(r, ["C10"])  # written during the snapshot: the product may show it
    t1 = b.w.record_times()[-1] + HALF
    der = rw.Derivation(b.w)
    cands = [der.states(t) for t in rw.window_times(b.w, t0, t1)]
    late = copy.deepcopy(der.states(t1))
    CHECKS.append(("comparisons", "a record written during the snapshot: the product's later view matches (race rule)",
                   rw.compare_window(cands, late, "turn-01"), []))
    CHECKS.append(("comparisons", "the same, compared with the start alone, would mismatch",
                   any(x.startswith("MISMATCH") for x in rw.compare_window(cands[:1], late, "turn-01")), True))
    bad = copy.deepcopy(late)
    next(x for x in bad if x["item"] == p)["state"] = "kept"
    CHECKS.append(("comparisons", "a state no candidate time has: a pinned mismatch",
                   [x.split(":")[0] for x in rw.compare_window(cands, bad, "turn-01")], [f"MISMATCH turn-01 {p} state pinned"]))
    k1 = copy.deepcopy(late)
    next(x for x in k1 if x["item"] == "P1")["k"] = 5  # P1 is a v1 item, kept, never watched: k 0 is pinned there (25.2 item 14, L3)
    CHECKS.append(("comparisons", "k of a never-watched kept item: a pinned mismatch (25.2 item 14)",
                   [x.split(":")[0] for x in rw.compare_window(cands, k1, "turn-01")], ["MISMATCH turn-01 P1 k pinned"]))
    w1 = copy.deepcopy(late)
    next(x for x in w1 if x["item"] == "P1")["waiting"] = 2  # a key the design does not state for an item out of its watch
    CHECKS.append(("comparisons", "waiting of a kept item: an unpinned mismatch",
                   [x.split(":")[0] for x in rw.compare_window(cands, w1, "turn-01")], ["MISMATCH turn-01 P1 waiting unpinned"]))
    CHECKS.append(("comparisons", "pinned keys by state (L3): related of kept and retired pinned, of restored not; k, r, since of a "
                   "never-watched item pinned, of a watched kept item not",
                   [rw.pinned("related", "kept"), rw.pinned("related", "retired"), rw.pinned("related", "restored"),
                    rw.pinned("k", "kept", True), rw.pinned("r", "retired", True), rw.pinned("since", "kept", True),
                    rw.pinned("k", "kept", False), rw.pinned("since", "restored", False), rw.pinned("state", "restored")],
                   [True, True, False, True, True, True, False, False, True]))
    CHECKS.append(("comparisons", "no item yet and no watch list: nothing to compare", rw.compare_window([[]], None, "turn-01"), []))
    # the race rule's lower margin (L4): the link's file lands after the product read the files, though its stamp is 2 s before the
    # snapshot's start; the product's view is the files without it, which only the re-derivation in [start - 5 s, start) gives
    tl = next(x.t for x in b.w.links if x.rejection == r)
    s0 = tl + rw.timedelta(seconds=2)
    c_lo = [der.states(t) for t in rw.window_times(b.w, s0, s0)]
    lower = [der.states(t) for t in rw.lower_times(b.w, s0)]
    before_link = copy.deepcopy(der.states(tl - HALF))
    CHECKS.append(("comparisons", "a record stamped before the start, written after the product's read: RACE-LOWER, reported, no mismatch",
                   sorted({x.split(" ")[0] for x in rw.compare_window(c_lo, before_link, "turn-02", lower)}), ["RACE-LOWER"]))
    CHECKS.append(("comparisons", "the same without the lower margin: a pinned mismatch",
                   any(x.startswith("MISMATCH turn-02 P3 state pinned") for x in rw.compare_window(c_lo, before_link, "turn-02")), True))
    CHECKS.append(("comparisons", "the lower margin is 5 s and starts the candidate list", (rw.RACE_LOWER.total_seconds(),
                   rw.lower_times(b.w, s0)[0] == s0 - rw.timedelta(seconds=5)), (5.0, True)))
    head = "- weekly-memo (offered by lead; contract v2, playbook v2)\n"
    ok_txt = head + '  playbook v2 (2026-11-01): "add P3"; 3 items (1 rules); watched: P3 warning (R2; the next related rejection retires it)\n'
    CHECKS.append(("comparisons", "root's services suffix equal to the re-derivation", rw.compare_services(cands, ok_txt, "weekly-memo", "turn-01"), []))
    CHECKS.append(("comparisons", "root's services suffix naming another related rejection",
                   [x.split(":")[0] for x in rw.compare_services(cands, ok_txt.replace("(R2;", "(R7;"), "weekly-memo", "turn-01")],
                   ["SERVICES-MISMATCH turn-01 P3 related"]))
    CHECKS.append(("comparisons", "root's services suffix: P3 new at the snapshot's start (before the link) matches by the race rule",
                   rw.compare_services(cands, ok_txt.replace("P3 warning (R2; the next related rejection retires it)", "P3 new (0 of 3 clean "
                                       "cases, k 3; waiting for the user's answer to R2)"), "weekly-memo", "turn-01"), []))
    CHECKS.append(("comparisons", "nothing watched in the listing while P3 is warned",
                   [x.split(":")[0] for x in rw.compare_services(cands, head + '  playbook v2 (2026-11-01): "x"; 3 items (1 rules), none watched\n',
                                                                 "weekly-memo", "turn-01")], ["SERVICES-MISMATCH turn-01 P3 item"]))
    CHECKS.append(("comparisons", "a playbook line the parser cannot read is reported, not guessed",
                   [x.split(":")[0] for x in rw.compare_services(cands, head + "  playbook v2 (2026-11-01): something else\n", "weekly-memo",
                                                                 "turn-01")], ["SERVICES-UNREAD turn-01"]))


def main(argv):
    errors = []
    try:
        cases()
    except Exception as e:  # a crash fails the part
        import traceback
        errors.append("".join(traceback.format_exception(e))[-2000:])
    ok, lines = 0, []
    for case, what, got, want in CHECKS:
        good = got == want
        ok += good
        lines.append(f"{'OK  ' if good else 'FAIL'} {case}: {what}: got {got!r}" + ("" if good else f", want {want!r}"))
    lines += [f"FAIL crashed:\n{e}" for e in errors]
    n = len(CHECKS) + len(errors)
    lines.append(f"g1_cases: {ok} of {n} checks OK")
    text = "\n".join(lines)
    print(text)
    if "--out" in argv:
        out = Path(argv[argv.index("--out") + 1])
        out.mkdir(parents=True, exist_ok=True)
        (out / "g1_cases.out").write_text(text + "\n")
    return 0 if ok == n else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
