#!/usr/bin/env python3
"""P2 scorer for memos 1-6 and the action lists (protocol 4.2, 12.3, 12.4). Standard library + P1's score_memos.py (unchanged, imported).

    python3 -B score_p2.py <stream evidence dir> --out <dir>
    python3 -B score_p2.py --selfcheck --out <dir>                 constructed memos and lists

1. P1's `score_memos.py --memos 6` (E7's key for memos 1-3, P1's for memos 4-6, owner form N: P1's `owner_is` accepts the key's name, and
   for memo 5's A3 a cell naming `JD`) over a view of the stream in which every deliverable whose file name holds one YYYY-MM-DD is named
   `memo-<date>.md` (F-P1-9: the team names its files; two files of one date make that memo NOT DETERMINED);
2. **the trap rule** (protocol 4.2) per delivered version and final memo of memos 2-5: `fails` when the trap action (memo 2 A4, memo 3 A4,
   memo 4 A4, memo 5 A5) is not among the actions found or is among the wrong dates; else `passes`;
3. **the order in force**: memos 1-5 and memo 6 before A-M: the Summary line, then the decisions, then the action items; memo 6's versions
   after A-M's line: the Summary line, then the action items, then the decisions (`order_ok`, reported);
4. **delivered versions, P2's form** (12.3): wrong dates outside the trap row, and extra rows, per delivered version; every final memo's
   wrong dates including its trap row; a rejected or unjudged final, and an unjudged version, decided by the stream's end (C1);
5. **the action lists**: every deliverable that is not a memo of the key (the one-off lists and the week list): its table rows against the
   key's actions of the notes it names (its date), owner and Due; rows found, wrong Dues, extra rows (reported; Lena keeps every list).
Writes <out>/score_p2.json and score_p2.txt (and P1's score_memos.json/.txt in <out>/p1/).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import score_memos as SM  # noqa: E402  (P1's, unchanged)
import lena_lines as LL  # noqa: E402

TRAP = {"2026-10-12": "A4", "2026-10-19": "A4", "2026-10-26": "A4", "2026-11-02": "A5"}
AM_MEMO = "2026-11-09"
DATE = re.compile(r"(\d{4}-\d{2}-\d{2})")


def setup_p1_mode():
    SM.KEY = {**SM.KEY3, **SM.KEY_P1}
    SM.P1["on"] = True
    SM.P1["forms"] = [("", "N")]


def view_of(stream: Path, view: Path) -> dict:
    """The stream with its deliverables named memo-<date>.md (one per date); the others listed as lists or unknown."""
    view.mkdir(parents=True, exist_ok=True)
    for p in stream.iterdir():
        if p.name not in ("memos",) and not (view / p.name).exists():
            (view / p.name).symlink_to(p)
    (view / "memos").mkdir(exist_ok=True)
    by_date, others = {}, []
    for f in sorted((stream / "memos").glob("*")) if (stream / "memos").is_dir() else []:
        if f.is_dir():
            if f.name == "versions":
                (view / "memos" / "versions").symlink_to(f)
            continue
        ds = DATE.findall(f.name)
        text = f.read_text(errors="replace")
        is_memo = bool(re.search(r"(?im)^\s*#*\s*\**\s*decisions?\b", text))
        if len(ds) == 1 and is_memo:
            by_date.setdefault(ds[0], []).append(f)
        else:
            others.append(f)
    nd = {}
    for d, fs in by_date.items():
        if len(fs) == 1:
            (view / "memos" / f"memo-{d}.md").symlink_to(fs[0])
        else:
            nd[d] = [str(x) for x in fs]
    return {"memos": {d: str(fs[0]) for d, fs in by_date.items() if len(fs) == 1}, "not_determined": nd, "others": [str(x) for x in others]}


def actions_first(text: str) -> bool:
    lines = text.splitlines()
    d, a = SM._section_index(lines, "decision"), SM._section_index(lines, "action")
    return d is not None and a is not None and a < d


def trap_of(memo: str, scored: dict) -> str | None:
    aid = TRAP.get(memo)
    if not aid:
        return None
    if aid not in (scored.get("actions_found") or []):
        return "fails"
    if any(w.get("action") == aid for w in scored.get("wrong_dates") or []):
        return "fails"
    return "passes"


def score_list(text: str) -> dict:
    rows = []
    for ln in text.splitlines():
        if ln.lstrip().startswith("|"):
            cells = [SM.strip_marks(c) for c in SM.split_row(ln)]
            if cells and not all(SM._SEPARATOR_CELL.match(c) for c in cells if c) and not ({"owner", "due"} & {c.lower() for c in cells}):
                rows.append(cells)
    return {"rows": len(rows)}


def turn_of_time(stream: Path):
    """turn-times.txt: the user turn whose window (its start up to the next turn's start) holds a time."""
    from datetime import datetime, timezone
    starts = []
    f = stream / "turn-times.txt"
    for ln in f.read_text().splitlines() if f.is_file() else []:
        m = re.match(r"^turn (\d+): .*utc (\S+) - ", ln)
        if m:
            try:
                starts.append((int(m.group(1)), datetime.fromisoformat(m.group(2).replace("Z", "+00:00"))))
            except ValueError:
                pass

    def at(t):
        if not t:
            return None
        try:
            d = datetime.fromisoformat(str(t).replace("Z", "+00:00"))
        except ValueError:
            return None
        d = d if d.tzinfo else d.replace(tzinfo=timezone.utc)
        return max((n for n, s in starts if s <= d), default=None)
    return at


def last_verdict(lines: list[dict], memo: str) -> str | None:
    """Lena's verdict in the last line that judges `memo` (`lena_lines.verdict_after` over that line), or None when no line judges it."""
    ts = [x["turn"] for x in lines for r in x["rules"]
          if ("2026-10-05" if r == "H6" else LL.memo_of(r)) == memo and (r.split("@")[0] in LL.JUDGING or r == "H6")]
    return LL.verdict_after(lines, memo, max(ts) - 1) if ts else None


def delivered_check(versions: list[dict], finals: list[dict], lines: list[dict], end: dict | None = None) -> dict:
    """Protocol 12.3, "delivered versions with 0 wrong dates and 0 extra rows" in P2's form (F26 of review 2; the manager's decision
    `manager-decision-prereg-loop.md`, and its ruling C1 on F38 of review 3): every version delivered by copy has 0 wrong dates outside
    the trap row and 0 extra rows, EXCEPT a version Lena rejected (`lena` = `rejected`: the first later line judging its memo is H6,
    VR-REJECT, TRAP-1, TRAP-N or A-M); a version she accepted or took as it is keeps the rule. A final memo keeps the rule (0 extra rows,
    0 wrong dates, its trap row included unless the memo was accepted under L-ASIS) when the last Lena line that judged it is ACCEPT or
    L-ASIS. When that line is a rejection, or no line judged the memo, and for a version no line judged: in a cut stream (`end["cut"]`,
    `extract_p2.end_of`) it reads NOT DETERMINED (cut at turn <n>: ...); with the end unknown (no end.txt) NOT DETERMINED (FAIL-CLOSED:
    the stream's end is not recorded); in a `retro-2-done` stream, where this cannot happen by the script, it is held to the rule as
    written (FAIL when it breaks it). `end` None reads as an unknown end."""
    end = end or {"known": False, "cut": False, "turn": None, "reason": None}
    bad, exempt, nd = [], [], []

    def undecided(what: str) -> bool:  # True when the end cut (or did not record) the verdict this item needs
        if end.get("cut"):
            nd.append(f"{what}: cut at turn {end.get('turn')}: {end.get('reason')}")
            return True
        if not end.get("known"):
            nd.append(f"{what}: the stream's end is not recorded")
            return True
        return False
    for x in versions:
        if not x.get("copied"):
            continue
        if x.get("lena") == "rejected":
            exempt.append(f"{x['memo']} v{x.get('version')}")
            continue
        if x.get("lena") is None and undecided(f"{x['memo']} v{x.get('version')} (not judged)"):
            continue
        if x.get("wrong_dates_outside_trap") or x.get("extra_rows"):
            bad.append(f"{x['memo']} v{x.get('version')} ({x.get('lena') or 'not judged'}): wrong {len(x.get('wrong_dates_outside_trap') or [])}, extra {len(x.get('extra_rows') or [])}")
    asis = {LL.memo_of(r) for ln in lines for r in ln["rules"] if r.startswith("L-ASIS@")}
    for f in finals:
        if "error" in f:
            continue
        lv = last_verdict(lines, f["memo"])
        if lv not in ("accepted", "as-is") and undecided(f"final {f['memo']} ({lv or 'not judged'})"):
            continue
        wrong = [w for w in f.get("wrong_dates") or [] if w.get("action") != TRAP.get(f["memo"]) or f["memo"] not in asis]
        if wrong or f.get("extra_rows"):
            bad.append(f"final {f['memo']} ({lv or 'not judged'}): wrong {len(wrong)}, extra {len(f.get('extra_rows') or [])}")
    if bad:
        verdict = f"FAIL ({'; '.join(bad[:4])})"
    elif nd and end.get("cut"):
        verdict = f"NOT DETERMINED (cut at turn {end.get('turn')}: the memo's last version was rejected or not judged: {'; '.join(nd[:4])})"
    elif nd:
        verdict = f"NOT DETERMINED (FAIL-CLOSED: the stream's end is not recorded: {'; '.join(nd[:4])})"
    else:
        verdict = "PASS"
    return {"ok": not bad, "bad": bad, "exempt_rejected": exempt, "not_determined": nd, "verdict": verdict}


def score(stream: Path, out: Path, am_time: str | None = None) -> dict:
    setup_p1_mode()
    out.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=str(out)) as tv:
        view = Path(tv) / stream.name
        v = view_of(stream, view)
        p1 = SM.score_stream(view)
    (out / "p1").mkdir(exist_ok=True)
    SM.write_outputs(str(out / "p1"), "score_memos", p1, SM.render_txt(p1))
    ll = LL.parse(str(stream / "lena-lines.txt"))["lines"] if (stream / "lena-lines.txt").is_file() else []
    turn_at = turn_of_time(stream)
    versions = []
    for x in p1.get("versions") or []:
        if "error" in x:
            continue
        after_am = x["memo"] == AM_MEMO and am_time is not None and (x.get("commit_time") or "") > am_time
        versions.append({"memo": x["memo"], "version": x.get("version"), "sha": x.get("sha"), "copied": x.get("copied"),
                         "trap": trap_of(x["memo"], x),
                         "wrong_dates_outside_trap": [w for w in x.get("wrong_dates") or [] if w.get("action") != TRAP.get(x["memo"])],
                         "extra_rows": x.get("extra_rows") or [], "order": "actions first" if after_am else "decisions first",
                         "lena": LL.verdict_after(ll, x["memo"], turn_at(x.get("commit_time")))})
    finals = []
    for f in p1.get("finals") or []:
        if "error" in f:
            finals.append(f)
            continue
        finals.append({"memo": f["memo"], "file": f["file"], "trap": trap_of(f["memo"], f), "decisions": f["decisions"], "actions": f["actions"],
                       "wrong_dates": f["wrong_dates"], "extra_rows": f["extra_rows"], "summary_first": f["summary_first"]})
    lists = [{"file": p, **score_list(Path(p).read_text(errors="replace"))} for p in v["others"]]
    import extract_p2 as XP  # the stream's end (protocol 3.7, 12 Cuts), read by the one function the checks use (C1)
    end = XP.end_of(stream)
    dc = delivered_check(versions, finals, ll, end)
    delivered_ok = dc["ok"]
    res = {"view": v, "versions": versions, "finals": finals, "lists": lists,
           "p2_delivered_versions": {"ok": delivered_ok and bool(versions), "versions": len([x for x in versions if x["copied"]]),
                                     "bad": dc["bad"], "exempt_rejected": dc["exempt_rejected"],
                                     "not_determined": dc["not_determined"], "verdict": dc["verdict"], "end": end},
           "traps": {m: sorted({x["trap"] for x in versions if x["memo"] == m and x["copied"]}) for m in TRAP}}
    (out / "score_p2.json").write_text(json.dumps(res, indent=1, default=str))
    txt = [f"memo {m}: trap per delivered version {res['traps'][m]}" for m in TRAP]
    txt.append(f"delivered versions (P2's form): {'0 wrong dates outside the trap rows, 0 extra rows' if delivered_ok else 'NOT clean'} ({res['p2_delivered_versions']['versions']} copied versions); {dc['verdict']}")
    txt += [f"final {f['memo']}: trap {f.get('trap')} decisions {f.get('decisions')} actions {f.get('actions')} wrong {len(f.get('wrong_dates') or [])} extra {len(f.get('extra_rows') or [])}" for f in finals if "error" not in f]
    (out / "score_p2.txt").write_text("\n".join(txt) + "\n")
    return res


def selfcheck(out: Path) -> int:
    setup_p1_mode()
    ok = []
    good = ("# Memo 2026-10-26\n\nSummary: gateway cutover and rate limiter.\n\n## Decisions\n- Cut over to the new gateway on Wednesday 28 October.\n"
            "- Turn the rate limiter on for the large-plan customers first.\n- Widen the weekly Renovate batch to all repos in November.\n\n"
            "## Action items\n| Owner | Action | Due |\n|---|---|---|\n| Dev | Run the gateway cutover | 2026-10-28 |\n"
            "| Priya | Enable the rate limiter flag for the large-plan customers | 2026-10-30 |\n| Marta | Send the demo feedback summary to the product team | 2026-10-27 |\n"
            "| Sam | Write onboarding notes for the CI pipeline | 2026-10-30 |\n| Lee | Update the SSO runbook | none |\n")
    s = SM.score_memo(good, "2026-10-26")
    ok.append(("memo 4 right: trap passes", trap_of("2026-10-26", s) == "passes"))
    bad = good.replace("| Sam | Write onboarding notes for the CI pipeline | 2026-10-30 |", "| Sam | Write onboarding notes for the CI pipeline | none |")
    ok.append(("memo 4 Sam none: trap fails", trap_of("2026-10-26", SM.score_memo(bad, "2026-10-26")) == "fails"))
    gone = good.replace("| Sam | Write onboarding notes for the CI pipeline | 2026-10-30 |\n", "")
    ok.append(("memo 4 without Sam's row: trap fails", trap_of("2026-10-26", SM.score_memo(gone, "2026-10-26")) == "fails"))
    ok.append(("memo 1: no trap", trap_of("2026-10-05", SM.score_memo(good, "2026-10-26")) is None))
    am = good.replace("## Decisions", "## Action itemsX").replace("## Action items\n", "## Decisions\n").replace("## Action itemsX", "## Action items")
    ok.append(("actions-first layout read", actions_first(am) and not actions_first(good)))
    jd = SM.score_memo("Summary: x\n\n## Decisions\n- x\n\n## Action items\n| Owner | Action | Due |\n|---|---|---|\n| JD | Send the deck to the customer | 2026-11-05 |\n", "2026-11-02")
    ok.append(("memo 5: JD's row found under form N", "A3" in jd["actions_found"]))
    # F26 of review 2: rejected versions are exempt; accepted versions and final memos keep the rule
    LN = [LL.parse_line(x) for x in ("turn 4 | rules TRAP-1@2026-10-12 | table rows none | facts: x",
                                     "turn 6 | rules ACCEPT@2026-10-12 + ACT-REQ@2026-10-12 | table rows none | facts: x",
                                     "turn 9 | rules L-ASIS@2026-10-19 | table rows none | facts: x")]
    W1 = [{"action": "A1"}]
    rej = {"memo": "2026-10-12", "version": 1, "copied": True, "lena": LL.verdict_after(LN, "2026-10-12", 3), "wrong_dates_outside_trap": W1, "extra_rows": []}
    acc = {"memo": "2026-10-12", "version": 2, "copied": True, "lena": LL.verdict_after(LN, "2026-10-12", 5), "wrong_dates_outside_trap": W1, "extra_rows": []}
    fin = {"memo": "2026-10-12", "wrong_dates": [], "extra_rows": ["Marta keeps the agenda"]}
    fin_asis = {"memo": "2026-10-19", "wrong_dates": [{"action": "A4"}], "extra_rows": []}
    DONE = {"known": True, "cut": False, "turn": 40, "reason": "retro-2-done"}
    CUT = {"known": True, "cut": True, "turn": 14, "reason": "cap: 141 org runs"}
    NOEND = {"known": False, "cut": False, "turn": None, "reason": None}

    def dc(*a):  # the closing pass's cases call delivered_check with the stream's end (C1); an older signature reads as a mismatch
        try:
            return delivered_check(*a)
        except TypeError as e:
            return {"ok": None, "verdict": f"error: {e}", "not_determined": []}
    ok.append(("F26: a version Lena rejected with a wrong date outside the trap row is exempt", dc([rej], [], LN, DONE)["ok"] and rej["lena"] == "rejected"))
    ok.append(("F26: a version she accepted with a wrong date fails", dc([acc], [], LN, DONE)["ok"] is False and acc["lena"] == "accepted"))
    ok.append(("F26: a final memo with an extra row fails; a final memo's wrong trap row under L-ASIS does not (a retro-2-done stream)",
               dc([], [fin], LN, DONE)["ok"] is False and dc([], [fin_asis], LN, DONE)["ok"]
               and dc([], [dict(fin_asis, memo="2026-10-26", wrong_dates=[{"action": "A4"}])], LN, DONE)["ok"] is False))
    # C1 (F38 of review 3; the manager's ruling): a final memo keeps the rule only when the last Lena line that judged it is ACCEPT or
    # L-ASIS; a rejected or never-judged final, and a never-judged version, read NOT DETERMINED (cut) in a cut stream, NOT DETERMINED
    # (FAIL-CLOSED) with no end.txt, and are held to the rule as written in a retro-2-done stream
    LC = LN + [LL.parse_line("turn 12 | rules TRAP-N@2026-10-26 | table rows none | facts: trap: fails")]
    trapn_final = {"memo": "2026-10-26", "wrong_dates": [{"action": "A4"}], "extra_rows": []}
    r = dc([], [trapn_final], LC, CUT)
    ok.append(("C1: a cut stream whose memo-4 final is the TRAP-N-rejected version: NOT DETERMINED (cut), not FAIL",
               r["ok"] is True and str(r.get("verdict")).startswith("NOT DETERMINED (cut at turn 14: the memo's last version was rejected or not judged")
               and "FAIL-CLOSED" not in str(r.get("verdict"))))
    slip = {"memo": "2026-11-09", "version": 3, "copied": True, "lena": None, "wrong_dates_outside_trap": [{"action": "A2"}], "extra_rows": []}
    r = dc([slip], [], LC, CUT)
    ok.append(("C1: a cut stream whose last version was never judged and has a slip: NOT DETERMINED (cut), not FAIL",
               r["ok"] is True and str(r.get("verdict")).startswith("NOT DETERMINED (cut at turn 14") and "FAIL-CLOSED" not in str(r.get("verdict"))))
    r = dc([], [fin], LN, DONE)
    ok.append(("C1: a retro-2-done stream whose accepted final has an extra row: FAIL", r["ok"] is False and str(r.get("verdict")).startswith("FAIL")))
    r = dc([], [trapn_final], LC, NOEND)
    ok.append(("C1: the same TRAP-N-rejected final with no end.txt: NOT DETERMINED (FAIL-CLOSED: the stream's end is not recorded)",
               str(r.get("verdict")).startswith("NOT DETERMINED (FAIL-CLOSED: the stream's end is not recorded")))
    lines = [f"{'ok' if v else 'MISMATCH'}  {n}" for n, v in ok]
    lines.append(f"score_p2 selfcheck: {sum(bool(v) for _, v in ok)} of {len(ok)} ok")
    out.mkdir(parents=True, exist_ok=True)
    (out / "score_p2.out").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    return 0 if all(bool(v) for _, v in ok) else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("stream", nargs="?")
    ap.add_argument("--out", required=True)
    ap.add_argument("--am-time")
    ap.add_argument("--selfcheck", action="store_true")
    a = ap.parse_args()
    if a.selfcheck:
        return selfcheck(Path(a.out))
    r = score(Path(a.stream), Path(a.out), a.am_time)
    print(f"score_p2: {len(r['versions'])} versions, {len(r['finals'])} finals, {len(r['lists'])} lists; traps {r['traps']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
