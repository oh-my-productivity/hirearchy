"""A deterministic stand-in for an LLM agent run, used to test the scheduler.

Behaviour is chosen by FAKE_MODE:
  work  - managers delegate each task to their first report and report up when results arrive;
          leaves write an artifact and report done.
  crash - exit 1 without doing anything.
  idle  - do nothing (simulates an agent that forgets to report).
"""

import os
import sys

from orgmcp.core import Org

mode = os.environ.get("FAKE_MODE", "work")
if mode == "crash":
    sys.exit(1)
if mode == "idle":
    sys.exit(0)

org = Org(os.environ["ORG_ROOT"])
me = os.environ["ORG_AGENT"]
kids = org.children(me)
for msg in org.messages(me, "inflight"):
    if msg.type == "task":
        if kids:
            sub = org.delegate(me, kids[0], msg.title, msg.body, "same as parent", budget=2)
            org.write(me, f"{me}/MEMORY.md", f"{sub.id}={msg.id}\n", append=True)
        else:
            org.write(me, f"{me}/work/out.md", f"done: {msg.title}")
            org.report(me, msg.id, "done", "Did it.", [f"{me}/work/out.md"])
    elif msg.type == "result":
        mapping = dict(line.split("=") for line in org.memory(me).split())
        org.report(me, mapping[msg.reply_to], msg.status, f"Team result: {msg.status}")
