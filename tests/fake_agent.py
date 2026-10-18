"""A deterministic stand-in for an LLM agent run, used to test the scheduler.

Behaviour is chosen by FAKE_MODE:
  work  - managers delegate each task to their first report and report up when results arrive;
          leaves write an artifact and report done.
  crash - exit 1 without doing anything.
  idle  - do nothing (simulates an agent that forgets to report).
  tools - like work, but through the orgmcp MCP tools (in-process), so tool.call events are recorded; each leaf also
          makes one refused call (a report with a bad status) before reporting.
  hang  - sleep for a long time (a run the scheduler has to kill on timeout).
"""

import os
import sys

from orgmcp.core import Org

mode = os.environ.get("FAKE_MODE", "work")
if mode == "crash":
    sys.exit(1)
if mode == "idle":
    sys.exit(0)

if mode == "hang":
    import time

    time.sleep(600)
    sys.exit(0)

org = Org(os.environ["ORG_ROOT"])
me = os.environ["ORG_AGENT"]
kids = org.children(me)

if mode == "tools":
    import asyncio

    from orgmcp import telemetry
    from orgmcp.server import build_server

    telemetry.set_process("mcp")
    server = build_server(org, me)

    def call(tool, **args):
        try:
            asyncio.run(server.call_tool(tool, args))
        except Exception:  # a refusal: the tool raised, the event recorded it
            pass

    call("whoami")
    for msg in org.messages(me, "inflight"):
        if msg.type == "task":
            if kids:
                call("delegate", to=kids[0], title=msg.title, goal=msg.body, acceptance="same as parent", budget=2)
                call("write", path=f"{me}/MEMORY.md", content=f"{msg.id}\n", append=True)
            else:
                call("write", path=f"{me}/work/out.md", content=f"done: {msg.title}")
                call("report", task_id=msg.id, status="bogus", summary="x" * 5000)  # refused
                call("report", task_id=msg.id, status="done", summary="Did it.", artifacts=[f"{me}/work/out.md"])
        elif msg.type == "result":
            call("report", task_id=org.memory(me).split()[0], status=msg.status, summary=f"Team result: {msg.status}")
    sys.exit(0)

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
