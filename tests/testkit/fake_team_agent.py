"""A deterministic stand-in for a whole blueprint team (used by the goal-workflow end-to-end test).

A manager delegates the task to every report (2 runs each), and when no delegation is outstanding writes
``work/final.md`` and reports ``done`` with it. A worker writes ``work/out.md`` and reports ``done`` with it.

The manager reports once, and only when every result is in and read: the results of its reports arrive while it runs, so a run that took only some of
them (the others still unread in its inbox) must wait for the run they wake - a report made then would return no budget (the runtime keeps the budget
of an agent with mail waiting) and the next result would make the manager report a second time, which the runtime refuses.
"""

import os

from hirearchy.core import Org

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
    elif msg.type == "result" and not org.outstanding(me) and not org.unread(me):
        task_id = org.memory(me).strip()
        if any(sent.type == "result" and sent.reply_to == task_id for sent in org.sent(me)):
            continue  # reported by an earlier message of this batch
        org.write(me, f"{me}/work/final.md", f"final of {me}\n")
        org.report(me, task_id, "done", "Team finished.", [f"{me}/work/final.md"])
