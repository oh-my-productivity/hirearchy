#!/usr/bin/env python3
"""P2 root's requests and one-off tasks after a turn (protocol 3.2, 4.5; F-P1-9: the memo input's name and value are read from each request,
never assumed). Read-only. Usage: requests_by_turn.py <S>/org --turn N   (two lines: the memo requests by notes date, the one-off tasks)."""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import p2lib as L  # noqa: E402

org, turn = Path(sys.argv[1]), sys.argv[sys.argv.index("--turn") + 1]
sent = L.read_msgs([org / "sent"]) if (org / "sent").is_dir() else {}
memos, oneoffs = [], []
for m in sorted(sent.values(), key=lambda m: m.id):
    if m.get("type") != "task" or m.get("revises"):
        continue
    if m.get("service"):
        req = " ".join(m.section("Request"))
        d = re.findall(r"(\d{4}-\d{2}-\d{2})", req)
        memos.append(f"{d[0] if len(d) == 1 else '?'}({m.get('service')})")
    else:
        oneoffs.append(f"{m.id} \"{m.get('title')}\" -> {m.get('to')}")
print(f"turn {int(turn):02d}: root's new service requests by notes date: {' '.join(memos) or '(none)'}")
print(f"turn {int(turn):02d}: root's one-off tasks: {'; '.join(oneoffs) or '(none)'}")
