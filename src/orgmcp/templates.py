"""Text templates: ORG.md, charters, message bodies, runtime notices, kiro profiles."""

from __future__ import annotations

ORG_RULES = """\
# Organization

## Mission
{mission}

## How this organization works
- Every agent is a directory; its address is the path (e.g. `ceo/cto`). The human at the top is `root`.
- You act ONLY through the orgmcp tools:
  - `delegate` gives a task (a contract) to one of your direct reports.
  - `report` answers a task assigned to you: done, failed, or blocked.
  - `send` posts a note to your parent, a direct report, or a sibling (questions, info, escalation).
- You may write only inside your own directory: artifacts go in `<you>/work/`, notes for your future self in
  `<you>/MEMORY.md`. You may read anything in the organization with `read`.
  Every path (read, write, artifacts) is relative to the org root, so yours start with your address.
- Budgets are counted in runs. Delegating moves budget from you to your report. When you are out of budget you stop being woken.

## Protocol for every run
1. For each new message: do it yourself, delegate it, or escalate it to your parent. Never ignore a message.
2. Never wait or poll. After delegating, end your run; the result will wake you.
3. Before reporting delegated work as done, `read` the artifacts and check them against the acceptance criteria
   yourself (`read` shows word count and modification time). Do not trust claims. If it falls short, send it back with
   `delegate(..., revises=<id of the earlier task>)` so the rework is recorded.
4. Keep reports short: a few lines of summary plus artifact paths. Put detail in files, not messages.
5. Every task assigned to you gets exactly one `report`. If you cannot finish, report `blocked` or `failed` and say why.
6. Before you stop, rewrite `<you>/MEMORY.md` with what your next run needs (plan, decisions, what you are waiting for). You remember nothing else.
   Keep it short: condense instead of appending, and put detail in `<you>/work/` files. Writes that make it too long are refused.
7. Stay within your charter. Escalate anything outside it.
"""

DEFAULT_MISSION = "(Describe the mission of this organization here.)"


def org_rules(mission: str | None) -> str:
    return ORG_RULES.format(mission=(mission or DEFAULT_MISSION).strip())


def charter_body(role: str, charter: str) -> str:
    """The charter under a single H1: the hirer's own top-level heading wins over the generated one."""
    charter = charter.strip()
    if charter.startswith("# "):
        return charter + "\n"
    return f"# Role: {role}\n\n{charter}\n"


def task_body(goal: str, acceptance: str, inputs: list[str]) -> str:
    parts = [f"## Goal\n{goal.strip()}", f"## Acceptance criteria\n{acceptance.strip()}"]
    if inputs:
        parts.append("## Inputs\n" + "\n".join(f"- {p}" for p in inputs))
    return "\n\n".join(parts)


def result_body(summary: str, artifacts: list[str]) -> str:
    parts = [f"## Summary\n{summary.strip()}"]
    if artifacts:
        parts.append("## Artifacts\n" + "\n".join(f"- {p}" for p in artifacts))
    return "\n\n".join(parts)


def notice_budget(agent: str, unread: int) -> str:
    return (
        f"`{agent}` has {unread} unread message(s) but no budget left, so it is paused.\n"
        f"To continue, grant runs: send(to=\"{agent}\", body=\"<why>\", budget=<runs>). "
        "Otherwise decide whether its work should be reported as failed or reassigned."
    )


def notice_failures(agent: str, count: int, log: str) -> str:
    return (
        f"`{agent}` failed {count} runs in a row and is paused. Last run log: {log}\n"
        f"A human must inspect it and run `orgmcp resume {agent}`."
    )


def notice_nudge(task_id: str, title: str) -> str:
    return (
        f"Task {task_id} ({title}) is still open, you are not running or waiting on any delegated work, "
        "and nothing has happened for a while. Finish it and `report` done, "
        "or `report` blocked/failed with the reason."
    )


def notice_stalled(agent: str, task_id: str, title: str, told: list[str]) -> str:
    return (
        f"`{agent}` is stalled on task {task_id} ({title}): it is not running, not waiting on delegated work, "
        f"and has not reported. Already told: {', '.join(f'`{t}`' for t in told)}. "
        "Follow up with it, reassign the work, or escalate further."
    )


def kiro_profile(name: str, description: str, tools: list[str], mcp_server: dict) -> dict:
    """A kiro-cli agent profile that loads only the orgmcp server (not the user's global mcp.json)."""
    return {
        "name": name,
        "description": description,
        "prompt": (
            "You are a member of a file-based agent organization. The user message contains your "
            "rules, charter, memory, state and new messages for this run. Follow it exactly, act "
            "through the orgmcp tools, and stop when the messages are handled."
        ),
        "mcpServers": {"orgmcp": mcp_server},
        "tools": tools,
        "allowedTools": tools,
        "resources": [],
        "hooks": {},
        "includeMcpJson": False,
    }
