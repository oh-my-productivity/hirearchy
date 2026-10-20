"""A deterministic stand-in for a whole blueprint team (used by the goal-workflow end-to-end test).

A manager delegates the task to every report (2 runs each), and when no delegation is outstanding writes
``work/final.md`` and reports ``done`` with it. A worker writes ``work/out.md`` and reports ``done`` with it.
"""

import os

from orgmcp.core import Org

org = Org(os.environ["ORG_ROOT"])
me = os.environ["ORG_AGENT"]
kids = org.children(me)
for msg in org.messages(me, "inflight"):
    if msg.type == "task" and kids:
        for kid in kids:
            org.delegate(me, kid, msg.title, msg.body, "same as parent", budget=2)
        org.write(me, f"{me}/MEMORY.md", msg.id)
    elif msg.type == "task":
        org.write(me, f"{me}/work/out.md", f"result of {me}: {msg.title}\n")
        org.report(me, msg.id, "done", "Did it.", [f"{me}/work/out.md"])
    elif msg.type == "result" and not org.outstanding(me):
        org.write(me, f"{me}/work/final.md", f"final of {me}\n")
        org.report(me, org.memory(me).strip(), "done", "Team finished.", [f"{me}/work/final.md"])
