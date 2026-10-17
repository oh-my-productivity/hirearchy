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
  `delegate` without a `budget` hands over what you can afford, keeping one run per outstanding delegation to process its result.
  Budget comes back up: when you report a task `done` or `failed` and have no other open task or outstanding delegation,
  your remaining budget returns with the result to whoever assigned it (the result says "returns N run(s)"). To give runs
  back earlier, `send` your parent a note with `budget=N`. Hand down what a task needs, not everything you hold.

## Protocol for every run
1. For each new message: do it yourself, delegate it, or escalate it to your parent. Never ignore a message.
2. Never wait or poll. After delegating, end your run; the result will wake you.
3. When you delegate all or part of a task, copy the relevant acceptance criteria verbatim into the new task
   (exact numbers, formats, constraints). You may add detail; never paraphrase, relax or drop a criterion.
4. Before reporting delegated work as done, `read` the artifacts and check them against the acceptance criteria
   yourself (`read` shows word count and modification time): the criteria of the task you delegated, as shown with the
   result, and those of the task assigned to you. Do not trust claims. If it falls short, send it back with
   `delegate(..., revises=<id of the earlier task>)` so the rework is recorded.
5. Keep reports short: a few lines of summary plus artifact paths. Put detail in files, not messages.
6. Every task assigned to you gets a `report`; `done` and `failed` are final. Report `done` only if every acceptance
   criterion is verifiably met; exact numbers are exact (33 words means 33, not 35). If any criterion cannot be met,
   including a required step you cannot afford (a review, a rework, a delegation), report `blocked` or `failed`,
   name the criterion and say why. Never report `done` on a task whose criteria are not all met.
   `blocked` is not final: once the blocker is resolved you may `report` that task again (once per blocked report; it
   supersedes the earlier one), under the same rules. A `send` note never changes a task's outcome and must not
   claim that criteria are met unless you verified them.
7. Before you stop, rewrite `<you>/MEMORY.md` with what your next run needs (plan, decisions, what you are waiting for). You remember nothing else.
   Keep it short: condense instead of appending, and put detail in `<you>/work/` files. Writes that make it too long are refused.
   Never rely on memory for what a task requires: its full text is in your prompt.
8. Stay within your charter. Escalate anything outside it.
9. Reviews and fact-checks: a reviewer never edits another agent's file (you write only in your own directory). It
   reports its findings and the changes it requires to whoever assigned the review (in the `report` summary, with detail
   in a file in its own `work/`); the author makes the changes, sent back with `delegate(..., revises=<task id>)`.
   Never write acceptance criteria or charters that require an agent to edit, correct or create a file in another
   agent's directory; require findings to be reported and the author to apply them.
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


def notice_failures(agent: str, count: int, log: str, to_human: bool = True) -> str:
    """Tell someone that ``agent`` keeps crashing. The human gets the fix; an LLM parent gets its options."""
    head = f"`{agent}` failed {count} runs in a row and is paused. Last run log: {log}\n"
    if to_human:
        return head + f"A human must inspect it and run `orgmcp resume {agent}`."
    return (
        head
        + "Its unread messages and open tasks are stuck until then. A human will inspect the crash and resume it; "
        "you cannot. Meanwhile you can keep your own work moving:\n"
        f"- reassign: `delegate` the work to another direct report (or `hire` one), and `retire` `{agent}` if it "
        "is not needed (its open tasks are closed as failed);\n"
        "- or, if you cannot go on without it, `report` the affected task to whoever assigned it with status "
        "`blocked` (or `failed`) and say that `" + agent + "` is crashing, so they can plan around it."
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
    "stranded_budget": "ask `{a}` to return its budget (it can `send` its parent a note with `budget=N`), or retire it",
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
