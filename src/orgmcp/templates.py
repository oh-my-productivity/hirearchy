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


def notice_budget_returned(agent: str, amount: int, retired_by: str, reason: str) -> str:
    return (
        f"`{agent}` and its team were retired by {retired_by} ({reason}). "
        f"Their unspent budget, {amount} run(s), is returned to you with this note."
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


# What to do about each health flag; {a} is the flagged agent.
REVIEW_ACTIONS = {
    "stuck": "follow up with `{a}` or reassign the work",
    "out_of_budget": 'grant runs with send(to="{a}", body="<why>", budget=N), or report the task failed',
    "paused": "investigate why `{a}` is paused; failed runs need a human (`orgmcp resume {a}`), so escalate",
    "low_quality": "tighten `{a}`'s charter and acceptance criteria, rework with delegate(..., revises=<task id>), or replace it",
    "expensive": "narrow `{a}`'s tasks, or change its charter or model",
    "wasteful": "fix `{a}`'s charter so every run ends with an action (report or send)",
    "idle": "retire `{a}` if it is no longer needed",
}


def review_item(addr: str, flag: str, reason: str, act: bool = True, branch: str | None = None) -> str:
    """One flagged (agent, flag) pair. ``branch`` = the report whose team contains the flagged ``addr``."""
    if branch:
        line = f"- `{branch}` team: `{addr}` is {flag}: {reason}"
        return line + (f"\n  -> ask `{branch}` to deal with it, or step in via its charter" if act else "")
    line = f"- `{addr}` {flag}: {reason}"
    return line + (f"\n  -> {REVIEW_ACTIONS[flag].format(a=addr)}" if act else "")


def notice_review_manager(manager: str, items: list[str]) -> str:
    return (
        f"Health review: {len(items)} new problem(s) among your direct reports.\n"
        + "\n".join(items)
        + f"\n\nAct within your charter and record your decisions in `{manager}/MEMORY.md`. "
        "Problems that persist are not repeated in later reviews."
    )


def notice_review_root(summary: str, items: list[str], skipped: dict[str, str]) -> str:
    """The org-wide summary for root: every flagged agent, with actions for root's own reports."""
    lines = [f"Health review: {summary}"] + items
    if skipped:
        lines.append("Managers not notified: " + ", ".join(f"`{m}` ({why})" for m, why in skipped.items()) + ".")
    return "\n".join(lines)


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
