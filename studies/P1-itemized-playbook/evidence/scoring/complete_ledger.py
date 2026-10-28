#!/usr/bin/env python3
"""The scorer's completion of each stream's D14 ledger (protocol 6.3, 13.2), written to scoring/<label>/measures/spend-ledger.json.

    python3 -B complete_ledger.py <EV> <label> [...]

The stream step's ledger (<label>/measures/spend-ledger.json: memo, lena_plan_budget, lena_grants) is copied unchanged and each entry gets the
case facts read from the raw files, each with its file in `_files`:
  * state: the head task's final line in final-services-progress-status-health.txt (`progress`), the case's latest task's state;
  * runs, relayed_runs, budget: the `case total: N runs used[: U by the user's requests, R by your relayed rework ...]; H handed down` clause
    of the final `progress` (protocol 6.3: "Used runs = the case's 'case total: N runs used' in the final progress, less the injected task's
    runs for memo 1");
  * d14_used = runs - relayed_runs (6.3);
  * contract_budget: the head task's `budget` header (msgs/sent/<head>.md), which is the contract's per-request budget;
  * ceilings: NOT derived by hand in this step (the approval's ceiling needs the runs used before each hand-down; a declared limit of the
    scoring, STUDY.md). rederive_watch.py --spend is therefore run with --stream (completeness) and without --quality (no comparison of the
    approval with the product's), and the product's figures are tabulated beside the ledger instead.
The stream step's own ledger file is not edited."""
import json
import re
import sys
from pathlib import Path

EV = Path(sys.argv[1]).resolve()


def case_tasks(D: Path, head: str) -> list:
    """The case's tasks from root's sent mail: the head and every task whose `revises` chain reaches it."""
    rev = {}
    for f in (D / "msgs" / "sent").glob("*.md"):
        t = f.read_text(errors="replace")
        if re.search(r"^type:\s*task\s*$", t, re.M):
            r = re.search(r"^revises:\s*(\S+)", t, re.M)
            rev[f.stem] = r.group(1) if r else None
    out = []
    for tid in rev:
        x, seen = tid, set()
        while x and x not in seen:
            if x == head:
                out.append(tid)
                break
            seen.add(x)
            x = rev.get(x)
    return sorted(out)


def progress_lines(D: Path) -> dict:
    out = {}
    t = (D / "final-services-progress-status-health.txt").read_text(errors="replace")
    for ln in t.splitlines():
        m = re.search(r"\(task (\d{8}T\d{12}-[a-z]+-[0-9a-f]{4})\)\s*$", ln)
        if m and ("case total:" in ln or re.search(r"\bruns \d+ of \d+", ln)):
            out[m.group(1)] = ln
    return out


for lab in sys.argv[2:]:
    D = EV / lab
    led = json.loads((D / "measures" / "spend-ledger.json").read_text())
    pl = progress_lines(D)
    for cid, c in led.get("cases", {}).items():
        if cid.startswith("<"):
            continue
        ln = pl.get(cid, "")
        m = re.search(r"case total: (\d+) runs used(?:: (\d+) by the user's requests, (\d+) by your relayed rework[^;]*)?(?:;| of) (\d+) handed down", ln)
        if not m:  # a one-task case: `progress` prints no case total; its runs are the head line's `runs N of M`
            one = re.search(r"\bruns (\d+) of (\d+)", ln)
            if one:
                class _M:  # the same groups as the case-total match
                    def __init__(s, r, h): s.g = {1: r, 3: None, 4: h}
                    def group(s, i): return s.g[i]
                m = _M(one.group(1), one.group(2))
        tasks = case_tasks(D, cid)
        last = pl.get(max(tasks), "") if tasks else ln
        st = re.search(r"\]: (\w+)", last)
        head = (D / "msgs" / "sent" / f"{cid}.md").read_text(errors="replace")
        b = re.search(r"^budget:\s*(\d+)", head, re.M)
        runs = int(m.group(1)) if m else None
        rel = int(m.group(3)) if m and m.group(3) else 0
        c.update({"state": st.group(1) if st else None, "runs": runs, "relayed_runs": rel,
                  "budget": int(m.group(4)) if m else None, "contract_budget": int(b.group(1)) if b else None, "ceilings": [],
                  "d14_used": (runs - rel) if runs is not None else None,
                  "_files": {"state": f"{lab}/final-services-progress-status-health.txt (the case's latest task {max(tasks) if tasks else cid})",
                             "runs, relayed_runs, budget, d14_used": f"{lab}/final-services-progress-status-health.txt (task {cid})",
                             "contract_budget": f"{lab}/msgs/sent/{cid}.md budget header", "ceilings": "not derived by hand (STUDY.md, declared limit)"},
                  "_progress_line": ln[:400]})
    led["_about_scorer"] = ("Completed by the scoring step (scoring/complete_ledger.py) from the raw files; the stream step's ledger "
                            f"{lab}/measures/spend-ledger.json is unchanged.")
    out = EV / "scoring" / lab / "measures"
    out.mkdir(parents=True, exist_ok=True)
    (out / "spend-ledger.json").write_text(json.dumps(led, indent=1))
    print(lab, {cid: (c.get("memo"), c.get("state"), c.get("runs"), c.get("relayed_runs"), c.get("d14_used"),
                      c.get("lena_plan_budget", 0) + sum(int(g["runs"]) for g in c.get("lena_grants", [])))
                for cid, c in led["cases"].items() if not cid.startswith("<")})
