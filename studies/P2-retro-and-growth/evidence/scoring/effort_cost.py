"""P2 step 12, reported measure: what the uncharged effort stops (batch 1.1) cost in seconds, runs and user turns. Read-only over
EV/<label>/run-logs/ and turn-times.txt; nothing is written under EV/."""
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

EV = Path("/Volumes/workspace/hirearchy/studies/P2-retro-and-growth/evidence")


def stamp(name: str) -> datetime:
    return datetime.strptime(name.split(".")[0], "%Y%m%dT%H%M%S%f").replace(tzinfo=timezone.utc)


def turns(l: str):
    out = []
    for ln in (EV / l / "turn-times.txt").read_text().splitlines():
        m = re.match(r"^turn (\d+): .*utc (\S+) - (\S+)", ln)
        if m:
            out.append((int(m.group(1)), datetime.fromisoformat(m.group(2).replace("Z", "+00:00")), datetime.fromisoformat(m.group(3).replace("Z", "+00:00"))))
    return out


res = {}
for l in sys.argv[1:] or ["R1", "C1", "R1-v1"]:
    logs = sorted((EV / l / "run-logs").rglob("*.log"))
    rows = []
    for f in logs:
        t = f.read_text(errors="replace")
        if "# kiro: effort not set" not in t:
            continue
        agent = str(f.parent.relative_to(EV / l / "run-logs"))
        m = re.search(r"^# exit (-?\d+) after (\d+)s", t, re.M)
        secs = int(m.group(2)) if m else None
        start = stamp(f.name)
        # the relaunch: the next run log of the same agent
        same = sorted(p for p in f.parent.glob("*.log"))
        nxt = next((p for p in same if stamp(p.name) > start), None)
        gap = (stamp(nxt.name) - start).total_seconds() if nxt else None
        turn = next((n for n, a, b in turns(l) if a <= start <= b), None)
        rows.append({"log": f"{agent}/{f.name}", "stopped_after_s": secs, "relaunch_start_after_s": round(gap, 1) if gap is not None else None,
                     "relaunch": f"{agent}/{nxt.name}" if nxt else None, "turn": turn})
    tot = sum(r["relaunch_start_after_s"] or 0 for r in rows)
    res[l] = {"stops": len(rows), "run_logs": len(logs), "rows": rows,
              "seconds_to_relaunch_total": round(tot, 1), "turns_with_a_stop": sorted({r["turn"] for r in rows if r["turn"]}),
              "stream_wall_s": round((turns(l)[-1][2] - turns(l)[0][1]).total_seconds()) if turns(l) else None}
print(json.dumps(res, indent=1))
