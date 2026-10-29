#!/usr/bin/env python3
"""P2 effort-stop counter (batch 1.1; the brief: "a run whose effort was not set is stopped and relaunched uncharged (`# kiro: effort not
set` in its log). Count such stops per stream"). Read-only.

    python3 -B effort_stops.py <S>/org [--turn N]      prints `turn N: effort stops <k> of <n> run logs (<files>)`
    python3 -B effort_stops.py --selfcheck             constructed run logs

A stop is a run log under <org>/**/runs/*.log (not .git) with a line starting `# kiro: effort not set`. Also counted beside it (reported): run
logs whose `# cmd:` line lacks `--effort high` (H4's side, model_check.sh decides it) and run logs with P1's F-P1-13 line `failed to set
effort`.
"""
import re
import sys
import tempfile
from pathlib import Path

STOP = re.compile(r"^# kiro: effort not set", re.M)
CMD = re.compile(r"^# cmd: .*$", re.M)
FAILED = re.compile(r"failed to set effort")


def count(org: Path) -> dict:
    logs = sorted(p for p in org.rglob("runs/*.log") if ".git" not in p.parts) if org.is_dir() else []
    stops, nocmd, failed = [], [], []
    for p in logs:
        t = p.read_text(errors="replace")
        if STOP.search(t):
            stops.append(str(p.relative_to(org)))
        m = CMD.search(t)
        if m and "--effort high" not in m.group(0):
            nocmd.append(str(p.relative_to(org)))
        if FAILED.search(t):
            failed.append(str(p.relative_to(org)))
    return {"logs": len(logs), "stops": stops, "cmd_without_effort_high": nocmd, "failed_to_set_effort": failed}


def selfcheck() -> int:
    with tempfile.TemporaryDirectory(dir="/tmp") as d:
        org = Path(d) / "org"
        (org / "lead" / "runs").mkdir(parents=True)
        (org / "lead" / "runs" / "a.log").write_text("# run of lead\n# cmd: kiro-cli chat --model claude-sonnet-5.5 --effort high\n")
        (org / "lead" / "runs" / "b.log").write_text("# run of lead\n# kiro: effort not set (relaunched uncharged)\n# cmd: x --effort high\n")
        (org / "lead" / "runs" / "c.log").write_text("# run\n# cmd: kiro-cli chat --model claude-sonnet-5.5\nfailed to set effort 'high'\n")
        (org / ".git" / "runs").mkdir(parents=True)
        (org / ".git" / "runs" / "d.log").write_text("# kiro: effort not set\n")
        r = count(org)
        ok = r["logs"] == 3 and r["stops"] == ["lead/runs/b.log"] and r["cmd_without_effort_high"] == ["lead/runs/c.log"] and r["failed_to_set_effort"] == ["lead/runs/c.log"]
        print(f"effort_stops selfcheck: {'1 of 1 ok' if ok else 'MISMATCH ' + str(r)}")
        return 0 if ok else 1


def main() -> int:
    if sys.argv[1:2] == ["--selfcheck"]:
        return selfcheck()
    org = Path(sys.argv[1])
    turn = sys.argv[sys.argv.index("--turn") + 1] if "--turn" in sys.argv else "end"
    r = count(org)
    print(f"turn {turn}: effort stops {len(r['stops'])} of {r['logs']} run logs ({', '.join(r['stops']) or 'none'}); "
          f"cmd without --effort high {len(r['cmd_without_effort_high'])}; 'failed to set effort' {len(r['failed_to_set_effort'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
