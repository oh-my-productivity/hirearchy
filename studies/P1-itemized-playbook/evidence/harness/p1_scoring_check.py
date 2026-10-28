#!/usr/bin/env python3
"""P1 self-check part: score_memos.py's P1 mode (memos 4-6 and the owner forms, protocol 12.3) on constructed memos.

Each constructed memo is the key itself written as a memo (a Summary line, every key decision, every key action with the key's Due, the
Owner cell in the form the case says), so the expected score is fixed by the key: all decisions and actions found, 0 wrong dates, 0 extra
rows, 0 owner-form errors; then the negative cases (full names under the initials rule; JD without the marker; a wrong Due; an extra row).
It also checks the private keys against the frozen tables (`key_check`: owners and Dues per meeting) without printing them.

    python3 -B p1_scoring_check.py [--out DIR]   ->  `p1_scoring_check: <ok> of <n> OK`
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import score_memos as sm  # noqa: E402

sm.KEY = {**sm.KEY3, **sm.KEY_P1}
sm.P1["on"] = True


def alt(groups):
    return " ".join(g[0].lstrip("=") for g in groups)


def owner_cell(owner, form):
    if owner == "JD":
        return "JD (full name not in the notes)" if form == "N+J" else "JD"
    return owner[0] if form == "I" else owner


def memo(meeting, form, wrong_due=False, extra=False):
    k = sm.KEY[meeting]
    lines = [f"# Memo {meeting}", "", "Summary: the meeting in one line.", "", "## Decisions"]
    lines += [f"- {alt(d['all'])}" for d in k["decisions"]]
    lines += ["", "## Action items", "", "| Owner | Action | Due |", "|---|---|---|"]
    for i, a in enumerate(k["actions"]):
        due = "2026-01-01" if (wrong_due and i == 0) else a["due"]
        lines.append(f"| {owner_cell(a['owner'], form)} | {alt(a['all'])} | {due} |")
    if extra:
        lines.append("| Dev | something that is no action item | none |")
    return "\n".join(lines) + "\n"


def main(argv):
    checks = []
    for mt in sm.KEY:
        for form in (("N+J",) if mt == "2026-11-02" else ("N", "I")):  # memo 5 under N has no right form (the key)
            r = sm.score_memo(memo(mt, form), mt, form)
            got = (r["decisions"]["k"] == r["decisions"]["n"], r["actions"]["k"] == r["actions"]["n"], len(r["wrong_dates"]),
                   len(r["extra_rows"]), len(r["owner_form_errors"]), r["summary_first"], r["decisions_before_actions"])
            checks.append((f"{mt} form {form}: the key as a memo scores perfect", got, (True, True, 0, 0, 0, True, True)))
    r = sm.score_memo(memo("2026-10-19", "N"), "2026-10-19", "I")
    checks.append(("memo 3 with full names under the initials rule: 5 owner-form errors, 5/5 actions",
                   (len(r["owner_form_errors"]), r["actions"]["k"]), (5, 5)))
    r = sm.score_memo(memo("2026-11-02", "N"), "2026-11-02", "N+J")
    checks.append(("memo 5 with 'JD' only after Lena's memo-5 line: 1 owner-form error", len(r["owner_form_errors"]), 1))
    r = sm.score_memo(memo("2026-11-02", "N+J"), "2026-11-02", "N")
    checks.append(("memo 5 under N (before her line): JD's row has no right form (the contract gap)", len(r["owner_form_errors"]), 1))
    r = sm.score_memo(memo("2026-11-09", "N", wrong_due=True, extra=True), "2026-11-09", "N")
    checks.append(("memo 6 with a wrong Due and an extra row", (len(r["wrong_dates"]), len(r["extra_rows"])), (1, 1)))
    # no regression (protocol 12.3, iteration 3, the manager's M7 decision): only G0's gate-able measures decide; the Summary and order
    # and the owner form are reported
    forms = {"2026-10-05": "N", "2026-10-12": "I", "2026-10-19": "I", "2026-10-26": "N", "2026-11-02": "N+J", "2026-11-09": "N+J"}

    def finals(**bad):
        out = []
        for mt, form in forms.items():
            text = memo(mt, forms[mt] if mt not in bad.get("form_of", {}) else bad["form_of"][mt], wrong_due=mt == bad.get("wrong_due"))
            if mt == bad.get("no_summary"):
                text = text.replace("Summary: the meeting in one line.\n", "")
            r = sm.score_memo(text, mt, form)
            out.append({**r, "memo": mt, "file": f"memos/memo-{mt}.md"})
        return [x for x in out if x["memo"] != bad.get("missing")]
    nr = sm.p1_no_regression([], finals())
    checks.append(("no regression: the keys as final memos pass, nothing reported", (nr["mechanical_pass"], nr["reported_ok"]), (True, True)))
    nr = sm.p1_no_regression([], finals(no_summary="2026-10-05", form_of={"2026-10-12": "N"}))
    checks.append(("no regression: memo 1 kept without a Summary (L-ASIS) and memo 2 with full names under I: reported, not a FAIL",
                   (nr["mechanical_pass"], nr["reported_ok"], nr["reported"]["2026-10-05"]["why"],
                    nr["reported"]["2026-10-12"]["why"].endswith("owner-form errors")),
                   (True, False, "Summary first / order", True)))
    nr = sm.p1_no_regression([], finals(wrong_due="2026-11-09"))
    checks.append(("no regression: a wrong Due in the final memo 6 fails", (nr["mechanical_pass"], nr["per_memo"]["2026-11-09"]["why"]),
                   (False, "1 wrong dates")))
    nr = sm.p1_no_regression([{"memo": "2026-10-12", "version": 1, "sha": "abc1234", "copied": True, "wrong_dates": [{}], "extra_rows": []}],
                             finals())
    checks.append(("no regression: one delivered version with a wrong date fails the stream (21.1 item 3)",
                   (nr["mechanical_pass"], len(nr["delivered_bad"])), (False, 1)))
    nr = sm.p1_no_regression([], finals(missing="2026-11-09"))
    checks.append(("no regression: memo 6 never delivered fails (E7 10.4)", (nr["mechanical_pass"], nr["per_memo"]["2026-11-09"]["final"]),
                   (False, None)))
    kc = sm.key_check(sm.DEFAULT_ANSWER_KEY_P1)
    checks.append(("answer-key-p1.md matches the frozen tables of memos 4-6 (owners, Dues, counts)", kc.get("ok"), True))
    kc3 = sm.key_check(sm.DEFAULT_ANSWER_KEY)
    checks.append(("answer-key.md (E7's) matches the frozen tables of memos 1-3", kc3.get("ok"), True))
    ok = 0
    lines = []
    for name, got, want in checks:
        good = got == want
        ok += good
        lines.append(f"{'OK  ' if good else 'FAIL'} {name}: got {got!r}" + ("" if good else f", want {want!r}"))
    lines.append(f"p1_scoring_check: {ok} of {len(checks)} OK")
    text = "\n".join(lines)
    print(text)
    if "--out" in argv:
        out = Path(argv[argv.index("--out") + 1])
        out.mkdir(parents=True, exist_ok=True)
        (out / "p1_scoring_check.out").write_text(text + "\n")
    return 0 if ok == len(checks) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
