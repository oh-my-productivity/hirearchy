"""MCP server: the organization's system calls.

Identity is assigned, not claimed: the scheduler starts each run with ORG_AGENT=<address>.
Without ORG_AGENT (e.g. registered in your own kiro mcp.json) you act as `root`, the human.
"""

from __future__ import annotations

import os

from mcp.server.fastmcp import FastMCP

from .core import ROOT, Org

INSTRUCTIONS = """\
You are a member of a file-based organization of agents. Your identity is fixed by the runtime.
Work flows down as tasks (delegate), results flow up (report), everything else is a note (send).
Call whoami first if you do not know your role, reports, budget and open tasks.
"""


def build_server(org: Org, me: str) -> FastMCP:
    me = org.require(me)
    mcp = FastMCP("orgmcp", instructions=INSTRUCTIONS)

    @mcp.tool()
    def whoami() -> str:
        """Your address, role, budget, direct reports, open tasks, outstanding delegations and charter."""
        return org.whoami(me)

    @mcp.tool()
    def inbox() -> str:
        """The messages for this run. For root (the human) this lists unread messages and marks them read."""
        if me == ROOT:
            batch = org.begin_run(ROOT)
            org.end_run(ROOT, ok=True)
        else:
            batch = org.messages(me, "inflight") or org.messages(me, "inbox")
        return "\n".join(m.render() for m in batch) or "(no new messages)"

    @mcp.tool()
    def delegate(
        to: str, title: str, goal: str, acceptance: str, inputs: list[str] | None = None, budget: int | None = None
    ) -> str:
        """Assign a task to one of your direct reports.

        to: the report's address (e.g. "ceo/cto"). title: a few words. goal: what outcome is needed and why.
        acceptance: concrete, checkable criteria for "done". inputs: paths (relative to the org root) the
        report should read. budget: runs handed to the report from your own budget (default from ORG.md).
        Returns the task id. Do not wait for the result: end your run, the result will wake you.
        """
        msg = org.delegate(me, to, title, goal, acceptance, inputs or [], budget)
        return f"delegated {msg.id} to {msg.to} with budget {msg.budget}. Your budget is now {org.budget(me)}."

    @mcp.tool()
    def report(task_id: str, status: str, summary: str, artifacts: list[str] | None = None) -> str:
        """Answer a task assigned to you, exactly once. Goes to whoever assigned it.

        status: "done" (acceptance criteria met), "failed", or "blocked" (say what would unblock it).
        summary: at most ~10 lines; this is all your manager reads by default. artifacts: paths of the
        files that hold the work (relative to the org root); they must exist. The runtime annotates each
        with its word count and whether it changed since the task was assigned.
        """
        msg = org.report(me, task_id, status, summary, artifacts or [])
        return f"reported {status} on {task_id} to {msg.to}"

    @mcp.tool()
    def send(to: str, body: str, title: str = "", reply_to: str | None = None, budget: int = 0) -> str:
        """Send a note: a question, information, or an escalation.

        Allowed recipients: your parent, your direct reports, your siblings, or the sender of the message
        you reply to (set reply_to to its id). budget: extra runs to grant a direct report (optional).
        """
        msg = org.send(me, to, body, title=title, reply_to=reply_to, budget=budget)
        return f"sent {msg.id} to {msg.to}"

    @mcp.tool()
    def hire(
        name: str,
        role: str,
        charter: str,
        model: str | None = None,
        tools: list[str] | None = None,
        can_hire: bool = False,
        max_children: int = 5,
        workspace: str | None = None,
    ) -> str:
        """Create a direct report (only if your charter allows hiring).

        name: lowercase-dashed (becomes the address <you>/<name>). role: a short job title.
        charter: markdown with purpose, responsibilities, decision rights, what to escalate, quality bar.
        model: kiro model id (optional). tools: kiro built-in tools to grant, only ones you have yourself
        (e.g. "read", "write", "shell"). can_hire: whether the report may build its own team.
        workspace: directory the report works in (must be inside yours).
        A new report has no budget until you delegate a task to it.
        """
        addr = org.hire(me, name, role, charter, model=model, tools=tools or [], can_hire=can_hire,
                        max_children=max_children, workspace=workspace)
        return f"hired {addr}"

    @mcp.tool()
    def retire(name: str, reason: str) -> str:
        """Remove a direct report and its team. Their open tasks are reported to you as failed."""
        addr = org.retire(me, name, reason)
        return f"retired {addr}"

    @mcp.tool()
    def read(path: str = ".") -> str:
        """Read a file (with word count and modification time) or list a directory anywhere in the
        organization. Paths are relative to the org root, e.g. "ceo/writer/work/brief.md"."""
        return org.read(path)

    @mcp.tool()
    def write(path: str, content: str, append: bool = False) -> str:
        """Write a file inside your own directory. Paths are relative to the org root, like every path here,
        so they start with your address: e.g. "<you>/MEMORY.md" or "<you>/work/plan.md".

        You may also rewrite a direct report's charter ("<you>/<name>/AGENT.md"). Inboxes, logs and your own
        charter are managed by the runtime; use send/delegate/report to communicate.
        """
        p = org.write(me, path, content, append=append)
        return f"wrote {p.relative_to(org.root)}"

    @mcp.tool()
    def status() -> str:
        """The whole organization as a tree: each agent's role, state, budget and workload."""
        return org.tree()

    return mcp


def serve() -> None:
    org = Org(Org.find_root())
    build_server(org, os.environ.get("ORG_AGENT") or ROOT).run()
