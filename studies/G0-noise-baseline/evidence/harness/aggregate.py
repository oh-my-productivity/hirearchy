#!/usr/bin/env python3
"""G0 aggregate: baseline.md (design 20.5). Standard library only.

Usage:  python3 -B aggregate.py <G0 evidence dir> --out <path>/baseline.md [--streams m0-s1,m1-s1,...]

Reads per stream (<G0 evidence dir>/<label>/), tolerating any missing file (the cell then says `missing (...)`; no value is ever invented):
  arm.txt                                  the arm (else the label prefix m0/m1, else `e7`)
  measures/assistant_facts.json            layer B (mechanical facts; the stratum comes from here, else measures/skill_check.json)
  measures/score_memos.json, ambiguity_recall.json, prompt_sizes.json, playbook_attempts.json    layer A
  measures/judged.json                     the scorer's judged measures (keys of judged-template.json)
  measures/validity.json                   {"valid": bool, "reason": str} written by the scorer
  quality/end.json                         `hirearchy quality --json` after the last turn (layer C)
  rederived/mismatches.txt                 `compared <k> keys, <m> mismatches` of rederive_quality.py --compare (layer C)
The key paths of the other helpers' files are the REGISTRY below (file, dotted path); a path that is absent in a file is a missing cell.

Output: one table per layer (A team, B assistant, C product); rows = measures; columns = the streams grouped by arm (M0, M1) and skill stratum
(A, B, N, n/a), then per arm, per arm x stratum, per stratum and over all valid streams. Numeric values: min / median / max (median of an even
count = the mean of the two middle values); rates: pooled `k of n` (`n/a (0 of 0)` for a zero denominator); binary values: `k of n` streams;
categorical values: counts. A cell over fewer than 3 valid streams reports its values and `spread n/a (k of 3)` (design 20.1). Invalid streams
(validity.json) keep their own column, are listed under "Invalid streams" and are left out of every group cell."""
import glob
import hashlib
import json
import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True

HERE = Path(__file__).resolve().parent
MISSING = object()
STRATA = ["A", "B", "N", "n/a", "unknown"]


# ---------------------------------------------------------------- the maths
def median(xs):
    s = sorted(xs)
    n = len(s)
    return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2


def fmt(x):
    if isinstance(x, bool):
        return "yes" if x else "no"
    if isinstance(x, float):
        t = f"{x:.4f}".rstrip("0").rstrip(".")
        return t if t not in ("", "-0") else "0"
    return str(x)


def spread_num(xs):
    return f"{fmt(min(xs))} / {fmt(median(xs))} / {fmt(max(xs))}"


def show_rate(r):
    return "n/a (0 of 0)" if r["n"] == 0 else f"{r['k']} of {r['n']}"


def pool_rates(rs):
    return {"k": sum(r["k"] for r in rs), "n": sum(r["n"] for r in rs)}


def one(kind, v):
    """A single stream's value as table text."""
    if kind == "rate":
        return show_rate(v)
    if kind == "bin":
        return "yes" if v else "no"
    if kind == "num":
        return fmt(v)
    return str(v)


def cell(kind, values, missing=0):
    """A group cell over `values` (one per valid stream with a value) and `missing` valid streams with none."""
    k = len(values)
    if k == 0:
        base = "n/a (0 of 0)" if not missing else f"missing (all {missing} stream{'s' if missing != 1 else ''})"
        return base
    elif k < 3:
        base = "; ".join(one(kind, v) for v in values) + f"; spread n/a ({k} of 3)"
    elif kind == "num":
        base = spread_num(values)
    elif kind == "rate":
        base = show_rate(pool_rates(values))
    elif kind == "bin":
        base = f"{sum(1 for v in values if v)} of {k}"
    else:  # cat
        counts = {}
        for v in values:
            counts[v] = counts.get(v, 0) + 1
        base = ", ".join(f"{a} {b}" for a, b in sorted(counts.items()))
    return base + (f" ({missing} missing)" if missing else "")


# ---------------------------------------------------------------- the streams
class Stream:
    def __init__(self, d):
        self.dir = Path(d)
        self.label = self.dir.name
        self._docs = {}
        arm = ""
        f = self.dir / "arm.txt"
        if f.exists():
            arm = f.read_text().split()[0] if f.read_text().split() else ""
        if not arm:
            m = re.match(r"(m[01])-", self.label)
            arm = m.group(1) if m else "e7"
        self.arm = arm
        v = self.doc("measures/validity.json")
        self.valid, self.why = True, ""
        self.validity_recorded = isinstance(v, dict)
        if isinstance(v, dict):
            self.valid = bool(v.get("valid", True))
            self.why = str(v.get("reason", ""))
        self.stratum = "unknown"
        af = self.doc("measures/assistant_facts.json")
        sk = self.doc("measures/skill_check.json")
        for src, path in ((af, "measures.skill_stratum"), (sk, "stratum")):
            val = get(src, path) if isinstance(src, dict) else MISSING
            if isinstance(val, str):
                self.stratum = val
                break

    def doc(self, rel):
        """The parsed JSON of a file of the stream: a dict/list, or a reason string (`no rel` / `unreadable rel`)."""
        if rel not in self._docs:
            p = self.dir / rel
            if not p.exists():
                self._docs[rel] = f"no {rel}"
            else:
                try:
                    self._docs[rel] = json.loads(p.read_text())
                except ValueError:
                    self._docs[rel] = f"unreadable {rel}"
        return self._docs[rel]

    def text(self, rel):
        p = self.dir / rel
        return p.read_text() if p.exists() else None


def get(doc, path):
    cur = doc
    for part in path.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        elif isinstance(cur, list) and part.isdigit() and int(part) < len(cur):
            cur = cur[int(part)]
        else:
            return MISSING
    return cur


def arm_name(a):
    return a.upper()


# ---------------------------------------------------------------- the registry: (layer, label, kind, extractor)
def from_doc(rel, path):
    def f(s):
        d = s.doc(rel)
        if isinstance(d, str):
            return ("missing", d)
        v = get(d, path)
        return ("missing", f"no {path} in {rel}") if v is MISSING else v
    return f


def quality_services(s):
    d = s.doc("quality/end.json")
    if isinstance(d, str):
        return None, d
    return (d.get("services") or []), None


def quality_val(fn):
    def f(s):
        sv, why = quality_services(s)
        if why:
            return ("missing", why)
        return fn(sv)
    return f


def _sum_cases(key):
    return lambda sv: sum((c.get(key) or 0) for r in sv for c in r.get("cases", []))


def _sum_dict(section, key):
    return lambda sv: sum((r.get(section) or {}).get(key, 0) or 0 for r in sv)


def _sum_len(section, key):
    return lambda sv: sum(len((r.get(section) or {}).get(key, []) or []) for r in sv)


def _fires(alarm):
    return lambda sv: any(((r.get("alarms") or {}).get(alarm) or {}).get("state") == "fires" for r in sv)


def _timeline(kind):
    return lambda sv: sum(1 for r in sv for m in r.get("timeline", []) if m.get("kind") == kind)


def rederive(which):
    def f(s):
        t = s.text("rederived/mismatches.txt")
        if t is None:
            return ("missing", "no rederived/mismatches.txt")
        m = re.search(r"compared (\d+) keys, (\d+) mismatches", t)
        if not m:
            return ("missing", "unreadable rederived/mismatches.txt")
        return int(m.group(1 if which == "compared" else 2))
    return f


AF = "measures/assistant_facts.json"
SM = "measures/score_memos.json"
REGISTRY = [
    # ---- A. the team
    ("A", "Final memos: decisions in substance (answer key)", "rate", from_doc(SM, "final_totals.decisions")),
    ("A", "Final memos: action items (right owner and substance)", "rate", from_doc(SM, "final_totals.actions")),
    ("A", "Final memos: wrong dates", "num", from_doc(SM, "final_totals.wrong_dates")),
    ("A", "Final memos: extra rows", "num", from_doc(SM, "final_totals.extra_rows")),
    ("A", "Final memos: Summary first and decisions before actions", "rate", from_doc(SM, "final_totals.summary")),
    ("A", "Versions delivered (copied), of all committed versions", "rate", from_doc(SM, "delivered")),
    ("A", "Reviewer ambiguity recall (D21)", "rate", from_doc("measures/ambiguity_recall.json", "recall")),
    ("A", "Lead prompt bytes, first", "num", from_doc("measures/prompt_sizes.json", "bytes.first")),
    ("A", "Lead prompt bytes, max", "num", from_doc("measures/prompt_sizes.json", "bytes.max")),
    ("A", "Lead prompt bytes, last", "num", from_doc("measures/prompt_sizes.json", "bytes.last")),
    ("A", "Lead prompt bytes, last minus first", "num", from_doc("measures/prompt_sizes.json", "bytes.last_minus_first")),
    ("A", "Reflect section words, max", "num", from_doc("measures/prompt_sizes.json", "reflect_words.max")),
    ("A", "Reflect section words, min", "num", from_doc("measures/prompt_sizes.json", "reflect_words.min")),
    ("A", "revise_playbook attempts", "num", from_doc("measures/playbook_attempts.json", "counts.attempts")),
    ("A", "revise_playbook attempts refused", "num", from_doc("measures/playbook_attempts.json", "counts.refused")),
    ("A", "revise_playbook attempts admitted", "num", from_doc("measures/playbook_attempts.json", "counts.admitted")),
    ("A", "revise_playbook attempts in the injection window", "num", from_doc("measures/playbook_attempts.json", "counts.in_window")),
    ("A", "Org runs outside the injection window", "num", from_doc(AF, "measures.org_runs_outside")),
    ("A", "Org runs in the injection window", "num", from_doc(AF, "measures.org_runs_window")),
    ("A", "Org-run credits outside the window", "num", from_doc(AF, "measures.org_credits_outside")),
    ("A", "Org-run seconds outside the window", "num", from_doc(AF, "measures.org_seconds_outside")),
    # ---- B. the assistant
    ("B", "Skill stratum (4.4.1)", "cat", from_doc(AF, "measures.skill_stratum")),
    ("B", "User turns", "num", from_doc(AF, "measures.user_turns")),
    ("B", "Wall time, seconds", "num", from_doc(AF, "measures.wall_seconds")),
    ("B", "Assistant credits", "num", from_doc(AF, "measures.assistant_credits")),
    ("B", "Assistant seconds", "num", from_doc(AF, "measures.assistant_seconds")),
    ("B", "Memo 1: user turns from request to accept", "num", from_doc(AF, "measures.memo1_turns")),
    ("B", "Memo 2: user turns from request to accept", "num", from_doc(AF, "measures.memo2_turns")),
    ("B", "Memo 3: user turns from request to accept", "num", from_doc(AF, "measures.memo3_turns")),
    ("B", "Human rejects recorded", "num", from_doc(AF, "measures.human_rejects")),
    ("B", "Human rejections recorded without root's reading (M-D23-1)", "rate", from_doc(AF, "measures.d23_without_reading")),
    ("B", "D1 rejects never recorded with feedback", "rate", from_doc(AF, "measures.d1_never_recorded")),
    ("B", "`about` differing from the rejection's reading (M-D23-3)", "rate", from_doc(AF, "measures.d23_about_differs")),
    ("B", "Flagged results (a block with items)", "num", from_doc(AF, "measures.flagged_results")),
    ("B", "Flagged items (all)", "num", from_doc(AF, "measures.flagged_items")),
    ("B", "Flagged questions (name a criterion id)", "num", from_doc(AF, "measures.flagged_questions")),
    ("B", "Notes for the client (name no id)", "num", from_doc(AF, "measures.flagged_notes")),
    ("B", "Flagged questions superseded by a human rework", "num", from_doc(AF, "measures.flagged_superseded")),
    ("B", "Flagged questions never copied", "num", from_doc(AF, "measures.flagged_never_copied")),
    ("B", "Flagged questions needing the D5 judgement", "num", from_doc(AF, "measures.flagged_needs_d5")),
    ("B", "Relayed reworks the assistant sent", "num", from_doc(AF, "measures.relayed_reworks_by_assistant")),
    ("B", "Copies into the deliverable folder (D6)", "num", from_doc(AF, "measures.copies")),
    ("B", "Copies that were hand edits", "rate", from_doc(AF, "measures.hand_edits")),
    ("B", "Copies made while `artifacts withheld (ask first)` showed", "rate", from_doc(AF, "measures.ask_first_copies")),
    ("B", "Delivered versions without a human-tier verdict", "rate", from_doc(AF, "measures.delivered_without_verdict")),
    ("B", "Shell commands (execute_bash)", "num", from_doc(AF, "measures.shell_commands")),
    ("B", "inbox calls", "num", from_doc(AF, "measures.inbox_calls")),
    ("B", "Shell reads of message files", "num", from_doc(AF, "measures.shell_reads")),
    ("B", "Root's unread results and notes at the end", "num", from_doc(AF, "measures.root_unread_at_end")),
    ("B", "P2 refusals", "num", from_doc(AF, "measures.p2_refusals")),
    ("B", "P2-UNRATED refusals", "num", from_doc(AF, "measures.p2_unrated")),
    ("B", "P4 refusals", "num", from_doc(AF, "measures.p4_refusals")),
    ("B", "FACADE refusals", "num", from_doc(AF, "measures.facade_refusals")),
    ("B", "Other refusals", "num", from_doc(AF, "measures.other_refusals")),
    ("B", "Plans shown (propose_org)", "num", from_doc(AF, "measures.plans")),
    ("B", "Plans whose result carried the budget question line", "rate", from_doc(AF, "measures.plans_with_budget_line")),
    ("B", "Turns that showed the budget question verbatim", "num", from_doc(AF, "measures.turns_showing_budget_line")),
    ("B", "Lena's answers: yes to a raised budget (H4)", "num", from_doc(AF, "measures.lena_yes_h4")),
    ("B", "Lena's answers: keep (L-BUDGET-Q)", "num", from_doc(AF, "measures.lena_keep_l_budget_q")),
    ("B", "HELD replies", "num", from_doc(AF, "measures.held_replies")),
    ("B", "TOPUP replies", "num", from_doc(AF, "measures.topup_replies")),
    ("B", "send(budget=N) grants", "num", from_doc(AF, "measures.grants")),
    ("B", "Human reworks", "num", from_doc(AF, "measures.human_reworks")),
    ("B", "Human reworks without a budget", "num", from_doc(AF, "measures.human_reworks_without_budget")),
    ("B", "L-ASIS uses", "num", from_doc(AF, "measures.lasis_uses")),
    ("B", "L-ASIS uses followed by an accept before the next turn", "rate", from_doc(AF, "measures.lasis_accepted")),
    ("B", "Deliverable notes the assistant received", "num", from_doc(AF, "measures.deliverable_notes")),
    ("B", "Schedulers", "num", from_doc(AF, "measures.schedulers_total")),
    ("B", "Schedulers started by the assistant", "num", from_doc(AF, "measures.schedulers_assistant")),
    ("B", "Schedulers running at the end of a turn", "rate", from_doc(AF, "measures.schedulers_running_at_turn_end")),
    ("B", "(Turn end, scheduler) pairs that survived", "rate", from_doc(AF, "measures.survival_pairs")),
    ("B", "Schedulers with a scheduler.exit by the end", "rate", from_doc(AF, "measures.schedulers_with_exit")),
    ("B", "scheduler.signal lines", "num", from_doc(AF, "measures.scheduler_signals")),
    ("B", "Unexplained scheduler.signal lines", "rate", from_doc(AF, "measures.unexplained_signals")),
    ("B", "run.orphan events", "num", from_doc(AF, "measures.run_orphan")),
    ("B", "Runs killed (run.end killed)", "num", from_doc(AF, "measures.run_end_killed")),
    ("B", "Turns whose sleep ended at least 20 s after the chat (M-C-8)", "rate", from_doc(AF, "measures.m_c_8")),
    # ---- C. the product (quality --json and its re-derivation)
    ("C", "Cases", "num", quality_val(lambda sv: sum(len(r.get("cases", [])) for r in sv))),
    ("C", "Case runs (sum)", "num", quality_val(_sum_cases("runs"))),
    ("C", "User runs (sum of user_cost)", "num", quality_val(_sum_cases("user_cost"))),
    ("C", "Relayed runs (sum)", "num", quality_val(_sum_cases("relayed_runs"))),
    ("C", "Credited runs (sum)", "num", quality_val(_sum_cases("credited"))),
    ("C", "First deliveries accepted", "num", quality_val(_sum_dict("first_deliveries", "accepted"))),
    ("C", "First deliveries rejected", "num", quality_val(_sum_dict("first_deliveries", "rejected"))),
    ("C", "First deliveries with no verdict", "num", quality_val(_sum_dict("first_deliveries", "no_verdict"))),
    ("C", "First deliveries superseded", "num", quality_val(_sum_dict("first_deliveries", "superseded"))),
    ("C", "Deliveries, total", "num", quality_val(_sum_dict("deliveries", "total"))),
    ("C", "Deliveries judged by the user", "num", quality_val(_sum_dict("deliveries", "judged"))),
    ("C", "Cases with an unseen relayed delivery", "num", quality_val(_sum_len("deliveries", "unseen_relayed"))),
    ("C", "Files not as delivered", "num", quality_val(_sum_len("deliveries", "not_as_delivered"))),
    ("C", "Escapes, total", "num", quality_val(lambda sv: sum(len(r.get("escapes", [])) for r in sv))),
    ("C", "Verifiers", "num", quality_val(lambda sv: sum(len(r.get("verifiers", [])) for r in sv))),
    ("C", "Repeat alarm fires", "bin", quality_val(_fires("repeat"))),
    ("C", "Cost alarm fires", "bin", quality_val(_fires("cost"))),
    ("C", "Timeline marks: contract", "num", quality_val(_timeline("contract"))),
    ("C", "Timeline marks: playbook", "num", quality_val(_timeline("playbook"))),
    ("C", "Timeline marks: top-up", "num", quality_val(_timeline("top-up"))),
    ("C", "Moved-past blocks (agents with held tasks)", "num", lambda s: moved_past(s)),
    ("C", "Re-derivation keys compared", "num", rederive("compared")),
    ("C", "Re-derivation mismatches", "num", rederive("mismatches")),
]


def judged_registry():
    tpl = json.loads((HERE / "judged-template.json").read_text())
    kinds = {"rate": "rate", "binary": "bin", "count": "num", "number": "num", "enum": "cat", "text": "text"}
    out = []
    for t in tpl["measures"]:
        key = t["key"]

        def f(s, key=key):
            d = s.doc("measures/judged.json")
            if isinstance(d, str):
                return ("missing", d)
            return d[key] if key in d and d[key] is not None else ("missing", "not yet judged")
        out.append((t["layer"], t["label"], kinds[t["type"]], f))
    return out


def moved_past(s):
    d = s.doc("quality/end.json")
    if isinstance(d, str):
        return ("missing", d)
    return len(d.get("moved_past") or [])


def cause_rows(streams):
    """One row per escape cause seen in any stream's quality/end.json."""
    causes = set()
    for s in streams:
        d = s.doc("quality/end.json")
        if isinstance(d, dict):
            for r in d.get("services", []):
                for e in r.get("escapes", []):
                    causes.add(e.get("cause", ""))
    rows = []
    for c in sorted(causes):
        def f(s, c=c):
            sv, why = quality_services(s)
            return ("missing", why) if why else sum(1 for r in sv for e in r.get("escapes", []) if e.get("cause") == c)
        rows.append(("C", f"Escapes: {c}", "num", f))
    return rows


# ---------------------------------------------------------------- the report
def discover(root, streams=None):
    root = Path(root)
    if streams:
        return [Stream(root / s) for s in streams]
    found = sorted(p for p in root.iterdir() if p.is_dir() and re.fullmatch(r"m[01]-s\d+(r\d*)?", p.name))
    return [Stream(p) for p in found]


def order_key(s):
    arm_rank = {"m0": 0, "m1": 1}.get(s.arm, 2)
    return (arm_rank, s.arm, STRATA.index(s.stratum) if s.stratum in STRATA else len(STRATA), s.label)


def value_of(row, s):
    layer, label, kind, f = row
    try:
        v = f(s)
    except Exception as e:  # noqa: BLE001
        return ("missing", f"error {type(e).__name__}")
    return v


def is_missing(v):
    return isinstance(v, tuple) and len(v) == 2 and v[0] == "missing"


def build(root, streams=None):
    ss = sorted(discover(root, streams), key=order_key)
    rows = list(REGISTRY)
    rows_c_index = max(i for i, r in enumerate(rows) if r[0] == "C" and r[1].startswith("Escapes, total"))
    rows[rows_c_index + 1:rows_c_index + 1] = cause_rows(ss)
    rows += judged_registry()
    return ss, rows


def groups_of(ss):
    """Ordered [(name, [streams])] of the non-empty group columns, valid streams only."""
    valid = [s for s in ss if s.valid]
    gs = []
    arms = sorted({s.arm for s in valid}, key=lambda a: ({"m0": 0, "m1": 1}.get(a, 2), a))
    for a in arms:
        gs.append((arm_name(a), [s for s in valid if s.arm == a]))
    for a in arms:
        for st in STRATA:
            sel = [s for s in valid if s.arm == a and s.stratum == st]
            if sel:
                gs.append((f"{arm_name(a)} x {st}", sel))
    for st in STRATA:
        sel = [s for s in valid if s.stratum == st]
        if sel:
            gs.append((st, sel))
    if valid:
        gs.append(("all valid", valid))
    return gs


def render(root, streams=None):
    ss, rows = build(root, streams)
    gs = groups_of(ss)
    L = ["# G0 baseline (noise baseline of Phase 0b)", "",
         f"Generated by aggregate.py from `{Path(root)}`. Streams: " + (", ".join(f"{s.label} ({arm_name(s.arm)}/{s.stratum}{'' if s.valid else ', invalid'})" for s in ss) or "none") + ".", ""]
    L += ["Reading the tables. Rows are measures; columns are the streams (grouped by arm, then skill stratum), then the group cells over VALID streams only.",
          "A numeric cell over 3 or more streams is `min / median / max` (the median of an even count is the mean of the two middle values); a rate is the pooled "
          "`k of n` (`n/a (0 of 0)` when the pooled denominator is 0); a yes/no value is `k of n` streams; a category is a count per value. A cell over fewer than 3 "
          "valid streams lists its values and says `spread n/a (k of 3)` (design 20.1). `missing (...)` means the stream has no such value (its file is absent or "
          "does not hold the key): it is never replaced by a number, and a group cell says how many streams were missing. No test of significance is made (design 20.5).", ""]
    layers = [("A", "A. Team layer"), ("B", "B. Assistant layer"), ("C", "C. Product layer")]
    for lk, title in layers:
        L += [f"## {title}", ""]
        head = ["Measure"] + [f"{s.label} ({arm_name(s.arm)}/{s.stratum}{', invalid' if not s.valid else ''})" for s in ss] + [g for g, _ in gs]
        L.append("| " + " | ".join(head) + " |")
        L.append("|" + "|".join("---" for _ in head) + "|")
        for row in [r for r in rows if r[0] == lk]:
            layer, label, kind, f = row
            vals = {s.label: value_of(row, s) for s in ss}
            cells = [label]
            for s in ss:
                v = vals[s.label]
                cells.append(f"missing ({v[1]})" if is_missing(v) else ("-" if kind == "text" else one(kind, v)))
            for g, members in gs:
                if kind == "text":
                    cells.append("-")
                    continue
                got = [vals[s.label] for s in members if not is_missing(vals[s.label])]
                miss = sum(1 for s in members if is_missing(vals[s.label]))
                cells.append(cell(kind, got, miss))
            L.append("| " + " | ".join(c.replace("|", "\\|") for c in cells) + " |")
        L.append("")
    inval = [s for s in ss if not s.valid]
    L += ["## Invalid streams", ""]
    L += [f"- {s.label} ({arm_name(s.arm)}): {s.why or 'no reason recorded'}" for s in inval] or ["none"]
    L.append("")
    unrec = [s.label for s in ss if not s.validity_recorded]
    if unrec:
        L += ["Validity not recorded (`measures/validity.json` missing; counted as valid until the scorer writes it): " + ", ".join(unrec), ""]
    return "\n".join(L) + "\n", ss


def main(argv):
    args = list(argv)
    out = streams = None
    for flag in ("--out", "--streams"):
        if flag in args:
            i = args.index(flag)
            val = args[i + 1]
            del args[i:i + 2]
            if flag == "--out":
                out = val
            else:
                streams = [x for x in val.split(",") if x]
    if len(args) != 1 or out is None:
        print(__doc__)
        return 2
    root = Path(args[0])
    if not root.is_dir():
        print(f"not a directory: {root}", file=sys.stderr)
        return 2
    md, ss = render(root, streams)
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Path(out).write_text(md)
    print(f"baseline.md written: {len(ss)} streams, {sum(1 for s in ss if s.valid)} valid; script md5 {hashlib.md5(Path(__file__).read_bytes()).hexdigest()}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
