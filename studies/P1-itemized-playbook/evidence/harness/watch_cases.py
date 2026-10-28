#!/usr/bin/env python3
"""P1 self-check cases for rederive_watch.py (design 18.6, 8.1 rows i-xxv, 18.4.1 O1-O10; F-G0-4).

Every case builds a small service's files with the builder below (tasks, results, verdict notes, link notes, contract versions and
playbook versions, each rendered and parsed again in the item format of 4.1-4.2) and states the expected state of each item at named
moments. The expected states are the design's (the row or the order named in each case), written before the code ran; a mismatch is a
harness bug to fix, never an expectation to move (protocol 13.4). Ids are real ids: E7's v1 holds C1-C9 (C3 the sections rule, C6
"Every row has a named person as Owner"), so A's criterion is C10, the planted rule's C11, its replacement C12 and memo 5's C13 (18.4's
labels C9-C12 by role).

    python3 -B watch_cases.py [--out DIR]     prints one line per check and `watch_cases: <ok> of <n> checks OK`; exit 0 iff all pass.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rederive_watch as rw  # noqa: E402

V1 = [f"criterion {i}" for i in range(1, 10)]
V1[2] = "Besides a title line, the memo has exactly two sections, Decisions and Action items."
V1[5] = "Every row has a named person as Owner."
SUMMARY = "Start the memo with a one-line 'Summary:' of the meeting, then the Decisions, then the Action items."
INITIALS = "Owners as initials only."
FULL = "Owners as full names, as the notes give them."
MARKER = "For someone the notes give only as initials, write the initials and '(full name not in the notes)'."


class B:
    """A service's files, built in time order (one event per second)."""

    def __init__(self, name="case"):
        self.name = name
        self.t0 = datetime(2026, 11, 1, tzinfo=rw.UTC)
        self.n = 0
        self.w = rw.World("weekly-memo", "lead", "root", None)
        self.marks: dict[str, datetime] = {}
        self.acc = list(V1)
        self.pv = 0
        self.items: dict[str, rw.Item] = {}
        self.why: dict[str, tuple[str, ...]] = {}
        self.items_max = 0
        self.contract(self.acc)  # v1 at t0
        self.w.created = self.w.contracts[0].defined

    def tick(self) -> datetime:
        self.n += 1
        return self.t0 + timedelta(seconds=self.n)

    def mid(self, who="root") -> str:
        t = self.tick()
        return t.strftime("%Y%m%dT%H%M%S%f") + f"-{who}-{self.n:04x}"

    def mark(self, name):
        self.marks[name] = self.t0 + timedelta(seconds=self.n, microseconds=500000)
        return self

    # mail
    def request(self, title="memo") -> str:
        i = self.mid()
        self.w.tasks.append(rw.Task(i, "weekly-memo", "lead", "", "", 12, title))
        return i

    def rework(self, of: str, source="human") -> str:
        i = self.mid()
        self.w.tasks.append(rw.Task(i, "weekly-memo", "lead", of, source, 5, "rework"))
        return i

    def done(self, task: str, status="done") -> str:
        i = self.mid("lead")
        self.w.results.append(rw.Result(i, task, status))
        return i

    def verdict(self, task: str, v: str, tier="human") -> str:
        i = self.mid()
        self.w.verdicts.append(rw.Verdict(i, task, v, tier))
        return i

    def accept(self, task, tier="human"):
        return self.verdict(task, "accept", tier)

    def reject(self, task, tier="human"):
        return self.verdict(task, "reject", tier)

    def link(self, rej: str, ids, tier="human") -> str:
        i = self.mid()
        self.w.links.append(rw.Link(i, rej, tuple(ids), tier))
        return i

    # contract
    def contract(self, acc, answers="", about="", initiated="") -> rw.Contract:
        t = self.tick()
        c = rw.Contract(len(self.w.contracts) + 1, t, tuple(acc), "root", answers, about, "Yes, add it.", initiated)
        self.w.contracts.append(c)
        return c

    def answer(self, rej: str, about: str, add=(), remove=(), link=True) -> rw.Contract:
        """define_service(answers=rej, about=...): the version, then the product's link naming answer_ids (0a.2)."""
        acc = [x for x in self.acc if x not in remove] + [x for x in add if x not in self.acc or x in remove]
        self.acc = acc
        c = self.contract(acc, answers=rej, about=about)
        if link:
            cr = rw.Criteria(self.w.contracts)
            self.link(rej, cr.answer_ids(c.version))
        return c

    def cid(self, text) -> str:
        return rw.Criteria(self.w.contracts).ids[text]

    # playbook (rendered in 4.1's format and parsed again by rederive_watch's parser)
    def pb(self, op, item="", by="lead", admitted="", related=(), restores=0):
        self.pv += 1
        steps = [x for x in self.items.values() if x.kind == "step"]
        rules = [x for x in self.items.values() if x.kind == "rule"]
        body = []
        if steps:
            body.append("## Steps")
            for n, s in enumerate(steps, 1):
                suf = f" (WHY {rw.render_why(self.why[s.id])})" if self.why.get(s.id) else ""
                lines = s.text.split("\n")
                body.append(f"{n}. [{s.id}] {lines[0]}" + ("" if len(lines) > 1 else suf))
                body += ["   " + x for x in lines[1:]]
        if rules:
            body += ["", "## Rules"] if body else ["## Rules"]
            for r in rules:
                suf = f" WHY {rw.render_why(self.why[r.id])}" if self.why.get(r.id) else ""
                body.append(f"- [{r.id}] WHEN {r.when} THEN {r.text}{suf}")
        meta = {"service": "weekly-memo", "version": self.pv, "revised": self.tick().isoformat(), "by": by, "op": op,
                "item": item, "admitted": admitted, "items_max": self.items_max, "rules": [r.id for r in rules],
                "why": {k: list(v) for k, v in self.why.items() if k in self.items and v}, "related": list(related),
                "restores": restores}
        p = rw.pversion_of(meta, "\n".join(body) + "\n")
        assert p.parse_error == "", p.parse_error
        assert {i.id: (i.kind, i.text, i.when) for i in p.items} == {i.id: (i.kind, i.text, i.when) for i in self.items.values()}, \
            "render/parse round trip"
        self.w.playbooks.append(p)
        return p

    def first(self, steps):
        for s in steps:
            self.items_max += 1
            self.items[f"P{self.items_max}"] = rw.Item(f"P{self.items_max}", "step", s)
        return self.pb("first", by="root")

    def add(self, text, why, kind="rule", when="always") -> str:
        self.items_max += 1
        iid = f"P{self.items_max}"
        self.items[iid] = rw.Item(iid, kind, text, when if kind == "rule" else "always")
        self.why[iid] = tuple(why)
        self.pb("add", iid, admitted="c")
        return iid

    def edit(self, iid, text, why, kind=None):
        old = self.items[iid]
        self.items[iid] = rw.Item(iid, kind or old.kind, text, old.when)
        self.why[iid] = tuple(why)
        rs = [i for i in why if i.upper().startswith("R")]
        return self.pb("edit", iid, admitted="b" if len(rs) >= 2 else "c")  # 6.2: (b) two assertions, else (c) on a confirmed criterion

    def fmt(self, iid, text):  # a formatting edit (equal tokens: W1)
        old = self.items[iid]
        self.items[iid] = rw.Item(iid, old.kind, text, old.when)
        return self.pb("edit", iid, admitted="exempt")

    def retire(self, iid):
        self.items.pop(iid)
        return self.pb("retire", iid, admitted="")

    def restore(self, iid, item: rw.Item, why=(), version=1):
        self.items[iid] = item
        self.why[iid] = tuple(why)
        return self.pb("restore", iid, admitted="restore", restores=version)

    def watch_retire(self, iid, related, restores=0):
        self.items.pop(iid)
        return self.pb("watch", iid, by="runtime (watch)", admitted="watch", related=related, restores=restores)

    def broken(self):
        """A hand edit of the item file that no longer parses (4.4): readers skip it."""
        self.pv += 1
        p = rw.PVersion(self.pv, self.tick(), "lead", "", "", "", None, {}, (), 0, "line 3: neither a heading, an item nor a continuation")
        self.w.playbooks.append(p)
        return p

    def repair(self):
        """The repair migration of 4.4: every line of the last body as a step with a new id (its list marker dropped, its [P<k>] kept),
        no why, no rule; the old ids leave the body."""
        lines = []
        for x in self.items.values():
            w = rw.render_why(self.why[x.id]) if self.why.get(x.id) else ""
            if x.kind == "rule":
                lines.append(f"[{x.id}] WHEN {x.when} THEN {x.text}" + (f" WHY {w}" if w else ""))
            else:
                lines.append(f"[{x.id}] {x.text}" + (f" (WHY {w})" if w else ""))
        self.items, self.why = {}, {}
        for ln in lines:
            self.items_max += 1
            self.items[f"P{self.items_max}"] = rw.Item(f"P{self.items_max}", "step", ln)
        return self.pb("migrate", by="runtime (migration)", admitted="migrate")

    def state(self, iid, t=None) -> dict:
        rows = rw.Derivation(self.w).states(t)
        return next((r for r in rows if r["item"] == iid), {"state": "absent"})


# ------------------------------------------------------------------------------------------------------------------ the checks
CHECKS: list[tuple[str, str, object, object]] = []


def expect(case: str, what: str, got, want):
    CHECKS.append((case, what, got, want))


def st(b: B, iid: str, at: str | None = None, key="state"):
    r = b.state(iid, b.marks[at] if at else None)
    return r.get(key) if key != "*" else r


def candidates(b: B, rule_why=("R1", "C10")):
    """A served rule P2 admitted now with `rule_why`, then three fresh cases; returns (b, P2, [(task, result)])."""
    return b


def base_rule(b: B, refs_crit: str):
    """v1 playbook, one human rejection R1 answered by a version adding `refs_crit`'s text, a rule P2 citing it."""
    b.first(["Read the request.", "Delegate the memo."])
    m1 = b.request()
    b.done(m1)
    r1 = b.reject(m1)
    b.answer(r1, "C3", add=[SUMMARY], remove=[V1[2]])
    m1r = b.rework(m1)
    b.done(m1r)
    b.accept(m1r)
    p = b.add("Start with a one-line Summary:.", ["R1", b.cid(SUMMARY)])
    return p, r1


def case_two_related():
    b = B("two related rejections")
    p, _ = base_rule(b, SUMMARY)
    c1 = b.request(); b.done(c1); r = b.reject(c1); b.answer(r, "C10", add=["Summary first, always, really."], remove=[SUMMARY])
    b.mark("after first")
    c2 = b.request(); b.done(c2); r2 = b.reject(c2); b.link(r2, ["C10"]); b.mark("after second")
    expect("18.6 a rule with two related rejections", "warning after the first", st(b, p, "after first"), "warning")
    expect("18.6 a rule with two related rejections", "retire due after the second", st(b, p, "after second", "retire_due"), True)
    b.watch_retire(p, ["R2", "R3"])
    expect("18.6 a rule with two related rejections", "retired once the runtime wrote it", st(b, p), "retired")


def case_pending_then_unrelated():
    b = B("pending then unrelated")
    p, _ = base_rule(b, SUMMARY)
    c1 = b.request(); b.done(c1); r = b.reject(c1); b.mark("pending")
    c2 = b.request(); b.done(c2); b.accept(c2)
    c3 = b.request(); b.done(c3); b.accept(c3); b.mark("all judged")
    b.link(r, ["none"]); b.mark("answered")
    expect("18.6 pending then an unrelated answer", "new while pending", st(b, p, "pending"), "new")
    expect("18.6 pending then an unrelated answer", "pending listed", st(b, p, "pending", "pending"), ["R2"])
    expect("18.6 pending then an unrelated answer", "new at E with a pending rejection (8.7)", st(b, p, "all judged"), "new")
    expect("18.6 pending then an unrelated answer", "kept at the unrelated answer (K)", st(b, p, "answered"), "kept")


def case_corrected_link():
    b = B("corrected link")
    p, _ = base_rule(b, SUMMARY)
    c1 = b.request(); b.done(c1); r = b.reject(c1); b.link(r, ["none"])
    c2 = b.request(); b.done(c2); b.accept(c2)
    c3 = b.request(); b.done(c3); b.accept(c3); b.mark("kept")
    b.link(r, ["C10"]); b.mark("corrected")
    expect("18.6 a corrected link (8.1 row xix)", "kept before", st(b, p, "kept"), "kept")
    expect("18.6 a corrected link (8.1 row xix)", "warning after the corrected link (the exception)", st(b, p, "corrected"), "warning")
    # 8.1's exception the other way (iteration 3, P2-M1): a corrected link unrelates the only related rejection; after D the files up to
    # that link derive kept, so K is the link (section 3) and the item goes warning -> kept; before D it goes warning -> new, then kept at K
    b = B("corrected link unrelates")
    p, _ = base_rule(b, SUMMARY)
    c1 = b.request(); b.done(c1); r = b.reject(c1); b.link(r, ["C10"]); b.mark("warned")
    c2 = b.request(); b.done(c2); b.accept(c2)
    c3 = b.request(); b.done(c3); b.accept(c3); b.mark("D")
    b.link(r, ["none"]); b.mark("unrelated")
    name = "18.6 a corrected link unrelates the only related rejection (8.1's exception)"
    expect(name, "after D: warning, warning at D, kept at the corrected link (K = the link)",
           (st(b, p, "warned"), st(b, p, "D"), st(b, p, "unrelated"), st(b, p, "unrelated", "K") == rw.iso(b.marks["unrelated"].replace(microsecond=0))),
           ("warning", "warning", "kept", True))
    b = B("corrected link unrelates before D")
    p, _ = base_rule(b, SUMMARY)
    c1 = b.request(); b.done(c1); r = b.reject(c1); b.link(r, ["C10"]); b.mark("warned")
    b.link(r, ["none"]); b.mark("unrelated")
    c2 = b.request(); b.done(c2); b.accept(c2)
    c3 = b.request(); b.done(c3); b.accept(c3); b.mark("D")
    expect(name, "before D: warning, new after the corrected link, kept at D", (st(b, p, "warned"), st(b, p, "unrelated"), st(b, p, "D")),
           ("warning", "new", "kept"))


def case_delayed_verdict():
    for related in (True, False):
        b = B("delayed verdict")
        p, _ = base_rule(b, SUMMARY)
        c1 = b.request(); b.done(c1); b.accept(c1)
        c2 = b.request(); b.done(c2)  # delivered before the k-th, judged after it
        c3 = b.request(); b.done(c3); b.accept(c3); b.mark("k-th judged, c2 unjudged")
        r = b.reject(c2)
        if related:
            b.link(r, ["C10"])
        else:
            b.link(r, ["none"])
        b.mark("c2 judged")
        name = "18.6 a delayed verdict (rows i, ii), " + ("related" if related else "not related")
        expect(name, "new and waiting while c2 has no verdict (row ii)", (st(b, p, "k-th judged, c2 unjudged"),
               st(b, p, "k-th judged, c2 unjudged", "waiting")), ("new", 1))
        expect(name, "after c2's verdict", st(b, p, "c2 judged"), "warning" if related else "kept")


def case_after_E():
    b = B("after E")
    p, _ = base_rule(b, SUMMARY)
    for _ in range(3):
        c = b.request(); b.done(c); b.accept(c)
    b.mark("kept")
    c4 = b.request(); b.done(c4); r = b.reject(c4); b.link(r, ["C10"]); b.mark("later")
    expect("18.6 a related rejection on a result after E (row iii)", "kept at K", st(b, p, "kept"), "kept")
    expect("18.6 a related rejection on a result after E (row iii)", "still kept: outside the window", st(b, p, "later"), "kept")


def old_rejections(b: B, n_cases=10, link_late=False, version_late=False):
    """n judged cases before the watch start, one of them rejected about C10's text, answered before or after the start."""
    b.first(["Read the request."])
    b.answer_ids_seed = None
    m = b.request(); b.done(m); r0 = b.reject(m); b.answer(r0, "C3", add=[SUMMARY], remove=[V1[2]])
    rr = b.rework(m); b.done(rr); b.accept(rr)
    rej_old = None
    for i in range(n_cases - 1):
        c = b.request(); b.done(c)
        if i == 0:
            rej_old = b.reject(c)
            if not (link_late or version_late):
                b.link(rej_old, ["C10"])
        else:
            b.accept(c)
    p = b.add("Start with a one-line Summary:.", ["R1", "C10"])
    return p, rej_old


def case_old_link_after_start():
    b = B("link after start")
    p, rej = old_rejections(b, link_late=True)
    k0 = st(b, p, None, "*")
    b.link(rej, ["C10"])
    k1 = st(b, p, None, "*")
    expect("18.6 a link on an old rejection after the watch start (8.4)", "r and k unchanged", (k1["k"], k1["r"]), (k0["k"], k0["r"]))
    b2 = B("link before start")
    p2, _ = old_rejections(b2, link_late=False)
    r2 = st(b2, p2, None, "*")
    expect("8.4 r known (10 judged, 2 about C10's text): k from r", "k, r", (r2["k"], r2["r"]), (11, [2, 10]))


def case_old_version_after_start():
    b = B("version after start")
    p, rej = old_rejections(b, version_late=True)
    k0 = st(b, p, None, "*")
    b.answer(rej, "C10", add=["Summary line first, then decisions."], remove=[])
    k1 = st(b, p, None, "*")
    expect("18.6 an answering version of an old rejection defined after the watch start (B3, row xxii)", "r and k unchanged",
           (k1["k"], k1["r"]), (k0["k"], k0["r"]))


def case_b1():
    for order in ("kth-answer-rej", "rej-kth-answer", "answer-rej-kth"):
        b = B("B1")
        p, _ = base_rule(b, SUMMARY)
        c1 = b.request(); b.done(c1); r = b.reject(c1)
        c2 = b.request(); b.done(c2); b.accept(c2)
        c3 = b.request(); b.done(c3)
        c4 = b.request(); b.done(c4)
        evs = {"kth": lambda: b.accept(c3), "answer": lambda: b.link(r, ["C10"])}
        r4 = None
        for e in order.split("-"):
            if e == "rej":
                r4 = b.reject(c4)
                b.link(r4, ["C10"])
            else:
                evs[e]()
        expect(f"18.6 B1 (row xx), order {order}", "retire due", (st(b, p), st(b, p, None, "retire_due")), ("warning", True))


def case_b2():
    b = B("B2")
    p, _ = base_rule(b, SUMMARY)
    other = b.add("Check every Due against the notes.", ["R1", "C10"])
    c1 = b.request(); b.done(c1); r = b.reject(c1); b.link(r, ["C10"])
    b.mark("warned")
    text = b.items[p].text
    b.retire(p)
    b.edit(other, text, ["R1", "C10"])
    b.mark("edited")
    expect("18.6 B2 (row xxi)", "P2 warning before", st(b, p, "warned"), "warning")
    r = st(b, other, "edited", "*")
    expect("18.6 B2 (row xxi)", "the edited item carries P2's warning", (r["state"], r["carried"]), ("warning", p))
    c2 = b.request(); b.done(c2); r2 = b.reject(c2); b.link(r2, ["C10"])
    expect("18.6 B2 (row xxi)", "one more related rejection: retire due", st(b, other, None, "retire_due"), True)


def case_b4():
    # xxiii: C6 removed by one answer (adding the initials text), re-added by a later one (removing it); a rule citing the initials id
    b = B("B4")
    b.first(["Read the request."])
    m = b.request(); b.done(m); r1 = b.reject(m)
    b.answer(r1, "C6", add=[INITIALS], remove=[V1[5]])
    ci = b.cid(INITIALS)
    early = b.request(); b.done(early); r_early = b.reject(early); b.link(r_early, ["C6"])  # answered before the re-add (xxiv)
    p = b.add("Owners as initials only.", ["R1", ci])
    c2 = b.request(); b.done(c2); r2 = b.reject(c2)
    b.answer(r2, ci, add=[V1[5]], remove=[INITIALS])  # re-adds C6's exact text
    crit = rw.Criteria(b.w.contracts)
    expect("B4 (row xxiii)", "the re-added text keeps its id", b.cid(V1[5]), "C6")
    expect("B4 (row xxiii)", "C6's lineage as of the re-add", sorted(crit.lineage("C6", b.w.contracts[-1].defined)), [ci])
    mail = rw.Mail(b.w)
    expect("B4 (row xxiv)", "a rejection answered before the re-add keeps its subjects", sorted(mail.subjects(r_early)), ["C6", "R2"])
    c3 = b.request(); b.done(c3); r3 = b.reject(c3); b.link(r3, ["C6"])
    mail = rw.Mail(b.w)
    expect("B4 (row xxiii)", "a rejection about C6 after the re-add relates to the rule citing the removed id", ci in mail.subjects(r3), True)
    expect("B4 (row xxiii)", "the rule: retire due (R3 at the re-add removed its criterion; R4 about C6)", st(b, p, None, "retire_due"), True)
    # xxv: a cycle C6 -> ci -> C6 -> ci (three answers): the lineage ends, each id once
    b.answer(b.reject(c3), "C6", add=[INITIALS], remove=[V1[5]])
    crit = rw.Criteria(b.w.contracts)
    t = b.w.contracts[-1].defined
    # each lineage as of t is the latest adding version's removal, then that id's, each id once: ci -> {C6}, C6 -> {ci}
    expect("B4 (row xxv)", "the cycle ends, each id once", (sorted(crit.lineage(ci, t)), sorted(crit.lineage("C6", t))), (["C6"], [ci]))


def superseded_base(b: B):
    p, _ = base_rule(b, SUMMARY)
    return p


def case_superseded():
    # v: first delivery superseded by a human rework the user accepts: clean
    b = B("v"); p = superseded_base(b)
    c1 = b.request(); b.done(c1); w1 = b.rework(c1); b.done(w1); b.accept(w1)
    c2 = b.request(); b.done(c2); b.accept(c2); c3 = b.request(); b.done(c3); b.accept(c3)
    r = st(b, p, None, "*")
    expect("18.6 row v", "clean through the rework; kept", (r["state"], r["judged"][0]["judged_task"], r["judged"][0]["superseded_before"]),
           ("kept", w1, 1))
    # vi: the same with a relayed rework the user rejects about the item's refs: related
    b = B("vi"); p = superseded_base(b)
    c1 = b.request(); b.done(c1); w1 = b.rework(c1, "relayed"); b.done(w1); r6 = b.reject(w1); b.link(r6, ["C10"])
    expect("18.6 row vi", "related", st(b, p), "warning")
    # vii: the k-th candidate's first delivery superseded, its rework rejected about the item: related, inside the window
    b = B("vii"); p = superseded_base(b)
    c1 = b.request(); b.done(c1); b.accept(c1); c2 = b.request(); b.done(c2); b.accept(c2)
    c3 = b.request(); b.done(c3); w3 = b.rework(c3); b.done(w3); r7 = b.reject(w3); b.link(r7, ["C10"])
    expect("18.6 row vii", "related inside the window", st(b, p), "warning")
    # viii: a late verdict on the superseded first delivery after the rework's verdict: judged(c), E unchanged
    b = B("viii"); p = superseded_base(b)
    c1 = b.request(); b.done(c1); w1 = b.rework(c1); b.done(w1); b.accept(w1)
    c2 = b.request(); b.done(c2); b.accept(c2); c3 = b.request(); b.done(c3); b.accept(c3)
    before = st(b, p, None, "*")
    b.reject(c1)  # late, on the superseded first delivery, recorded after K
    after = st(b, p, None, "*")
    expect("18.6 row viii", "judged(c), E unchanged; kept", (after["judged"], after["E"], after["state"]),
           (before["judged"], before["E"], "kept"))


def case_review3():
    # xiii: c4 delivered after c3's delivery, rejected and linked before c3's verdict: warning, and still warning after it
    b = B("xiii"); p = superseded_base(b)
    c1 = b.request(); b.done(c1); b.accept(c1); c2 = b.request(); b.done(c2); b.accept(c2)
    c3 = b.request(); b.done(c3); c4 = b.request(); b.done(c4); r4 = b.reject(c4); b.link(r4, ["C10"]); b.mark("linked")
    b.accept(c3)
    expect("18.6 row xiii", "warning, and still warning after c3's verdict", (st(b, p, "linked"), st(b, p)), ("warning", "warning"))
    # xiv: the same rejection recorded after c3's verdict: outside the window, kept
    b = B("xiv"); p = superseded_base(b)
    c1 = b.request(); b.done(c1); b.accept(c1); c2 = b.request(); b.done(c2); b.accept(c2)
    c3 = b.request(); b.done(c3); c4 = b.request(); b.done(c4); b.accept(c3); r4 = b.reject(c4); b.link(r4, ["C10"])
    expect("18.6 row xiv", "kept", st(b, p), "kept")
    # xv: a relayed verdict on c3 before c4's link, the user's verdict on c3 after it: warning stays
    b = B("xv"); p = superseded_base(b)
    c1 = b.request(); b.done(c1); b.accept(c1); c2 = b.request(); b.done(c2); b.accept(c2)
    c3 = b.request(); b.done(c3); c4 = b.request(); b.done(c4); b.accept(c3, "relayed"); r4 = b.reject(c4); b.link(r4, ["C10"])
    b.accept(c3)
    expect("18.6 row xv", "warning", st(b, p), "warning")
    # xvi: after K, a rejection of an early delivery answered as related: kept stays
    b = B("xvi"); p = superseded_base(b)
    cs = []
    for _ in range(3):
        c = b.request(); b.done(c); b.accept(c); cs.append(c)
    r = b.reject(cs[1]); b.link(r, ["C10"])
    expect("18.6 row xvi", "kept stays", st(b, p), "kept")
    # xvii: at D a rejection in the window is pending; another, on a result created before E, answered as related: warning
    b = B("xvii"); p = superseded_base(b)
    c1 = b.request(); b.done(c1); rp = b.reject(c1); c2 = b.request(); b.done(c2); b.accept(c2)
    c3 = b.request(); b.done(c3); b.accept(c3); r2 = b.reject(c2); b.link(r2, ["C10"])
    expect("8.1 row xvii", "warning", st(b, p), "warning")
    # xviii: "same as R<j>" while R<j> is pending: pending; answering R<j> settles both (0 -> 2 in one call)
    b = B("xviii"); p = superseded_base(b)
    c1 = b.request(); b.done(c1); ra = b.reject(c1); c2 = b.request(); b.done(c2); rb = b.reject(c2)
    rid_a = rw.Mail(b.w).rid[ra]
    b.link(rb, [rid_a]); b.mark("same as")
    expect("8.1 row xviii", "both pending", st(b, p, "same as", "pending"), sorted([rid_a, rw.Mail(b.w).rid[rb]], key=rw.id_num))
    b.link(ra, ["C10"])
    expect("8.1 row xviii", "both related in one call: retire due", st(b, p, None, "retire_due"), True)


def case_w1_w2():
    # ix: a move, then a formatting edit of a warned item, then its second related rejection: retire due of the reformatted text
    b = B("ix"); p = superseded_base(b)
    c1 = b.request(); b.done(c1); r = b.reject(c1); b.link(r, ["C10"])
    b.fmt(p, "Start with a one-line **Summary:**.")
    c2 = b.request(); b.done(c2); r2 = b.reject(c2); b.link(r2, ["C10"])
    expect("8.1 row ix", "retire due after W1", (st(b, p), st(b, p, None, "retire_due")), ("warning", True))
    # x: an exempt restore of a client-written text while warned: warning, the clean count restarted, the next related retires it
    b = B("x"); b.first(["Read the request.", "Every row names its owner (C6)."])
    m = b.request(); b.done(m); r1 = b.reject(m); b.link(r1, ["C6"])
    m2 = b.request(); b.done(m2); r2 = b.reject(m2); b.link(r2, ["C6"])
    p = "P2"
    v1item = b.items[p]
    b.edit(p, "Every row names its owner by first name (C6).", ["R1", "R2", "C6"])
    c1 = b.request(); b.done(c1); r = b.reject(c1); b.link(r, ["C6"])
    b.restore(p, v1item)
    r_ = st(b, p, None, "*")
    expect("8.1 row x", "warning after the exempt restore, clean 0", (r_["state"], r_["clean"]), ("warning", 0))
    c2 = b.request(); b.done(c2); r2b = b.reject(c2); b.link(r2b, ["C6"])
    expect("8.1 row x", "the next related rejection: retire due", st(b, p, None, "retire_due"), True)
    # xi: an owner's retire in warning, then a restore of the same id; separately an add of a text with the same text key
    for how in ("restore", "add"):
        b = B("xi"); p = superseded_base(b)
        c1 = b.request(); b.done(c1); r = b.reject(c1); b.link(r, ["C10"])
        it = b.items[p]
        b.retire(p)
        if how == "restore":
            b.items[p] = it; b.why[p] = ("R1", "C10"); b.pb("restore", p, admitted="b")
            q = p
        else:
            q = b.add(it.text, ["R1", "C10"])
        rr = st(b, q, None, "*")
        expect(f"8.1 row xi ({how})", "warning, carried", (rr["state"], rr["carried"] if how == "add" else p), ("warning", p))


def case_repair():
    """8.1 row xii (carried watch (ii), 4.4): a repair migration of a hand-broken file holding a warned rule whose line was not touched."""
    b = B("xii"); p = superseded_base(b)
    c1 = b.request(); b.done(c1); r = b.reject(c1); b.link(r, ["C10"]); b.mark("warned")
    b.broken()
    b.repair()
    q = f"P{b.items_max}"  # the rule's line, repaired as the last step
    rq = st(b, q, None, "*")
    expect("8.1 row xii (repair migration)", "the repaired item: warning, carried from the old id; the old id retired",
           (rq["state"], rq["carried"], st(b, p), rq["since"] == st(b, p, "warned", "since")), ("warning", p, "retired", True))
    expect("8.1 row xii (repair migration)", "the untouched v1 steps come back kept", (st(b, "P4"), st(b, "P5")), ("kept", "kept"))
    c2 = b.request(); b.done(c2); r2 = b.reject(c2); b.link(r2, ["C10"])
    expect("8.1 row xii (repair migration)", "one more related rejection: retire due", st(b, q, None, "retire_due"), True)


def flow(b: B, variant: dict) -> dict:
    """18.4.1's script on constructed mail, with the order variant; returns the item ids and marks. `settle`, when given, is called after
    every recorded answer (it plays the product's settler, 8.5: g1_cases.py writes the runtime retire there)."""
    v = variant
    settle = v.get("settle") or (lambda _b: None)
    b.first(["Read the request.", "Delegate the memo."])
    m1 = b.request("memo 1"); b.done(m1); r1 = b.reject(m1)
    b.answer(r1, "C3", add=[SUMMARY], remove=[V1[2]]); settle(b)
    m1r = b.rework(m1)
    A = b.add("Start with a one-line Summary:.", ["R1", "C10"])  # live from memo 1's rework run
    b.done(m1r); b.accept(m1r)
    m2 = b.request("memo 2"); b.done(m2); r2 = b.reject(m2)
    b.answer(r2, "C6", add=[INITIALS], remove=[V1[5]] if v.get("o10") else []); settle(b)
    m2r = b.rework(m2)
    Bid = None
    if v.get("b_at", "memo2-rework") == "memo2-rework":
        Bid = b.add("Owners as initials only.", ["R2", "C11"], kind="rule", when="always")
    b.done(m2r)
    if v.get("extra_m2"):  # an unscripted rejection of memo 2's rework, linked "same as R2" (protocol 12.1, M5): relates to B early
        rx = b.reject(m2r); b.link(rx, [rw.Mail(b.w).rid[r2]]); settle(b)
        m2r2 = b.rework(m2); b.done(m2r2); b.accept(m2r2)
    else:
        b.accept(m2r)
    m3 = b.request("memo 3")
    if v.get("b_at") == "memo3-run":
        Bid = b.add("Owners as initials only.", ["R2", "C11"])
    if v.get("o9_early"):  # B's owner retires B before R4 (in memo 3's run), nothing after
        b.retire(Bid)
    b.done(m3)
    m4 = b.request("memo 4")
    if v.get("b_at") == "memo4-before":
        Bid = b.add("Owners as initials only.", ["R2", "C11"])
    b.done(m4)
    if v.get("b_at") == "memo4-after":
        Bid = b.add("Owners as initials only.", ["R2", "C11"])
    o1 = v.get("o1", "a")
    r4 = None

    def ans4():
        if v.get("o2") == "confirms":
            b.link(r4, ["C11"])
        elif v.get("r4_unrelated"):  # O2's variant: the answer names another id and removes nothing in C11's lineage
            b.answer(r4, "C1", add=[FULL], remove=[])
        elif v.get("o10"):
            b.answer(r4, "C11", add=[V1[5]], remove=[INITIALS])  # brings C6's exact text back
        else:
            b.answer(r4, "C11", add=[FULL], remove=[INITIALS])
        settle(b)
    if o1 == "a":
        b.accept(m3); r4 = b.reject(m4); ans4()
    elif o1 == "b":
        r4 = b.reject(m4); b.accept(m3); ans4()
    elif o1 == "c":
        r4 = b.reject(m4); b.accept(m3, "relayed"); ans4(); b.accept(m3)
    elif o1 == "o5":
        r4 = b.reject(m4); b.accept(m3, "relayed"); ans4()
    b.mark("R4 answered")
    if v.get("o8"):
        b.edit(Bid, "Owners as initials only, in the Owner cell.", ["R2", "C11"])
    B0 = Bid
    if v.get("o9"):
        it = b.items[Bid]
        b.retire(Bid)
        if v["o9"] == "readd":
            Bid = b.add(it.text, ["R2", "C11"])
        elif v["o9"] == "restore":
            b.items[Bid] = it; b.why[Bid] = ("R2", "C11"); b.pb("restore", Bid, admitted="c")
        elif v["o9"] == "edit-other":
            b.edit(A, it.text, ["R2", "C11"])
            Bid = A
        elif v["o9"] == "none-then-other-add":  # an unrelated add after the retire (memo 5's C13 item, H3): no carry
            b.add("For someone the notes give only as initials, write the initials.", ["R4", "C12"])
    m4r = b.rework(m4); b.done(m4r)
    if not v.get("o6"):
        b.accept(m4r)
    m5 = b.request("memo 5"); b.done(m5)
    target = m5
    if v.get("o4"):
        m5w = b.rework(m5); b.done(m5w); target = m5w
    if v.get("o3"):
        b.reject(target, "relayed")
    r5 = b.reject(target)
    if o1 == "o5":
        b.mark("before memo 3 accept")
    full_id = "C6" if v.get("o10") else (b.cid(FULL) if FULL in b.acc else "C11")
    if v.get("r5_unrelated"):  # root's answer names neither [full] nor a replacement of it (18.4)
        b.answer(r5, "C1", add=[MARKER], remove=[])
    elif v.get("r5_about_A"):  # O5's reported variant: the answer names A's criterion
        b.answer(r5, "C10", add=[MARKER], remove=[])
    else:
        b.answer(r5, full_id, add=[MARKER], remove=[V1[5] if v.get("o10") else FULL] if v.get("replace5", True) and v.get("o2") != "confirms" else [])
    if v.get("late_retire"):  # the settler's write fails in the call; the retire is written later (a later change, 8.5)
        b.n += 40
    settle(b)
    b.mark("R5 answered")
    if v.get("o6"):
        b.accept(m4r)  # O6: memo 4's rework accepted after memo 5's request and R5's answer
    if o1 == "o5":
        b.accept(m3)
        b.mark("memo 3 accepted late")
    m5r = b.rework(m5); b.done(m5r); b.accept(m5r)
    m6 = b.request("memo 6"); b.done(m6); b.accept(m6)
    b.mark("end")
    return {"A": A, "B": Bid, "B0": B0, "m1": m1, "m2": m2, "m3": m3, "m4": m4, "m5": m5, "m6": m6, "r1": r1, "r2": r2, "r4": r4, "r5": r5}


def case_orders():
    def run(name, variant, want_A_end, want_B_R4, want_B_end):
        b = B(name)
        ids = flow(b, variant)
        A, Bid = ids["A"], ids["B"]
        got = (st(b, A), st(b, Bid, "R4 answered") if Bid else "absent", st(b, Bid) if Bid else "absent",
               st(b, Bid, None, "retire_due") if Bid else False)
        expect(f"18.4.1 {name}", "A at the end; B at R4's answer; B at the end (retire due)", got,
               (want_A_end, want_B_R4, want_B_end[0], want_B_end[1]))
        return b, ids
    for o1 in ("a", "b", "c"):
        b, ids = run(f"O1({o1})", {"o1": o1}, "kept", "warning", ("warning", True))
        mail = rw.Mail(b.w)
        Ks = rw.Derivation(b.w).states(None)
        rowA = next(r for r in Ks if r["item"] == ids["A"])
        human_m3 = [v for v in mail.verdicts if v.task == ids["m3"] and v.tier == "human"][0]
        ans4 = max([x.t for x in mail.human_links(ids["r4"])] + ([mail.crit.answering(ids["r4"]).defined] if mail.crit.answering(ids["r4"]) else []))
        expect(f"18.4.1 O1({o1})", "A's K = the later of memo 3's human accept and R4's answer",
               rowA["K"], rw.iso(max(human_m3.t, min([x.t for x in mail.human_links(ids['r4'])] +
                                                       ([mail.crit.answering(ids['r4']).defined] if mail.crit.answering(ids['r4']) else [])))))
    run("O2 (R4 answered by feedback(confirms=..., criterion=[C11]))", {"o2": "confirms"}, "kept", "warning", ("warning", True))
    run("O3 (a relayed verdict on memo 5 before Lena's)", {"o3": True}, "kept", "warning", ("warning", True))
    run("O4 (memo 5's first delivery superseded)", {"o4": True}, "kept", "warning", ("warning", True))
    b, ids = run("O5 (memo 3's human accept after R5)", {"o1": "o5"}, "kept", "warning", ("warning", True))
    expect("18.4.1 O5", "A new before memo 3's human accept (R5 in A's window, unrelated, waiting)", st(b, ids["A"], "R5 answered"), "new")
    expect("18.4.1 O5", "A kept at memo 3's late human accept", st(b, ids["A"], "memo 3 accepted late"), "kept")
    run("O6 (memo 4's rework accepted before memo 5's request: the base)", {}, "kept", "warning", ("warning", True))
    run("O6 (memo 4's rework accepted after memo 5's request and R5's answer)", {"o6": True}, "kept", "warning", ("warning", True))
    run("O7 (B added in memo 3's run before memo 3's delivery)", {"b_at": "memo3-run"}, "kept", "warning", ("warning", True))
    run("O7 (B added in memo 4's run before its first delivery)", {"b_at": "memo4-before"}, "kept", "warning", ("warning", True))
    b, ids = run("O7 (B added after memo 4's first delivery)", {"b_at": "memo4-after"}, "kept", "new", ("warning", False))
    run("O8 (B edited after R4)", {"o8": True}, "kept", "warning", ("warning", True))
    run("O9 (B retired, then re-added)", {"o9": "readd"}, "kept", "absent-or-warning", ("warning", True)) if False else None
    for how in ("readd", "restore", "edit-other"):
        b = B(f"O9 {how}")
        ids = flow(b, {"o9": how})
        r = st(b, ids["B"], None, "*")
        expect(f"18.4.1 O9 (B retired after R4, then {how})", "the carrying item: warning, carried, retire due at R5's answer",
               (r["state"], bool(r["carried"]) or how == "restore", r["retire_due"]), ("warning", True, True))
    b = B("O9 none")
    ids = flow(b, {"o9": "none"})
    expect("18.4.1 O9 (B retired after R4, nothing after)", "B retired; G1(b) vacuous", st(b, ids["B"]), "retired")
    b, ids = run("O10 (memo 4's answer re-adds C6's exact text)", {"o10": True}, "kept", "warning", ("warning", True))
    mail = rw.Mail(b.w)
    expect("18.4.1 O10", "memo 5's question names C6: C6's lineage as of R5's answer holds C11",
           "C11" in mail.crit.lineage("C6", mail.answer_time(ids["r5"])), True)


def case_spend():
    """F-G0-4: a held grant on a blocked case (G0 m0-s1 `6c7a`): 0b.1 3.2 gives 14 of 14 (STUDY.md F-G0-2; 0b.1 line 111)."""
    f = rw.spend_figures({"state": "blocked", "runs": 13, "relayed_runs": 0, "budget": 15, "user_budget": 15, "user_granted": 2,
                          "returned": 3, "user_returned": 3, "contract_budget": 12, "ceilings": [14], "lena_plan_budget": 12,
                          "lena_grants": [{"turn": 11, "runs": 2}], "d14_used": 13})
    expect("18.6 a held grant on a blocked case (m0-s1 6c7a)", "user_cost, case_spend, user_approved, ratio",
           (f["user_cost"], f["case_spend"], f["user_approved"], f["ratio"]), (14, 14, 14, "1.00"))
    f2 = rw.spend_figures({"state": "done", "runs": 13, "relayed_runs": 0, "budget": 15, "user_granted": 2, "returned": 3,
                           "contract_budget": 12, "ceilings": [14]})
    expect("0b.1 3.3 a done case holds nothing", "user_cost, case_spend", (f2["user_cost"], f2["case_spend"]), (13, 13))


def case_k_values():
    import math
    vals = {0.5: 4, 0.3: 7, 0.2: 11, 0.1: 22}
    got = {r: max(3, math.ceil(math.log(0.1) / math.log(1 - r))) for r in vals}
    expect("8.4 k values", "r = 0.5, 0.3, 0.2, 0.1", got, vals)


def case_zero():
    b = B("8.7 zero")
    b.first(["Read the request."])
    expect("8.7 a v1 item, never watched", "kept, k 0, r [0, 0], since None", (st(b, "P1"), st(b, "P1", None, "k"),
           st(b, "P1", None, "r"), st(b, "P1", None, "since")), ("kept", 0, [0, 0], None))
    p, _ = (base_rule(B("8.7 zero2"), SUMMARY))
    b2 = B("8.7 zero3"); p2, _ = base_rule(b2, SUMMARY)
    r = st(b2, p2, None, "*")
    expect("8.7 a watched item with 0 deliveries", "new, clean 0 of k 3", (r["state"], r["clean"], r["k"]), ("new", 0, 3))
    b3 = B("8.7 blocked"); p3, _ = base_rule(b3, SUMMARY)
    c = b3.request(); b3.done(c, "blocked")
    expect("8.7 a blocked result never rejected", "holds nothing", st(b3, p3), "new")
    c2 = b3.request(); b3.done(c2, "blocked"); rr = b3.reject(c2); b3.link(rr, ["C10"])
    expect("8.2 a rejection of a blocked result relates", "warning", st(b3, p3), "warning")


def case_b3_same_stamp():
    """B3 (section 3, K): at an equal microsecond a contract version comes before the link note define_service writes after it."""
    b = B("B3 equal stamp"); p = superseded_base(b)
    c1 = b.request(); b.done(c1); r = b.reject(c1)
    c2 = b.request(); b.done(c2); b.accept(c2); c3 = b.request(); b.done(c3); b.accept(c3)
    acc = list(b.acc) + ["Every memo names its notes file."]
    b.acc = acc
    c = b.contract(acc, answers=r, about="C1")
    lid = c.defined.strftime("%Y%m%dT%H%M%S%f") + "-root-b3b3"
    b.w.links.append(rw.Link(lid, r, tuple(rw.Criteria(b.w.contracts).answer_ids(c.version)), "human"))
    rr = st(b, p, None, "*")
    expect("B3 (section 3: K at an equal microsecond)", "kept, K = the answering version's defined", (rr["state"], rr["K"]),
           ("kept", rw.iso(c.defined)))


ALL = [case_two_related, case_pending_then_unrelated, case_corrected_link, case_delayed_verdict, case_after_E, case_old_link_after_start,
       case_old_version_after_start, case_b1, case_b2, case_b4, case_b3_same_stamp, case_superseded, case_review3, case_w1_w2, case_repair,
       case_orders, case_spend, case_k_values, case_zero]


def main(argv):
    out = None
    if "--out" in argv:
        out = Path(argv[argv.index("--out") + 1])
    errors = []
    for fn in ALL:
        try:
            fn()
        except Exception as e:  # a crash is a failed check of that case
            import traceback
            errors.append((fn.__name__, "".join(traceback.format_exception(e))[-1500:]))
    ok = 0
    lines = []
    for case, what, got, want in CHECKS:
        good = got == want
        ok += good
        lines.append(f"{'OK  ' if good else 'FAIL'} {case}: {what}: got {got!r}" + ("" if good else f", want {want!r}"))
    for name, tb in errors:
        lines.append(f"FAIL {name}: crashed:\n{tb}")
    n = len(CHECKS) + len(errors)
    lines.append(f"watch_cases: {ok} of {n} checks OK")
    text = "\n".join(lines)
    print(text)
    if out:
        out.mkdir(parents=True, exist_ok=True)
        (out / "watch_cases.out").write_text(text + "\n")
    return 0 if ok == n else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
