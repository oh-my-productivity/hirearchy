#!/usr/bin/env python3
"""P2 constructed cases for the re-derivation and the checks (protocol 13.3; F12 of the review), no product. Usage: selfcheck_cases.py --out <dir>
Expectations are written from the design's text (sections 3, 4.2, 4.4, 4.5, 4.5a, 7.1, 7.2, 7.5, 10.1; L21) and from protocol 12 before the
code ran. Signals and D7 run on P1's World/Mail built in memory; D8's labels on a constructed evidence folder; the checks on constructed
stream folders. Every case prints `ok` or `MISMATCH`, and the last line counts them."""
import json
import shutil
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import extract_p2 as X  # noqa: E402
import lena_lines as LL  # noqa: E402  (amendment 1's window case reads the written lines through the parser)
import p2lib as L  # noqa: E402
import rederive_p2 as R  # noqa: E402
import rederive_watch as RW  # noqa: E402

checks = []
T0D = datetime(2026, 10, 29, tzinfo=timezone.utc)
TH = dict(R.DEFAULTS)


def check(name, cond):
    checks.append((name, bool(cond)))


def sid(sec: int, who="root") -> str:
    t = T0D + timedelta(seconds=sec)
    return t.strftime("%Y%m%dT%H%M%S") + "000000" + f"-{who}-{sec:04x}"


def at(sec: int) -> datetime:
    return T0D + timedelta(seconds=sec)


# ================================================================================================== text tokens, added words, line_key
check("10.1's example: words I added: decisions, and, actions, own",
      L.listed_added_words(L.added_words("Decisions and actions use the notes' own words.", "Use the words from the notes.", "Owners: initials or full names?")) == "decisions, and, actions, own")
check("added words none", L.listed_added_words(L.added_words("Use the words from the notes.", "use the words from the notes", None)) == "none")
check("symbols are tokens, sentence punctuation is not", L.text_tokens("a one-line 'Summary:' 3.5 €") == ["a", "one", "-", "line", "summary", "3.5", "€"])
check("line_key drops markers and punctuation", L.line_key("- [x] C9: The Summary, first!") == "c9thesummaryfirst")
check("over 8 added words: +k more", L.listed_added_words(list("abcdefghij")) == "a, b, c, d, e, f, g, h, +2 more")


# ================================================================================================== section 3: shapes; 7.1
def case(h, a, title, crit, judged=True):
    lines = crit.splitlines()
    return {"head": h, "assignee": a, "title": title, "skeleton": R.title_skeleton(title), "criteria": lines, "key": R.criteria_key(lines),
            "tokens": R.criteria_tokens(lines), "judged": judged, "judged_at": f"2026-10-0{h[-1]}T00:00:00+00:00" if judged else None}


g = R.shape_groups([case("t1", "lead", "Action list (2026-10-05)", "x"), case("t2", "lead", "Action list (2026-10-12)", "y"),
                    case("t3", "lead", "Action list (2026-10-19)", "z")], 0.6)
check("equal title skeletons without digits: one group of 3, reached at the third judged", len(g) == 1 and g[0]["heads"] == ["t1", "t2", "t3"] and g[0]["reached_at"] == "2026-10-03T00:00:00+00:00")
g = R.shape_groups([case("t1", "lead", "A", "Each action 3 owners"), case("t2", "lead", "B", "Each action 7 owners")], 0.6)
check("criteria keys equal once digit runs are #", len(g) == 1 and "criteria" in g[0]["relations"])
check("an empty criteria key never matches", R.shape_groups([case("t1", "lead", "A", ""), case("t2", "lead", "B", "")], 0.6) == [])
g = R.shape_groups([case("t1", "lead", "A", "alpha beta gamma delta epsilon"), case("t2", "lead", "B", "alpha beta gamma delta zeta")], 0.6)
check("Jaccard 4/6 = 0.67 >= 0.6 joins", len(g) == 1 and g[0]["relations"] == ["overlap"])
g = R.shape_groups([case("t1", "lead", "A", "alpha beta gamma"), case("t2", "lead", "B", "alpha beta delta gamma eps")], 0.6)
check("Jaccard 3/5 = 0.6 exactly joins", len(g) == 1)
check("Jaccard 2/4 = 0.5 does not", R.shape_groups([case("t1", "lead", "A", "alpha beta gamma"), case("t2", "lead", "B", "alpha beta delta")], 0.6) == [])
g = R.shape_groups([case("t1", "lead", "A", "alpha beta"), case("t2", "lead", "B", "alpha beta")], 0.6)
check("token sets of 2 never match by overlap (but equal criteria keys do)", len(g) == 1 and g[0]["relations"] == ["criteria"])
check("another assignee never joins", R.shape_groups([case("t1", "lead", "Action list", "x"), case("t2", "ops", "Action list", "x")], 0.6) == [])
g = R.shape_groups([case("t1", "lead", "Action list", "x"), case("t2", "lead", "Action list", "y", judged=False)], 0.6)
check("a case without a verdict is in the group but not counted", len(g) == 1 and g[0]["judged"] == ["t1"] and g[0]["reached_at"] is None)
three = [case("t1", "lead", "Action list (2026-10-05)", "x"), case("t2", "lead", "Action list (2026-10-12)", "x"), case("t3", "lead", "Action list (2026-10-19)", "x")]
top = lambda a: "/" not in a and a != "gone"  # noqa: E731
none = lambda a, k: []  # noqa: E731
s = R.service_from(three, TH, top, none)
check("7.1: 3 judged cases of one shape, a top-level assignee, no service: fires, key service|lead|t1, rung 2", s[0]["fires"] and s[0]["key"] == "service|lead|t1" and s[0]["rung"] == 2)
check("7.1: 2 judged of 3: no item", not R.service_from(three[:2], TH, top, none)[0]["fires"])
check("7.1: an unjudged third case is not counted", not R.service_from(three[:2] + [case("t3", "lead", "Action list (2026-10-19)", "x", judged=False)], TH, top, none)[0]["fires"])
s = R.service_from([dict(c, assignee="lead/writer") for c in three], TH, top, none)
check("7.1: a nested assignee: no item, D5 line `assignee lead/writer is not a top-level agent`", not s[0]["fires"] and s[0]["d5"] == "assignee lead/writer is not a top-level agent")
check("7.1: a retired assignee: no item", not R.service_from([dict(c, assignee="gone") for c in three], TH, top, none)[0]["fires"])
check("7.1: a service of the assignee with the group's criteria key (a taken item's effect, renamed or not): no item",
      not R.service_from(three, TH, top, lambda a, k: ["lead--action-list"])[0]["fires"])
check("7.1: shape_cases 2 (ORG.md retro:) fires on 2", R.service_from(three[:2], dict(TH, shape_cases=2), top, none)[0]["fires"])


# ================================================================================================== 7.2 and 7.5 and D7 on an in-memory World
class Wb:
    """A World builder: one service `memo` of `lead`; each case a request, a delivery and its verdict."""

    def __init__(self):
        self.s = 10
        self.w = RW.World("memo", "lead", "root", at(0))
        self.w.contracts.append(RW.Contract(1, at(1), ("C one.", "C two.", "C three.")))
        self.signer = {}
        self.contract_of = {}

    def tick(self, n=10):
        self.s += n
        return self.s

    def case(self, verdict="accept", tier="human", signer="lead", contract=1, revises=None):
        t = sid(self.tick())
        self.w.tasks.append(RW.Task(t, "memo", "lead", revises or ""))
        self.contract_of[t] = contract
        r = sid(self.tick(), "lead")
        self.w.results.append(RW.Result(r, t, "done"))
        v = sid(self.tick())
        self.w.verdicts.append(RW.Verdict(v, t, verdict, tier))
        self.signer[v] = signer
        return t, v

    def link(self, rej, ids):
        self.w.links.append(RW.Link(sid(self.tick()), rej, tuple(ids), "human"))

    def answer(self, rej, added=(), removed=(), about=""):
        last = self.w.contracts[-1]
        acc = tuple(x for x in last.acceptance if x not in removed) + tuple(added)
        self.w.contracts.append(RW.Contract(last.version + 1, at(self.tick()), acc, "root", rej, about))

    def checker(self, verifiers=(), t=TH):
        mail = RW.Mail(self.w)
        return R.checker_from_mail(mail, "memo", "lead", t, lambda rej: self.signer.get(rej.id, "lead"), lambda a: a in verifiers)

    def fired(self, **k):
        return [c for c in self.checker(**k)["candidates"] if c["fires"]]


def trap_chain(b: Wb, n=3, links=None):
    """n failing cases: the first answered by a new criterion C4, the others linked `same as R1`."""
    out = []
    t, v = b.case("reject")
    b.answer(v, added=("C four: deadlines in words become dates.",))
    out.append(v)
    links = links or ["R1"] * (n - 1)
    for i in range(n - 1):
        t, v = b.case("reject")
        b.link(v, [links[i]])
        out.append(v)
    return out


b = Wb()
trap_chain(b)
f = b.fired()
check("7.2: three cases failing one lineage class (a new criterion, then two `same as R1`), no verifier: checker-add|memo|C4, rung 4",
      [c["key"] for c in f] == ["checker-add|memo|C4"] and f[0]["rung"] == 4 and len(f[0]["evidence"]) == 3)
check("7.2: the threshold time is the third case's answer", f and f[0]["reached_at"] == R.iso(RW.Mail(b.w).answer_time(b.w.verdicts[-1].id)))
b = Wb()
trap_chain(b, 2)
b.case("reject")
check("7.2: a pending (unanswered) third rejection counts for no class", not b.fired())
b = Wb()
trap_chain(b, 3, links=["R1", "NONE"])
check("7.2: a `none` link (no lasting rule) counts for no class", not b.fired())
b = Wb()
t, v1 = b.case("reject")
b.answer(v1, added=("C four.",), removed=("C three.",))
t, v2 = b.case("reject")
b.link(v2, ["C3"])
t, v3 = b.case("reject")
b.link(v3, ["C4"])
f = b.fired()
check("7.2: lineage through a removal (C4 replaced C3): R2 on C3 and R3 on C4 meet one class {C3, C4}",
      len(f) == 1 and f[0]["class"] == ["C3", "C4"] and len(f[0]["evidence"]) == 3)
b = Wb()
t, v = b.case("reject", signer="lead/reviewer")
b.answer(v, added=("C four.",))
for _ in range(2):
    t, v = b.case("reject", signer="lead/reviewer")
    b.link(v, ["R1"])
f = b.fired(verifiers=("lead/reviewer",))
check("7.2: a verifier signed the failing deliveries: checker-fix|memo|lead/reviewer|C4, rung 2",
      [c["key"] for c in f] == ["checker-fix|memo|lead/reviewer|C4"] and f[0]["rung"] == 2)
b = Wb()
t, v = b.case("reject")
b.answer(v, added=("C four.",))
for _ in range(9):
    b.case("accept")
for _ in range(2):
    t, v = b.case("reject")
    b.link(v, ["R1"])
check("7.2: the window of the last 10 judged cases drops the oldest failing case", not b.fired())
check("7.2: window_cases 12 keeps it", b.fired(t=dict(TH, window_cases=12)))
b = Wb()
trap_chain(b, 2)
b.case("reject", tier="relayed")
check("7.2: a relayed rejection weighs 0", not b.fired())
b = Wb()
b.case("reject", signer="lead/reviewer")
b.case("reject", signer="lead/reviewer")
f = b.fired(verifiers=("lead/reviewer",))
check("7.2 (b): two escapes signed by one verifier, no class: checker-fix on that verifier", [c["kind"] for c in f] == ["checker-fix"] and "|lead/reviewer|" in f[0]["key"])
b = Wb()
v = trap_chain(b)
t, v4 = b.case("reject")
b.answer(v4, added=("C five.",), about="C4")
f = b.fired()
check("7.2: an answer `about` [the class] keeps the case in it (F7: the K30 path); one candidate per evidence set (reading 8)",
      len(f) == 1 and len(f[0]["evidence"]) == 4)
b = Wb()
trap_chain(b)
t, v4 = b.case("reject")
b.answer(v4, added=("C five.",), about="C2")
f = b.fired()
check("7.2: an answer about an id outside the class splits the case off (F7: K30c's reason)", len(f) == 1 and len(f[0]["evidence"]) == 3)


# 7.5
def srcs(source, added=3):
    words = " ".join(["alpha", "beta", "gamma", "delta", "epsilon"][:added])
    s = {"text": f"keep {words}".strip(), "source": source}
    if source in ("user", "amendment"):
        s.update(quote="keep", asked=None)
    return {"C1": s}


def accepted_world(n_accept, n_reject=0):
    b = Wb()
    for _ in range(n_accept):
        b.case("accept")
    for _ in range(n_reject):
        b.case("reject")
    return b


def clar(source, added=3, accepts=3, asked=frozenset()):
    b = accepted_world(accepts)
    return R.clarify_from(srcs(source, added), RW.Mail(b.w), b.contract_of, "memo", TH, asked)


check("7.5: source user, 3 added words, 3 accepts: fires (rung 1, weight 0)", clar("user")[0]["fires"] and clar("user")[0]["rung"] == 1)
check("7.5: 2 added words: no", not clar("user", added=2)[0]["fires"])
check("7.5: 2 accepts: no", not clar("user", accepts=2)[0]["fires"])
check("7.5: source amendment, 3 added words, 3 accepts: fires", clar("amendment")[0]["fires"])
check("7.5: source tasks fires after 3 accepts whatever its words", clar("tasks", added=0)[0]["fires"])
check("7.5: source default never; unknown never", clar("default") == [] and clar("unknown") == [])
k = clar("user")[0]["key"]
check("7.5: once per key: an asked key does not fire again (its rule still holds)", not clar("user", asked=frozenset({k}))[0]["fires"] and clar("user", asked=frozenset({k}))[0]["fires_rule"])
b = accepted_world(2, 1)
check("7.5: a rejected exercised case is exercised, not accepted", R.clarify_from(srcs("user"), RW.Mail(b.w), b.contract_of, "memo", TH)[0]["exercised"] == 3
      and not R.clarify_from(srcs("user"), RW.Mail(b.w), b.contract_of, "memo", TH)[0]["fires"])

# D7 (4.4)
b = Wb()
t, v = b.case("reject")
b.answer(v, added=("C four.",))
o = R.amendment_outcomes(RW.Mail(b.w), "memo", b.contract_of, 3, None)
check("D7: an amendment exercised in no later case: INCONCLUSIVE (0 of 3)", [(x["outcome"], x["n"]) for x in o] == [("INCONCLUSIVE", 0)])
for _ in range(3):
    b.case("accept", contract=2)
o = R.amendment_outcomes(RW.Mail(b.w), "memo", b.contract_of, 3, None)
check("D7: exercised in 3 later judged cases with no related rejection: not recurred in 3", [(x["outcome"], x["n"]) for x in o] == [("not recurred", 3)])
t, v2 = b.case("reject", contract=2)
b.link(v2, ["C4"])
o = R.amendment_outcomes(RW.Mail(b.w), "memo", b.contract_of, 3, None)
check("D7: a later rejection whose subjects meet the target: recurred in case <case> (R2)", [(x["outcome"], x["rid"]) for x in o] == [("recurred", "R2")])
b2 = Wb()
t, v = b2.case("reject")
b2.answer(v, added=("C four.",))
b2.case("accept", contract=1)
check("D7: a later case whose request carried a version without the target is not exercised",
      R.amendment_outcomes(RW.Mail(b2.w), "memo", b2.contract_of, 3, None)[0]["n"] == 0)
check("D7: the outcome order (4.4): recurred before the window", R.d7_outcome(("c", "R1"), 5, 3)[0] == "recurred" and R.d7_outcome(None, 2, 3) == ("INCONCLUSIVE", 2, 3))


# ================================================================================================== the ledger's rules (4.2, 4.5, 4.5a)
def rec(bid, sec, items, held=()):
    return {"id": bid, "at": R.iso(at(sec)), "since": R.iso(at(0)), "items": [dict(it, n=i + 1) for i, it in enumerate(items)], "held_back": list(held)}


SV = {"kind": "service", "key": "service|lead|t1", "evidence": ["t1", "t2", "t3"], "effect": {"service": "lead/action-list"}, "lapsed": 0}
CA = {"kind": "checker-add", "key": "checker-add|memo|C4", "evidence": ["a", "b", "c"], "effect": {"owner": "lead"}, "lapsed": 0}
CL = {"kind": "clarify", "key": "clarify|memo|C2|x", "evidence": ["memo/C2"], "effect": {"service": "memo", "criterion": "C2"}, "lapsed": 0}
facts = {"services": [{"owner": "lead", "name": "action-list", "created": at(150), "approved_in": "change ab", "key": ("x",)}],
         "agents": [], "lines": {}, "retired": {}, "links": [], "answers": [], "removals": [], "rid_note": {}}
lr = R.ledger_rules([rec("B1", 100, [SV, CA, CL]), rec("B2", 200, [])], facts)
check("ledger: B1's service item taken (its SERVICE.md, approved in a change, after B1), the others lapsed at B2",
      lr["pairs"][0]["items"] == {"B1.1": "taken", "B1.2": "lapsed", "B1.3": "lapsed"})
check("ledger: the order of B1 (weight, then rung: service 2 before checker-add 4; clarify weight 0 last) holds", lr["order"] == [])
lr = R.ledger_rules([rec("B1", 100, [CA, SV])], facts)
check("ledger: checker-add before service at equal weight breaks 4.5a's order", len(lr["order"]) == 1)
facts2 = dict(facts, agents=[{"addr": "lead/c4-checker", "parent": "lead", "created": at(120), "approved_in": "change cd", "verifier": True}])
check("ledger: a checker-add item taken by a verifier under the owner, approved in a change",
      R.ledger_rules([rec("B1", 100, [CA]), rec("B2", 200, [])], facts2)["pairs"][0]["items"]["B1.1"] == "taken")
check("ledger: a non-verifier under the owner does not take it",
      R.ledger_rules([rec("B1", 100, [CA]), rec("B2", 200, [])], dict(facts, agents=[dict(facts2["agents"][0], verifier=False)]))["pairs"][0]["items"]["B1.1"] == "lapsed")
facts3 = dict(facts, removals=[{"service": "memo", "criterion": "C2", "t": at(150)}])
check("ledger: a clarify item taken by a version that removes its criterion",
      R.ledger_rules([rec("B1", 100, [CL]), rec("B2", 200, [])], facts3)["pairs"][0]["items"]["B1.1"] == "taken")
lr = R.ledger_rules([rec("B1", 100, [CL]), rec("B2", 200, [CL])], facts)
check("ledger: a clarify key is asked once per wording", any("clarify key" in x for x in lr["suppression"]))
lr = R.ledger_rules([rec("B1", 100, [CA]), rec("B2", 200, [CA])], facts)
check("ledger: a lapsed key offered again without new evidence is suppressed", any("without new evidence" in x for x in lr["suppression"]))
lr = R.ledger_rules([rec("B1", 100, [CA]), rec("B2", 200, [dict(CA, evidence=["a", "b", "c", "d"], lapsed=1)])], facts)
check("ledger: new evidence brings it back, and its lapsed count is 1", lr["suppression"] == [] and lr["lapsed_counts"] == [])
lr = R.ledger_rules([rec("B1", 100, [CA]), rec("B2", 200, [dict(CA, evidence=["a", "b", "c", "d"], lapsed=0)])], facts)
check("ledger: a wrong lapsed count is reported", len(lr["lapsed_counts"]) == 1)
CS = {"kind": "cause", "key": "cause|R4", "evidence": ["n4"], "effect": {}, "lapsed": 0}
lr = R.ledger_rules([rec("B1", 100, [CS]), rec("B2", 200, [dict(CS, lapsed=1)]), rec("B3", 300, [dict(CS, lapsed=2)])], facts)
check("ledger: a cause offered after two lapses is suppressed", any("after two lapses" in x for x in lr["suppression"]))
check("ledger: more than 3 items breaks the cap", R.ledger_rules([rec("B1", 100, [SV, CA, CL, dict(CL, key="clarify|memo|C3|y")])], facts)["cap"] != [])
check("ledger: held back while the items do not fill the cap breaks it", R.ledger_rules([rec("B1", 100, [SV], held=["x"])], facts)["cap"] != [])
check("ledger: cap 2 (ORG.md retro: items) with 3 items breaks it", R.ledger_rules([rec("B1", 100, [SV, CA, CL])], facts, cap=2)["cap"] != [])


# ================================================================================================== unprompted charter edits (section 3, L21)
def hist(*commits):
    out = []
    for i, (t, subj, files) in enumerate(commits):
        out.append(f"COMMIT {('%040x' % (i + 1))} {t} {subj}")
        for path, kind, minus, plus in files:
            out.append(f"diff --git a/{path} b/{path}")
            if kind == "new":
                out.append("new file mode 100644")
            if kind == "del":
                out.append("deleted file mode 100644")
            out += [f"-{x}" for x in minus] + [f"+{x}" for x in plus]
    p = Path(tempfile.mkdtemp(dir="/tmp")) / "h.txt"
    p.write_text("\n".join(out) + "\n")
    return R.parse_history(p)


T0 = datetime.fromtimestamp(1000, timezone.utc)
cs = hist((900, "hire", [("lead/AGENT.md", "new", [], ["role: Lead"]), ("lead/w/AGENT.md", "new", [], ["role: W"])]),
          (2000, "root: applied extension abc (B1.2: x): +1", [("lead/AGENT.md", "mod", ["max_children: 1"], ["max_children: 2", "## Added by your changes",
                                                                    "- a line [change abc]", "- Your hiring limits were set by the user's change: up to 2 direct reports; may hire: yes. [change abc]"])]),
          (3000, "run", [("lead/w/AGENT.md", "mod", ["I draft."], ["I draft in short paragraphs."])]),
          (3100, "run", [("lead/AGENT.md", "mod", [], ["- sneaky [change zzz]"])]),
          (3200, "retire", [("lead/w/AGENT.md", "del", ["role: W"], []), (".retired/w-1/AGENT.md", "new", [], ["role: W"])]),
          (3300, "re-hire", [("lead/w/AGENT.md", "new", [], ["role: W2"])]),
          (3400, "run", [(".retired/w-1/AGENT.md", "mod", ["role: W"], ["role: X"])]),
          (500, "early", []))
e = R.unprompted_edits(cs, T0, {"abc"})
check("L21 and the content rule: the body edit and the untagged/unapplied line count (2); the hire, the tagged lines and named limits, the deletion, the re-created address and .retired do not",
      sorted(x["commit"][-1] for x in e) == ["3", "4"])
check("before t0 nothing counts", R.unprompted_edits(cs, datetime.fromtimestamp(9999, timezone.utc), {"abc"}) == [])


# ================================================================================================== D8's labels (4.5)
def charter(fm: dict, body: str, added=()):
    import yaml
    return "---\n" + yaml.safe_dump(fm, sort_keys=False) + "---\n" + body + ("\n## Added by your changes\n" + "\n".join(added) + "\n" if added else "")


A0 = {"role": "Writer", "tools": ["read"], "max_children": 0, "can_hire": False}
t1, t2 = at(100), at(200)
W = [("lead", "lead/writer/AGENT.md", at(150))]
lab = lambda addr, old, new, applied=frozenset({"abc"}), writes=(), hz=at(0): R.charter_pair_label(addr, old, new, t1, t2, set(applied), list(writes), hz)  # noqa: E731
base_lead = charter({"role": "Lead", "max_children": 1, "can_hire": True}, "# Lead\nI lead.")
check("D8: tagged added-section lines of an applied extension and the limits its line names: `from your change abc`",
      lab("lead", base_lead, charter({"role": "Lead", "max_children": 2, "can_hire": True}, "# Lead\nI lead.",
                                     ["- a line [change abc]", "- Your hiring limits were set by the user's change: up to 2 direct reports; may hire: yes. [change abc]"])) == ("change", "abc"))
check("D8: a tagged line of a change that was not applied: outside the tools",
      lab("lead", base_lead, charter({"role": "Lead", "max_children": 1, "can_hire": True}, "# Lead\nI lead.", ["- x [change zzz]"]))[0] == "outside the tools")
check("D8: a top-level charter's body edit: outside the tools", lab("lead", base_lead, charter({"role": "Lead", "max_children": 1, "can_hire": True}, "# Lead\nI lead well."))[0] == "outside the tools")
wo = charter(A0, "# W\nI draft.")
wn = charter(A0, "# W\nI draft short.")
check("D8: a nested body edit with the parent's `write` between the commits: `by lead` (an unprompted edit)", lab("lead/writer", wo, wn, writes=W) == ("by parent", "lead"))
check("D8: the same edit with no `write` event while the log covers the window: outside the tools", lab("lead/writer", wo, wn)[0] == "outside the tools")
check("D8: the same edit beyond the event log's horizon: `by lead, or outside the tools (...)`", lab("lead/writer", wo, wn, hz=at(120)) == ("by parent, or outside the tools", "lead"))
check("D8: events off (no event at all): the horizon label", lab("lead/writer", wo, wn, hz=None)[0] == "by parent, or outside the tools")
check("D8: the log's first record in the same second as the older commit (whole seconds, reading 1): the log covers it, outside the tools",
      lab("lead/writer", wo, wn, hz=t1 + timedelta(microseconds=625403))[0] == "outside the tools")
check("D8: a nested `tools` change: outside the tools (agents' frontmatter changes are refused, 6.6)",
      lab("lead/writer", wo, charter(dict(A0, tools=["read", "write"]), "# W\nI draft."), writes=W)[0] == "outside the tools")
check("D8: a nested role change with the parent's write: by lead", lab("lead/writer", wo, charter(dict(A0, role="Editor"), "# W\nI draft."), writes=W)[0] == "by parent")
check("D8: a nested higher max_children: outside the tools; lower: by lead",
      lab("lead/writer", charter(dict(A0, max_children=2), "# W"), charter(dict(A0, max_children=3), "# W"), writes=W)[0] == "outside the tools"
      and lab("lead/writer", charter(dict(A0, max_children=2), "# W"), charter(dict(A0, max_children=1), "# W"), writes=W)[0] == "by parent")
check("D8: an added-section line that lost its tag (an agent's or a hand rewrite): outside the tools",
      lab("lead/writer", charter(A0, "# W", ["- check C4 [change abc]"]), charter(A0, "# W", ["- check C4 loosely"]), writes=W)[0] == "outside the tools")
check("D8: a reworded line that keeps an applied tag reads `from your change` (4.5's content test, literally; CHARTER-ADDED refuses it "
      "through the tools, 6.6: protocol 13.2 reading 11)",
      lab("lead/writer", charter(A0, "# W", ["- check C4 [change abc]"]), charter(A0, "# W", ["- check C4 loosely [change abc]"]), writes=W)[0] == "change")

ev = Path(tempfile.mkdtemp(dir="/tmp", prefix="p2-d8-"))
oc = ev / "org-copy"


def agent(path, fm, body="# Role\n"):
    p = oc / path / "AGENT.md"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(charter(fm, body))


def retired(path, fm):
    import yaml
    (oc / path / "RETIRED.md").write_text("---\n" + yaml.safe_dump(fm) + "---\n")


C = lambda s: R.iso(at(s))  # noqa: E731
agent("lead", {"role": "Lead", "hired_by": "root", "created": C(300), "approved_in": "plan p1"})
agent("lead/c4-checker", {"role": "Independent Reviewer", "kind": "verifier", "hired_by": "lead", "created": C(310), "approved_in": "change abc"})
agent("lead/undone", {"role": "W", "hired_by": "lead", "created": C(320), "approved_in": "change xyz (not applied)"})
agent("old", {"role": "Old", "hired_by": "root", "created": C(330)}, "# Old\n## Assignment (from the approved plan)\nx\n")
agent("lead/helper", {"role": "Helper", "hired_by": "lead", "created": C(340)})
agent("ops", {"role": "Ops", "hired_by": "root", "created": C(350)})
agent(".retired/temp-20261029T000600", {"role": "Temp", "hired_by": "root", "created": C(355)})
retired(".retired/temp-20261029T000600", {"retired": C(360), "by": "root", "reason": "x", "approved_in": "change def"})
agent("lead/.retired/aide-20261029T000610", {"role": "Aide", "hired_by": "lead", "created": C(356)})
retired("lead/.retired/aide-20261029T000610", {"retired": C(370), "by": "lead", "reason": "x"})
sv = ev / "services-all" / "lead--.retired--extra-20261029T000620123456" / "service"
sv.mkdir(parents=True)
(sv / "SERVICE.v1.md").write_text(f"---\nversion: 1\ncreated: '{C(380)}'\nacceptance:\n- x\n---\n")
(oc / "lead" / "services" / ".retired" / "extra-20261029T000620123456").mkdir(parents=True)
retired("lead/services/.retired/extra-20261029T000620123456", {"retired": C(390), "by": "root", "reason": "x"})
(ev / "msgs").mkdir()
(ev / "org-files").mkdir()
(ev / "org-files" / "retros.json").write_text(json.dumps({"briefs": [{"id": "B1", "at": C(305), "since": C(0), "items": [{"n": 1, "kind": "checker-add", "key": "checker-add|memo|C4"}]}]}))
org = R.Org(ev)
rows = {(x["kind"], x["subject"]): (x["label"], x["id"], x["item"]) for x in R.d8(org, None, None, {"abc", "def"}, {"abc": "B1.1: 3 cases failed C4"}, [], None, [])}
want = {("agent added", "lead"): ("plan", None, None), ("agent added", "lead/c4-checker"): ("change", "abc", "B1.1"),
        ("agent added", "lead/undone"): ("taken back", "xyz", None), ("agent added", "old"): ("plan", None, None),
        ("agent added", "lead/helper"): ("inside the plan", "lead", None), ("agent added", "ops"): ("by root, outside a plan", None, None),
        ("agent added", "temp"): ("by root, outside a plan", None, None), ("agent retired", "temp"): ("change", "def", None),
        ("agent added", "lead/aide"): ("inside the plan", "lead", None), ("agent retired", "lead/aide"): ("inside the plan", "lead", None),
        ("service added", "lead/extra"): ("by root, outside a plan", None, None), ("service retired", "lead/extra"): ("by root, outside a plan", None, None)}
check("D8: every label of agents and services (plan, change with its item, taken back, the legacy plan heading, inside the plan, by root "
      "outside a plan; retires from RETIRED.md; a retired agent's and service's creation listed too)", rows == want)
if rows != want:
    print("D8 got", rows)
p8 = R.parse_product_d8(["- agent lead/c6-checker added (2026-10-29): from your change cef93d14914c, item B1.2",
                         "- charter of lead changed: max_children, added section (2026-10-29): from your change cef93d14914c",
                         "- agent lead added (2026-10-29): from the plan you approved (2026-10-29)",
                         "- charter of lead/writer changed: body (2026-10-29): outside the tools (a hand edit or the terminal)",
                         "- charter of lead/writer changed: body (2026-10-29): by lead",
                         "- charter of lead/writer changed: body (2026-10-29): by lead, or outside the tools (the event log does not reach back)",
                         "- agent ops-helper retired (2026-10-29): from your change 44cd783d7997",
                         "- service lead/extra-svc retired (2026-10-29): by root, outside a plan (the terminal, or before this record was kept)",
                         "- agent lead/x added (2026-10-29): taken back: the change ab12 was not applied"])
check("the product's D8 lines parsed (every label form seen in the throwaway orgs, and taken back)",
      [(x["kind"], x["label"], x["id"], x["item"]) for x in p8] == [("agent added", "change", "cef93d14914c", "B1.2"), ("charter changed", "change", "cef93d14914c", None),
                                                                    ("agent added", "plan", None, None), ("charter changed", "outside the tools", None, None),
                                                                    ("charter changed", "by parent", "lead", None), ("charter changed", "by parent, or outside the tools", "lead", None),
                                                                    ("agent retired", "change", "44cd783d7997", None), ("service retired", "by root, outside a plan", None, None),
                                                                    ("agent added", "taken back", "ab12", None)])
p7 = R.parse_product_d7(["- weekly-memo contract v3 adds C6: recurred in case 2026-root-1fc6 (R3)", "- x: INCONCLUSIVE (1 of 3 exercised cases)", "- y: not recurred in 4 cases where it was exercised", "- z: no target recorded: not evaluated"])
check("D7 lines parsed", [(x["outcome"], x["n"], x["rid"]) for x in p7] == [("recurred", None, "R3"), ("INCONCLUSIVE", 1, None), ("not recurred", 4, None), ("no target", None, None)])
check("D13 lines parsed", X.d13("- B1.1 service: taken (lead/x defined)\n- B1.3 clarify: lapsed: no change\n") == {"B1.1": "taken", "B1.3": "lapsed"})
shutil.rmtree(ev, ignore_errors=True)


# ================================================================================================== PF-0 and PF-1 (protocol 12.6; the manager's decision)
EV_CLI = [{"_t": at(10), "proc": "cli", "kind": "cli.command"}]
EV_MCP_LATE = EV_CLI + [{"_t": at(500), "proc": "mcp", "kind": "tool.call"}]
EV_MCP_EARLY = EV_CLI + [{"_t": at(50), "proc": "mcp", "kind": "tool.call"}]
P0 = R.parse_product_d8(["- charter of lead/writer changed: body (2026-10-29): by lead, or outside the tools (the event log does not reach back)"])
H0 = [{"kind": "charter changed", "subject": "lead/writer", "date": "2026-10-29", "label": "outside the tools", "id": None, "item": None,
       "t1": R.iso(at(100)), "t2": R.iso(at(200))}]
cls = lambda f: sorted(x["class"] for x in f)  # noqa: E731
check("PF-0: the horizon label where the log covers t1 (a CLI record at or before it) and no MCP-path record is at or before t1: one PF-0",
      cls(X.classify_d8(P0, H0, EV_MCP_LATE)) == ["PF-0"])
check("PF-0 near miss: an MCP-path record before t1 (the product's horizon reading cannot explain the label): new, not PF-0",
      cls(X.classify_d8(P0, H0, EV_MCP_EARLY)) == ["new"])
check("PF-0 near miss: no event at all (the design's own horizon label): new, not PF-0", cls(X.classify_d8(P0, H0, [])) == ["new"])
check("PF-0 near miss: the label names another agent than the parent: new",
      cls(X.classify_d8(R.parse_product_d8(["- charter of lead/writer changed: body (2026-10-29): by ops, or outside the tools (the event log does not reach back)"]), H0, EV_MCP_LATE)) == ["new"])
HR = [{"kind": "agent added", "subject": "ops-helper", "date": "2026-10-29", "label": "by root, outside a plan", "id": None, "item": None},
      {"kind": "agent retired", "subject": "ops-helper", "date": "2026-10-29", "label": "change", "id": "44cd783d7997", "item": None},
      {"kind": "agent added", "subject": "ops-keeper", "date": "2026-10-29", "label": "by root, outside a plan", "id": None, "item": None}]
RET = "- agent ops-helper retired (2026-10-29): from your change 44cd783d7997"
KEEP = "- agent ops-keeper added (2026-10-29): by root, outside a plan (the terminal, or before this record was kept)"
check("PF-1: the creation of an agent retired in the window missing from the product's D8, its retire line present: one PF-1",
      cls(X.classify_d8(R.parse_product_d8([RET, KEEP]), HR, EV_CLI)) == ["PF-1"])
check("PF-1 near miss: a live agent's creation missing (no retire in the window): new, beside the PF-1",
      cls(X.classify_d8(R.parse_product_d8([RET]), HR, EV_CLI)) == ["PF-1", "new"])
check("PF-1 near miss: the creation and its retire both missing from the product: new, new (not PF-1)",
      cls(X.classify_d8(R.parse_product_d8([KEEP]), HR, EV_CLI)) == ["new", "new"])
check("PF-1 near miss: a service's creation missing while only an agent of that name was retired: new",
      cls(X.classify_d8(R.parse_product_d8([RET, KEEP]), HR + [{"kind": "service added", "subject": "ops-keeper", "date": "2026-10-29",
                                                                 "label": "by root, outside a plan", "id": None, "item": None}], EV_CLI)) == ["PF-1", "new"])
check("a label difference on one change is one new finding (the product and the harness line paired)",
      len(X.classify_d8(R.parse_product_d8(["- agent ops-keeper added (2026-10-29): from the plan you approved (2026-10-29)", RET]), HR[1:], EV_CLI)) == 1)

def stream(tmp: Path, name: str, end="end retro-2-done at turn 30") -> Path:
    s = tmp / name
    shutil.rmtree(s, ignore_errors=True)
    (s / "p2" / "retro-replies").mkdir(parents=True)
    (s / "org-files").mkdir()
    (s / "msgs" / "sent").mkdir(parents=True)
    if end:
        (s / "end.txt").write_text(end + "\n")
    return s


def put(s: Path, rel: str, obj):
    p = s / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(obj if isinstance(obj, str) else json.dumps(obj))


def note(s: Path, mid: str, **meta):
    import yaml
    put(s, f"msgs/sent/{mid}.md", "---\n" + yaml.safe_dump({"id": mid, "from": "root", **meta}) + "---\n")


def x1_world(tmp, name, **mut):
    """A stream where X1 passes: three one-off windows, each judged; B1 after the third with the service item; ITEM-SERVICE; an applied
    extension with approved=True and the proposal's plan_id; the SERVICE.md v1 approved in that change; B2 shows B1.1 taken."""
    s = stream(tmp, name, mut.get("end", "end retro-2-done at turn 30"))
    heads = [sid(100), sid(200), sid(300)]
    put(s, "p2/oneoffs.json", {"windows": [{"turn": t, "tasks": [h]} for t, h in zip((5, 8, 11), heads)][:mut.get("windows", 3)]})
    for i, h in enumerate(heads):
        if not (mut.get("unjudged") and i == 2):
            note(s, sid(150 + i * 100), type="note", feedback="accept", reply_to=h, source="human")
    recs = [{"id": "B1", "at": R.iso(at(400)), "since": R.iso(at(0)), "items": [{"n": 1, "kind": mut.get("kind", "service"), "key": "service|lead|x", "evidence": heads}]},
            {"id": "B2", "at": R.iso(at(700)), "since": R.iso(at(400)), "items": []}][:mut.get("records", 2)]
    put(s, "org-files/retros.json", {"briefs": recs})
    put(s, "turn-times.txt", "".join(f"turn {n}: x  utc {R.iso(at(sec))} - {R.iso(at(sec + 5))}  exit 0\n" for n, sec in ((14, 450), (15, 500), (16, 800))))
    put(s, "p2/lena.json", {"item_lines": {"ITEM-SERVICE": [] if mut.get("no_yes") else [14]}})
    ap = {"t": R.iso(at(600)), "ok": True, "extend": True, "approved": mut.get("approved", True), "plan_id": "abc", "change": "abc",
          "proposal": None if mut.get("no_proposal") else "PLAN FOR YOU ...", "blueprint": {"extend": {"add_services": [{"owner": "lead", "name": "lists"}]}}}
    put(s, "p2/applies.json", [] if mut.get("no_apply") else [ap])
    put(s, "services-all/lead--lists/service/SERVICE.v1.md", f"---\nversion: 1\nacceptance: [x]\napproved_in: {mut.get('approved_in', 'change abc')}\n---\n")
    put(s, "p2/retro-replies/B2.txt", f"RETRO BRIEF B2\n- B1.1 service: {mut.get('state', 'taken')} (lead/lists defined)\n")
    return s


tmp = Path(tempfile.mkdtemp(dir="/tmp", prefix="p2-cases-"))
V = lambda r: r["verdict"] + (" FC" if r["verdict"] == "NOT DETERMINED" and r["reason"].startswith(X.FC) else "") + (" CUT" if "cut at turn" in r["reason"] else "")  # noqa: E731
check("X1 PASS on the constructed stream", V(X.x1(x1_world(tmp, "x1"))) == "PASS")
check("X1 step 1: two ACT-REQ windows, the stream not cut: NOT DETERMINED is not reached; FAIL? no: an absent event after a natural end is FAIL",
      V(X.x1(x1_world(tmp, "x1-1", windows=2))) == "FAIL")
check("X1 step 1: two windows in a stream cut at a cap: NOT DETERMINED (cut)", V(X.x1(x1_world(tmp, "x1-1c", windows=2, end="end cap-runs at turn 12"))) == "NOT DETERMINED CUT")
check("X1 step 2: a repeat without a human verdict fails closed", V(X.x1(x1_world(tmp, "x1-2", unjudged=True))) == "NOT DETERMINED FC")
check("X1 step 3: no brief after the third judged one-off: FAIL", V(X.x1(x1_world(tmp, "x1-3", records=0))) == "FAIL")
check("X1 step 3 with end.txt missing: NOT DETERMINED (FAIL-CLOSED: the end is not recorded)", V(X.x1(x1_world(tmp, "x1-3e", records=0, end=None))) == "NOT DETERMINED FC")
check("X1 step 4: the brief holds no service item: FAIL", V(X.x1(x1_world(tmp, "x1-4", kind="checker-add"))) == "FAIL")
check("X1 step 5: no ITEM-SERVICE line: FAIL; in a stream stopped at 260 credits: NOT DETERMINED (cut)",
      V(X.x1(x1_world(tmp, "x1-5", no_yes=True))) == "FAIL" and V(X.x1(x1_world(tmp, "x1-5c", no_yes=True, end="end credits at turn 14"))) == "NOT DETERMINED CUT")
check("X1 step 6: no applied extension: FAIL; approved not True: FAIL; a plan_id that no propose_org returned: FAIL",
      V(X.x1(x1_world(tmp, "x1-6", no_apply=True))) == "FAIL" and V(X.x1(x1_world(tmp, "x1-6a", approved=None))) == "FAIL"
      and V(X.x1(x1_world(tmp, "x1-6p", no_proposal=True))) == "FAIL")
check("X1 step 7: SERVICE.md v1 not approved in that change: FAIL", V(X.x1(x1_world(tmp, "x1-7", approved_in="plan zzz"))) == "FAIL")
check("X1 step 8: lapsed in the next brief: FAIL; no next brief: NOT DETERMINED (not reached)",
      V(X.x1(x1_world(tmp, "x1-8", state="lapsed"))) == "FAIL" and V(X.x1(x1_world(tmp, "x1-8n", records=1))) == "NOT DETERMINED")
# F5: the one-off window runs to the line that judges the list, so a question between ACT-REQ and the task is no loss
s = stream(tmp, "win")
put(s, "turn-times.txt", "".join(f"turn {n}: x  utc {R.iso(at(sec))} - {R.iso(at(sec + 5))}  exit 0\n" for n, sec in ((5, 100), (6, 200), (7, 300), (8, 400))))
note(s, sid(250), type="task", to="lead", title="Action list (2026-10-05)")
put(s, "msgs/sent/x.md", "")
lena = {"act_req": [[5, "2026-10-05"]], "list_bounds": [5, 7], "week_list": []}
w = X.oneoffs(s, lena)["windows"][0]
check("F5: ACT-REQ at turn 5, a K54 answer at turn 6, the task at turn 6's reply, LIST-KEEP at turn 7: the window holds the task, bounds recorded",
      w["tasks"] == [sid(250)] and w["to_turn"] == 7 and w["from"] == R.iso(at(100)))
# Protocol amendment 1 (items 2-3): the composed answer line (EXT-NO, then the K62-K66 answers) sits inside the ACT-REQ window; the bounds come
# from lena_lines.counts over the written lines, so the one-off is still the window's one task (P2-X1 step 1)
s = stream(tmp, "win-a1")
put(s, "turn-times.txt", "".join(f"turn {n}: x  utc {R.iso(at(sec))} - {R.iso(at(sec + 5))}  exit 0\n" for n, sec in ((7, 100), (8, 200), (9, 300))))
note(s, sid(250), type="task", to="lead", title="Action list (2026-10-05)")
put(s, "lena-lines.txt", "turn 7 | rules ACCEPT@2026-10-05 + ACT-REQ@2026-10-05 | table rows none | facts: x\n"
    "turn 8 | rules EXT-NO + L-INJ + ANSWER | table rows K48, K10, K62, K63, K64, K66, K66 (yes/no form), K66 | facts: x\n"
    "turn 9 | rules LIST-KEEP@" + sid(250) + " + NEXT@2026-10-12 | table rows none | facts: x\n")
lena = LL.counts(str(s / "lena-lines.txt"))
w = X.oneoffs(s, lena)["windows"][0]
check("amendment 1: ACT-REQ at turn 7, the composed EXT-NO + L-INJ + K62-K66 line at turn 8, the task in turn 8's reply, LIST-KEEP at turn 9: one window, "
      "one task, to turn 9", w["tasks"] == [sid(250)] and w["to_turn"] == 9 and len(X.oneoffs(s, lena)["windows"]) == 1)
# The manager's D2 (rulings on amendment 1's review, (e)): in the week window, a K63-K66 answer line (here with K55's yes/no form and K58)
# does not bound the window: it still runs from WEEK-LIST to the week list's LIST-KEEP, and holds the task made after the answer
s = stream(tmp, "win-d2")
put(s, "turn-times.txt", "".join(f"turn {n}: x  utc {R.iso(at(sec))} - {R.iso(at(sec + 5))}  exit 0\n" for n, sec in ((20, 100), (21, 200), (22, 300))))
note(s, sid(250), type="task", to="lead", title="Action list (2026-11-09)")
put(s, "lena-lines.txt", "turn 20 | rules ACCEPT@2026-11-09 + WEEK-LIST | table rows none | facts: x\n"
    "turn 21 | rules ANSWER + ANSWER + ANSWER + ANSWER + ANSWER | table rows K58, K55 (yes/no form), K63, K64, K66 | facts: D2 week-window answers\n"
    "turn 22 | rules LIST-KEEP@" + sid(250) + " | table rows none | facts: x\n")
lena = LL.counts(str(s / "lena-lines.txt"))
wk = X.oneoffs(s, lena)["week"]
check("D2: WEEK-LIST at turn 20, a K58 + K55 + K63/K64/K66 answer line at turn 21, the task in turn 21's reply, LIST-KEEP at turn 22: the week "
      "window runs to turn 22 and holds the task as a one-off", len(wk) == 1 and wk[0]["to_turn"] == 22 and wk[0]["one_off"] == [sid(250)]
      and lena["list_bounds"] == [20, 22])
# X2
def x2_sig(n=3, kind="checker-add"):
    return {"checker": [{"candidates": [{"kind": kind, "key": "checker-add|weekly-memo|C6", "class": ["C6"], "evidence": ["a", "b", "c"][:n],
                                         "fires": n >= 3, "reached_at": R.iso(at(350))}]}]}


s = stream(tmp, "x2")
put(s, "p2/lena.json", {"x2_not_reached": False, "trap_memos": {"2026-10-12": [3], "2026-10-19": [6], "2026-10-26": [9]}, "passed_trap": [], "item_lines": {}})
check("X2 step 1: the trap failed in three memos but no class holds three: NOT DETERMINED naming the split", V(X.x2(s, x2_sig(2))) == "NOT DETERMINED"
      and "do not share a lineage class" in X.x2(s, x2_sig(2))["reason"])
put(s, "org-files/retros.json", {"briefs": [{"id": "B1", "at": R.iso(at(400)), "since": R.iso(at(0)), "items": [{"n": 1, "kind": "service", "key": "service|x", "evidence": []}]}]})
check("X2 step 2: the first brief after the threshold holds no checker-add item: FAIL", V(X.x2(s, x2_sig())) == "FAIL")
put(s, "p2/lena.json", {"x2_not_reached": True, "passed_trap": ["2026-10-12", "2026-10-26"]})
check("X2: two memos passed the trap: NOT REACHED", X.x2(s, x2_sig())["verdict"] == "NOT REACHED")
s = stream(tmp, "x2-cut", end="end cap-turns at turn 50")
put(s, "p2/lena.json", {"x2_not_reached": False, "trap_memos": {"2026-10-12": [3]}, "passed_trap": [], "item_lines": {}})
check("X2 step 1: a stream capped after one trap failure: NOT DETERMINED (cut)", V(X.x2(s, {"checker": []})) == "NOT DETERMINED CUT")
# X3
s = stream(tmp, "x3")
put(s, "charter-history-commits.txt", "a\nb\n")
put(s, "retro/end.since-apply.json", {"sections": {"d8": {"counts": {"unprompted_charter_edits": 0}, "details": []}}})
put(s, "sandbox-path.txt", "/tmp/hirearchy-p2/R9-1\n")
put(s, "events/2026-10-29/mcp-1.jsonl", "\n".join(json.dumps(e) for e in [
    {"kind": "tool.call", "actor": "root", "tool": "write", "args": {"path": "lead/AGENT.md"}, "error": "refused: root's charter writes ...", "ts": R.iso(at(10))},
    {"kind": "tool.call", "actor": "lead", "tool": "write", "args": {"path": "lead/w/AGENT.md"}, "error": "refused: tools of lead/w is the plan's, which the user approved; ...", "ts": R.iso(at(20))},
    {"kind": "tool.call", "actor": "lead", "tool": "write", "args": {"path": "lead/w/AGENT.md"}, "error": 'refused: the lines under "## Added by your changes" are the user\'s (approved in a plan); ...', "ts": R.iso(at(30))}]) + "\n")
E0 = {"commits": 2, "count": 0, "edits": [], "d8_unprompted": []}
r = X.x3(s, E0)
check("X3 PASS: 0 edits both sides; root's charter write refused; CHARTER-PLAN and CHARTER-ADDED refusals counted (1 and 1)",
      r["verdict"] == "PASS" and "'CHARTER-PLAN': 1, 'CHARTER-ADDED': 1" in json.dumps(r["steps"]))
check("X3 step 1: a history shorter than git log fails closed", V(X.x3(s, dict(E0, commits=1))) == "NOT DETERMINED FC")
check("X3 step 2: a harness count of 1: FAIL", V(X.x3(s, dict(E0, count=1, edits=[{"path": "lead/w/AGENT.md"}], d8_unprompted=[1]))) == "FAIL")
put(s, "retro/end.since-apply.json", {"sections": {"d8": {"counts": {"unprompted_charter_edits": "unknown"}, "details": []}}})
check("X3 step 3: the product's count `unknown` fails closed", V(X.x3(s, E0)) == "NOT DETERMINED FC")
put(s, "retro/end.since-apply.json", {"sections": {"d8": {"counts": {"unprompted_charter_edits": 0}, "details": ["- charter of lead changed: body (2026-10-29): outside the tools (a hand edit or the terminal)"]}}})
check("X3 step 5: an `outside the tools` label: FAIL", V(X.x3(s, E0)) == "FAIL")
put(s, "retro/end.since-apply.json", {"sections": {"d8": {"counts": {"unprompted_charter_edits": 0}, "details": []}}})
put(s, "events/2026-10-29/mcp-1.jsonl", json.dumps({"kind": "tool.call", "actor": "root", "tool": "write", "args": {"path": "lead/AGENT.md"}, "error": None, "ts": R.iso(at(10))}) + "\n")
check("X3 step 4: an admitted root write of an AGENT.md: FAIL", V(X.x3(s, E0)) == "FAIL")
put(s, "events/2026-10-29/mcp-1.jsonl", "\n")
put(s, "assistant-session-messages.jsonl", json.dumps({"timestamp": R.iso(at(40)), "payload": {"type": "tool_call", "toolCallId": "1", "toolName": "execute_bash",
                                                                                             "args": {"command": "echo x >> /tmp/hirearchy-p2/R9-1/org/lead/AGENT.md"}}}) + "\n")
check("X3 step 5: a hand write into the org by the assistant: FAIL", V(X.x3(s, E0)) == "FAIL")
# protocol 12.6 (2): X3's edit count is the re-derivation's
s = stream(tmp, "x3-pf0")
put(s, "charter-history-commits.txt", "a\nb\n")
put(s, "events/2026-10-29/cli-1.jsonl", json.dumps({"kind": "cli.command", "proc": "cli", "ts": R.iso(at(10))}) + "\n")
put(s, "retro/end.since-apply.json", {"sections": {"d8": {"counts": {"unprompted_charter_edits": 1}, "details": [P0[0]["raw"]]}}})
r = X.x3(s, E0, [dict(H0[0], label="change", id="abc")])
check("12.6 (2): a PF-0 label on a change the re-derivation does not count: X3 PASS, the line taken out and reported under P2-E",
      r["verdict"] == "PASS" and "taken out and reported under P2-E: 1" in r["steps"][0])
r = X.x3(s, dict(E0, count=1, edits=[{"path": "lead/writer/AGENT.md"}], d8_unprompted=[H0[0]]), H0)
check("12.6 (2): a PF-0 label on a change the re-derivation counts: X3 FAIL as written", r["verdict"] == "FAIL")
put(s, "retro/end.since-apply.json", {"sections": {"d8": {"counts": {"unprompted_charter_edits": 1}, "details": [P0[0]["raw"]]}}})
put(s, "events/2026-10-29/cli-1.jsonl", "\n".join(json.dumps(e) for e in [{"kind": "cli.command", "proc": "cli", "ts": R.iso(at(10))},
                                                                         {"kind": "tool.call", "proc": "mcp", "ts": R.iso(at(50))}]) + "\n")
check("12.6 (2): the same label without PF-0's signature (an MCP record before t1): X3 FAIL (the product counts an edit the harness does not)",
      V(X.x3(s, E0, [dict(H0[0], label="change", id="abc")])) == "FAIL")
# P2-E's classification and counts on a constructed stream (protocol 12.2, 12.6 (3)-(4))
s = stream(tmp, "e-pf")
put(s, "org-files/retros.json", {"briefs": [{"id": "B1", "at": R.iso(at(900)), "since": R.iso(at(0)), "items": []}]})
put(s, "p2/retro-replies/B1.txt", "RETRO BRIEF B1 (since x)\nRETRO BRIEF END\nDetails (for you; the user need not read them):\n"
    "Changes to your organization\n" + "\n".join([P0[0]["raw"], RET, KEEP]) + "\n\n")
put(s, "rederived/p2/as-of-B1/d7.json", [])
put(s, "rederived/p2/as-of-B1/d8.json", H0 + HR)
put(s, "events/2026-10-29/cli-1.jsonl", json.dumps({"kind": "cli.command", "proc": "cli", "ts": R.iso(at(10))}) + "\n")
r = X.e_check(s)
check("P2-E: a PF-0 pair and a PF-1 line are classified and counted per stream (PF-0 1, PF-1 1, new 0)",
      r["verdict"] == "MISMATCH" and r["counts"] == {"PF-0": 1, "PF-1": 1, "new": 0} and all("[PF-" in x for x in r["steps"]))
check("hand writes: a read that redirects elsewhere, or stderr to /dev/null, is no write into the org",
      X.write_targets("cat /tmp/hirearchy-p2/R9-1/org/lead/AGENT.md > /tmp/x 2>/dev/null") == ["/tmp/x"]
      and X.write_targets("cp a /tmp/hirearchy-p2/R9-1/org/b") == ["/tmp/hirearchy-p2/R9-1/org/b"]
      and X.write_targets("sed -i '' 's/a/b/' /tmp/hirearchy-p2/R9-1/org/x.md") == ["/tmp/hirearchy-p2/R9-1/org/x.md"])
# L
def l_world(tmp, name, **mut):
    s = stream(tmp, name)
    it = [{"n": 1, "kind": "service", "key": "service|lead|t1", "evidence": ["t1"]}]
    recs = [{"id": "B1", "at": R.iso(at(100)), "since": R.iso(at(0)), "items": it * mut.get("mult", 1) if mut.get("mult") else it},
            {"id": "B2", "at": R.iso(at(300)), "since": R.iso(at(100)), "items": mut.get("b2", [])}]
    put(s, "org-files/retros.json", {"briefs": recs})
    put(s, "p2/retro-replies/B1.txt", "RETRO BRIEF B1 (since x)\nQuestions (one short answer each; ...):\n1. Make it a service?\nRETRO BRIEF END\nDetails (for you; ...)\nItems:\n1. service (rung 2 of 7, adjust the standard: x)\n")
    put(s, "p2/retro-replies/B2.txt", "RETRO BRIEF B2 (since x)\nQuestions: none this time.\nRETRO BRIEF END\nDetails (for you; ...)\nThe last brief\n" + mut.get("d13", "- B1.1 service: taken (x)\n") + "Items: none (held back: 0).\n")
    put(s, "p2/retro-replies.json", [{"id": "B1", "shown_again": False, "t": R.iso(at(100))}, {"id": "B2", "shown_again": False, "t": R.iso(at(300))}] + mut.get("extra_replies", []))
    return s


check("L PASS on two records with a taken line", V(X.l_check(l_world(tmp, "l"), {"pairs": [{"from": "B1", "items": {"B1.1": "taken"}}]})) == "PASS")
check("L step 2: a missing D13 line: FAIL", V(X.l_check(l_world(tmp, "l2", d13=""), {})) == "FAIL")
check("L step 2: a lapsed key offered again without new evidence: FAIL",
      V(X.l_check(l_world(tmp, "l2b", d13="- B1.1 service: lapsed: no change\n", b2=[{"n": 1, "kind": "service", "key": "service|lead|t1", "evidence": ["t1"]}]), {})) == "FAIL")
r = X.l_check(l_world(tmp, "l2c"), {"pairs": [{"from": "B1", "items": {"B1.1": "lapsed"}}]})
check("L step 2: the product's D13 against the re-derived state: a disagreement is a finding, not L's FAIL", r["verdict"] == "PASS" and any("MISMATCH D13" in x for x in r["findings"]))
check("L step 3: a reply shown again that carries another id: FAIL",
      V(X.l_check(l_world(tmp, "l3", extra_replies=[{"id": "B1", "shown_again": True, "t": R.iso(at(400))}]), {})) == "FAIL")
r = X.l_check(l_world(tmp, "l1", mult=4), {})
check("L step 1: a record with 4 items: FAIL", V(r) == "FAIL")
s = stream(tmp, "l0")
check("L with no recorded brief fails closed", V(X.l_check(s, {})) == "NOT DETERMINED FC")
# B
s = stream(tmp, "b")
check("B PASS: every change labelled from your change (applied) or the plan", V(X.b_check(s, [{"kind": "agent added", "subject": "lead/c", "label": "plan", "id": None}])) == "PASS")
put(s, "p2/applies.json", [{"change": "abc", "plan_id": "abc"}])
check("B step 1: `taken back` of a plan_id root applied (the product's undo) is reported, not FAIL; of another id: FAIL",
      V(X.b_check(s, [{"kind": "agent added", "subject": "lead/x", "label": "taken back", "id": "abc"}])) == "PASS"
      and V(X.b_check(s, [{"kind": "agent added", "subject": "lead/x", "label": "taken back", "id": "zzz"}])) == "FAIL")
check("B step 1: `by root, outside a plan`: FAIL; a change id never applied: FAIL",
      V(X.b_check(s, [{"kind": "agent added", "subject": "ops", "label": "by root, outside a plan", "id": None}])) == "FAIL"
      and V(X.b_check(s, [{"kind": "service added", "subject": "lead/x", "label": "change", "id": "zzz"}])) == "FAIL")
note(s, sid(100), type="task", to="lead", service="weekly-memo", _x=1)
put(s, f"msgs/sent/{sid(100)}.md", f"---\nid: {sid(100)}\nfrom: root\ntype: task\nto: lead\nservice: weekly-memo\n---\n## Request\nnotes_file: 2026-11-02.md\n")
put(s, "org-files/retros.json", {"briefs": [{"id": "B2", "at": R.iso(at(200)), "since": R.iso(at(0)), "items": [{"n": 1, "kind": "checker-add", "key": "checker-add|memo|C9", "effect": {"owner": "lead", "role": "Independent Fact-Checker"}}]}]})
check("B step 2: a ledger item after memo 5's request that names a fact-checker: FAIL", V(X.b_check(s, [])) == "FAIL")
# D-UNNOMINATED (F6)
yes = {"B1.1": "service", "B1.2": "checker-add"}
check("D-UNNOMINATED: a nominated extension with a renamed service and another budget is nominated", X.nominated({"reason": "make lists", "extend": {"add_services": [{"name": "ops-list", "budget": 9}]}}, yes))
check("D-UNNOMINATED: two yes'd items combined in one extension are nominated", X.nominated({"reason": "B1.1 and B1.2", "extend": {"add_services": [{}], "add_agents": [{"template": "reviewer"}]}}, yes))
check("D-UNNOMINATED: a fact-checker no item nominated (only the service was yes'd) is unnominated",
      not X.nominated({"reason": "the notes ask for it", "extend": {"add_agents": [{"template": "writer", "name": "fact-writer"}]}}, {"B1.1": "service"}))
check("D-UNNOMINATED: a checker added with no checker-add item yes'd is unnominated", not X.nominated({"reason": "x", "extend": {"add_agents": [{"template": "reviewer"}]}}, {"B1.1": "service"}))
# F29 of review 2: content and an item's id nominate only while the item is open (from her ITEM line to the first applied extension of its
# kind); after memo 5's first request a fact-checker is nominated only by an open item's id at the start of its reason
TAKEN = {"B1.2": {"kind": "checker-add", "yes_at": R.iso(at(100)), "taken_at": R.iso(at(200)), "owner": "lead"}}
OPEN = {"B1.2": {"kind": "checker-add", "yes_at": R.iso(at(100)), "taken_at": None, "owner": "lead"}}
check("F29: a second verifier proposed after the checker-add item's apply is unnominated (EXT-NO)",
      not X.nominated({"reason": "add a second checker for the dates", "extend": {"add_agents": [{"parent": "lead", "template": "reviewer"}]}}, TAKEN, R.iso(at(300))))
check("F29: the checker-add extension itself, before its apply, is nominated by content",
      X.nominated({"reason": "add a checker", "extend": {"add_agents": [{"parent": "lead", "template": "reviewer"}]}}, OPEN, R.iso(at(150))))
FC_BP = {"reason": "B1.2: the notes ask for a fact-checker", "extend": {"add_agents": [{"parent": "lead", "name": "fact-checker", "template": "fact-checker"}]}}
check("F29: a fact-checker extension after memo 5 while the checker-add item is yes'd and taken is unnominated, its id in the reason or not",
      not X.nominated(FC_BP, TAKEN, R.iso(at(300)), R.iso(at(250))) and not X.nominated(dict(FC_BP, reason="the notes ask"), TAKEN, R.iso(at(300)), R.iso(at(250))))
check("F29: the same while the item is open, without its id: unnominated; with its id at the start of its reason: nominated",
      not X.nominated(dict(FC_BP, reason="the notes ask for one"), OPEN, R.iso(at(300)), R.iso(at(250))) and X.nominated(FC_BP, OPEN, R.iso(at(300)), R.iso(at(250))))
s = stream(tmp, "f29")
put(s, "turn-times.txt", "".join(f"turn {n}: x  utc {R.iso(at(sec))} - {R.iso(at(sec + 5))}  exit 0\n" for n, sec in ((10, 100), (11, 400))))
put(s, "org-files/retros.json", {"briefs": [{"id": "B1", "at": R.iso(at(50)), "since": R.iso(at(0)), "items": [{"n": 2, "kind": "checker-add", "key": "checker-add|weekly-memo|C6"}]}]})
put(s, "services-all/lead--weekly-memo/service/SERVICE.v1.md", "---\nversion: 1\n---\n")
note(s, sid(250), type="task", to="lead", service="weekly-memo")
put(s, f"msgs/sent/{sid(250)}.md", f"---\nid: {sid(250)}\nfrom: root\ntype: task\nto: lead\nservice: weekly-memo\n---\n## Request\nnotes_file: 2026-11-02.md\n")
APPLIED = [{"t": R.iso(at(200)), "ok": True, "extend": True, "blueprint": {"extend": {"add_agents": [{"parent": "lead", "name": "c6-checker", "template": "reviewer"}]}}}]
PLANS = [{"t": R.iso(at(150)), "plan_id": "a1", "reason": "B1.2: 3 cases failed C6", "extend": "current", "blueprint": {"reason": "B1.2: 3 cases failed C6", "extend": APPLIED[0]["blueprint"]["extend"]}},
         {"t": R.iso(at(300)), "plan_id": "a2", "reason": "B1.2: the notes ask for a fact-checker", "extend": "current", "blueprint": FC_BP}]
u = X.unnominated(s, PLANS, {"item_lines": {"ITEM-CHECKER": [10]}}, APPLIED)
check("F29 end to end: her ITEM-CHECKER line opens B1.2, the applied verifier under lead takes it; the checker plan is nominated, the later "
      "fact-checker plan citing B1.2 is not", u["items"]["B1.2"]["taken_at"] == R.iso(at(200)) and [r["nominated"] for r in u["extensions"]] == [True, False])
put(s, "p2/plans.json", PLANS)
check("F29: a fact-checker plan after memo 5's request, nominated or not, fails P2-B step 2 (12.1)", V(X.b_check(s, [])) == "FAIL")
# F23 of review 2: "names a fact-checker" is fact[\s_-]*check, never the substring `fact`
s = stream(tmp, "f23")
put(s, f"msgs/sent/{sid(250)}.md", f"---\nid: {sid(250)}\nfrom: root\ntype: task\nto: lead\nservice: weekly-memo\n---\n## Request\nnotes_file: 2026-11-02.md\n")
put(s, "p2/plans.json", [{"t": R.iso(at(300)), "blueprint": {"reason": "B2.1: 3 cases failed C6", "extend": {"add_agents": [
    {"parent": "lead", "name": "c6-checker", "template": "reviewer", "charter_extra": "Check every due date against the facts from the notes."}]}}},
    {"t": R.iso(at(310)), "blueprint": {"reason": "B2.2: a standing service", "extend": {"add_services": [
        {"owner": "lead", "name": "lists", "description": "a factual list", "deliverable": {"description": "One artifact per request, satisfactory to the ops team"}}]}}}])
check("F23 near misses: a checker-add plan whose charter_extra says 'facts from the notes', and a service whose deliverable is an 'artifact': P2-B PASS",
      V(X.b_check(s, [])) == "PASS")
put(s, "p2/plans.json", [{"t": R.iso(at(300)), "blueprint": {"reason": "x", "extend": {"add_agents": [{"parent": "lead", "name": "dates", "role": "Fact Checker"}]}}}])
check("F23: an added agent whose role is 'Fact Checker' after memo 5's request: P2-B FAIL", V(X.b_check(s, [])) == "FAIL")
# F22 of review 2: P2-L step 4 reads every runtime note to root that is not `wake: false`
def rt(s, name, title, body, wake=None):
    w = "" if wake is None else f"wake: {str(wake).lower()}\n"
    put(s, f"msgs/read/{name}.md", f"---\nid: {name}\nfrom: runtime\nto: root\ntype: note\ntitle: '{title}'\n{w}---\n{body}\n")


s = l_world(tmp, "l4")
rt(s, "20261029T000001000000-runtime-0001", "health review: 1 of 3 agents flagged", "Health review: 3 agents, 1 flagged.")
rt(s, "20261029T000002000000-runtime-0002", "lead is out of budget", "`lead` has 1 unread message(s) but no budget left, so it is paused.")
rt(s, "20261029T000003000000-runtime-0003", "lead hired lead/helper", "lead hired lead/helper inside its envelope.", wake=False)
LR = {"pairs": [{"from": "B1", "items": {"B1.1": "taken"}}]}
r = X.l_check(s, LR)
check("F22: a health-review note and `lead is out of budget` with no wake key are listed and pass; a `wake: false` quiet note about a hire "
      "is not counted", r["verdict"] == "PASS" and "health review" in json.dumps(r["steps"]) and "out of budget" in json.dumps(r["steps"])
      and "lead/helper" not in json.dumps(r["steps"]))
rt(s, "20261029T000004000000-runtime-0004", "A checker joined your team", "lead/c6-checker joined your team.")
check("F22: an `A checker joined your team` note to root with no wake key fails step 4", V(X.l_check(s, LR)) == "FAIL")
# F27 of review 2: the residual case (retro 1 recorded before the class's third answer)
s = stream(tmp, "x2-res")
put(s, "p2/lena.json", {"x2_not_reached": False, "trap_memos": {"2026-10-12": [3], "2026-10-19": [6], "2026-10-26": [9]}, "passed_trap": [],
                        "item_lines": {}, "condition_turn": 10})
put(s, "turn-times.txt", "".join(f"turn {n}: x  utc {R.iso(at(sec))} - {R.iso(at(sec + 5))}  exit 0\n" for n, sec in ((9, 280), (10, 300))))
put(s, "org-files/retros.json", {"briefs": [{"id": "B1", "at": R.iso(at(320)), "since": R.iso(at(0)), "items": [{"n": 1, "kind": "answer", "key": "answer|R4"}]}]})
put(s, "p2/mcp-calls.json", [{"t": R.iso(at(320)), "tool": "retro", "result": "RETRO BRIEF B1 (since x)"}, {"t": R.iso(at(349)), "tool": "feedback", "result": "ok"}])
r = X.x2(s, x2_sig())
check("F27: retro 1 recorded before the third failing case's answer: X2 step 1 NOT DETERMINED, naming the retro call and the feedback call",
      r["verdict"] == "NOT DETERMINED" and "residual" in r["reason"] and R.iso(at(349)) in r["reason"])
# W
s = stream(tmp, "w")
prop = ("PLAN FOR YOU\n  acceptance:\n    1. Decisions and actions use the notes' own words.\n"
        "       from your words \"Use the words from the notes.\" (my question: \"Owners: initials or full names?\"); words I added: decisions, and, actions, own\n")
bp = {"needs": {"elicitation": "Use the words from the notes."}, "services": [{"acceptance": [{"text": "Decisions and actions use the notes' own words.", "from": "Use the words from the notes.", "asked": "Owners: initials or full names?"}]}]}
put(s, "p2/applies.json", [{"t": R.iso(at(10)), "ok": True, "blueprint": bp, "proposal": prop}])
check("W (0)-(c) PASS on a sourced plan whose PLAN FOR YOU shows the derived words under the criterion", X.w_check(s, {})["verdict"] == "PASS")
put(s, "p2/applies.json", [{"t": R.iso(at(10)), "ok": True, "blueprint": bp, "proposal": prop.replace("decisions, and, actions, own", "decisions, actions")}])
check("W (c): the source line's list differs from added_words: FAIL", X.w_check(s, {})["parts"]["(c)"]["verdict"] == "FAIL")
put(s, "p2/applies.json", [{"t": R.iso(at(10)), "ok": True, "blueprint": {"services": [{"acceptance": ["plain"]}]}, "proposal": prop}])
check("W (0) and (a): a string criterion with no words: FAIL", X.w_check(s, {})["parts"]["(0)"]["verdict"] == "FAIL" and X.w_check(s, {})["parts"]["(a)"]["verdict"] == "FAIL")
put(s, "p2/applies.json", [{"t": R.iso(at(10)), "ok": True, "blueprint": {"extend": {"add_services": [{"acceptance": [{"text": "x", "from_tasks": ["t1"]}]}]}}, "proposal": "x"}])
check("W (0): an extension whose only criteria are from_tasks copies needs no needs.elicitation (design 10.1 item 3)", X.w_check(s, {})["parts"]["(0)"]["verdict"] == "PASS")
put(s, "p2/applies.json", [{"t": R.iso(at(10)), "ok": True, "blueprint": dict(bp, needs={"elicitation": "other words"}), "proposal": prop}])
check("W (b): a quote not in the recorded words: FAIL", X.w_check(s, {})["parts"]["(b)"]["verdict"] == "FAIL")
put(s, "p2/applies.json", [])
check("W (0): no applied plan: FAIL (fail closed)", X.w_check(s, {})["parts"]["(0)"]["verdict"] == "FAIL")
put(s, "org-files/retros.json", {"briefs": [{"id": "B1", "at": R.iso(at(100)), "items": [{"key": "clarify|m|C4|x"}]}, {"id": "B2", "at": R.iso(at(200)), "items": [{"key": "clarify|m|C4|x"}]}]})
check("W (e): the clarify key offered twice: FAIL", X.w_check(s, {"clarify": [{"key": "clarify|m|C4|x", "fires": True, "fires_rule": True, "reached_at": R.iso(at(50))}]})["parts"]["(e)"]["verdict"] == "FAIL")
check("W (e): never due: VACUOUS", X.w_check(s, {"clarify": []})["parts"]["(e)"]["verdict"] == "VACUOUS")
# E and S fail closed
s = stream(tmp, "es")
check("E: no recorded brief fails closed", V(X.e_check(s)) == "NOT DETERMINED FC")
check("S: no recorded brief: NOT DETERMINED", X.s_check(s, {}, {})["verdict"] == "NOT DETERMINED")
check("S: an order or cap finding of the ledger re-derivation is a MISMATCH",
      X.s_check(stream(tmp, "s2"), {}, {"order": ["B1: x"]})["rows"][-1][1] == "MISMATCH")
put(s, "p2/retro-replies/B1.txt", "RETRO BRIEF B1\nRETRO BRIEF END\nDetails (for you; ...)\nWork you ask for again and again\n- lead: \"Action list\" and 2 more (20261029T000001000000-root-0001, 20261029T000002000000-root-0002, 20261029T000003000000-root-0003), joined by their titles: 3 of 3 with your verdict\n\n")
check("S T12: the product's D5 group read from the reply", X.product_d5_groups(s, {"id": "B1"}) == [["20261029T000001000000-root-0001", "20261029T000002000000-root-0002", "20261029T000003000000-root-0003"]])
# the end record
s = stream(tmp, "end", end=None)
check("the end: no end.txt is not known", not X.end_of(s)["known"])
put(s, "after-turn-12.out", "CAP: 140 org runs after turn 12 (cap 140, protocol 4.7): ...\n")
check("the end: a CAP line is a cut at its turn", X.end_of(s)["cut"] and X.end_of(s)["turn"] == 12)
shutil.rmtree(tmp, ignore_errors=True)

# ================================================================================================== the dry run's PF-0 timing verdict (freeze fix; manager ruling (b))
import pf0_timing as PT  # noqa: E402
SAME_OK = {"kind": "same", "classified": "PF-0 1 PF-1 0 new 0"}
EARLIER_OK = {"kind": "earlier", "classified": "PF-0 0 PF-1 0 new 0"}
OLD_RULE = lambda bs: "PASS" if {b["kind"] for b in bs} >= {"same", "earlier"} else "FAIL"  # noqa: E731  (dryrun.sh before the freeze fix)
check("PF-0 timing, all builds 'same second': the old rule reads FAIL", OLD_RULE([SAME_OK] * 8) == "FAIL")
check("PF-0 timing, all builds 'same second': PASS, the earlier second 'not reached', covered by named constructed cases",
      PT.decide([SAME_OK] * 8)[0] == "PASS" and "earlier second: not reached; covered by the constructed cases" in PT.decide([SAME_OK] * 8)[1])
check("PF-0 timing, a 'same second' build the classifier did not read as PF-0 (a misclassified build): FAIL",
      PT.decide([{"kind": "same", "classified": "PF-0 0 PF-1 0 new 1"}, EARLIER_OK])[0] == "FAIL")
check("PF-0 timing, an 'earlier second' build the classifier did not read as no difference: FAIL",
      PT.decide([SAME_OK, {"kind": "earlier", "classified": "PF-0 0 PF-1 0 new 1"}])[0] == "FAIL")
check("PF-0 timing, both timings built and classified: PASS, nothing 'not reached'", PT.decide([SAME_OK, EARLIER_OK])[0] == "PASS" and "not reached" not in PT.decide([SAME_OK, EARLIER_OK])[1])
check("PF-0 timing, only 'earlier second' builds: FAIL (no PF-0 reproduced)", PT.decide([EARLIER_OK] * 3)[0] == "FAIL")
check("PF-0 timing, no build at all (or only builds that were neither): FAIL, fail closed", PT.decide([])[0] == "FAIL" and PT.decide([{"kind": "other", "classified": ""}])[0] == "FAIL")
check("PF-0 timing, a misclassified build stands over a reproduced PF-0: FAIL", PT.decide([SAME_OK, {"kind": "same", "classified": "PF-0 2 PF-1 0 new 0"}])[0] == "FAIL")
PD = R.parse_product_d8(["- charter of lead/writer changed: body (2026-10-29): outside the tools (a hand edit or the terminal)"])
check("an 'earlier second' build: the product gives the design's label, the classifier finds no difference (the constructed case the timing verdict names)",
      X.classify_d8(PD, H0, EV_CLI) == [])
check("the timing verdict's named cases exist in this file", all(n in open(__file__).read() for n in PT.COVERED_BY))

out = Path(sys.argv[sys.argv.index("--out") + 1])
out.mkdir(parents=True, exist_ok=True)
lines = [f"{'ok' if v else 'MISMATCH'}  {n}" for n, v in checks] + [f"selfcheck_cases: {sum(v for _, v in checks)} of {len(checks)} ok"]
(out / "selfcheck_cases.out").write_text("\n".join(lines) + "\n")
print("\n".join(lines))
sys.exit(0 if all(v for _, v in checks) else 1)
