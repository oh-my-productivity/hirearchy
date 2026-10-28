"""The notices the runtime sends: budget, failures, stalls, health reviews."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from .api import Notices

# What to do about each health flag; {a} is the flagged agent. None of the actions suggests a change of an agent's charter or model: those are the plan's,
# which the user changes (design 6.6: the texts that prompted a charter edit by a manager).
REVIEW_ACTIONS = {
    "stuck": "follow up with `{a}` or reassign the work",
    "out_of_budget": 'grant runs with send(to="{a}", body="<why>", budget=N), or report the task failed',
    "paused": "investigate why `{a}` is paused; failed runs need a human (`hirearchy resume {a}`), so escalate",
    "low_quality": (
        "compare `{a}`'s last checks with the client's rejections it let through (escapes, and its re-checks after a FAIL): if you own a "
        "service, make sure its review tasks carry the regression list. Its charter is the plan's: the retro brief shows the user these escapes."
    ),
    "expensive": "narrow `{a}`'s tasks; its model and its charter are the plan's, which the user changes",
    "wasteful": "tell `{a}` (send) that every run ends with an action (report or send)",
    "stranded_budget": "ask `{a}` to return its budget (it can `send` its parent a note with `budget=N`), or retire it",
    "idle": "retire `{a}` if it is no longer needed",
}



class StaticNotices(Notices):
    """Renders the notices from fixed text (pure: the same arguments always give the same bytes)."""

    def budget(self, agent: str, unread: int) -> str:
        return (
            f"`{agent}` has {unread} unread message(s) but no budget left, so it is paused.\n"
            f"To continue, grant runs: send(to=\"{agent}\", body=\"<why>\", budget=<runs>). "
            "Otherwise decide whether its work should be reported as failed or reassigned."
        )

    def budget_returned(self, agent: str, amount: int, retired_by: str, reason: str) -> str:
        return (
            f"`{agent}` and its team were retired by {retired_by} ({reason}). "
            f"Their unspent budget, {amount} run(s), is returned to you with this note."
        )

    def failures(self, agent: str, count: int, log: str, to_human: bool = True) -> str:
        """Tell someone that ``agent`` keeps crashing. The human gets the fix; an LLM parent gets its options."""
        head = f"`{agent}` failed {count} runs in a row and is paused. Last run log: {log}\n"
        if to_human:
            return head + f"A human must inspect it and run `hirearchy resume {agent}`."
        return (
            head
            + "Its unread messages and open tasks are stuck until then. A human will inspect the crash and resume it; "
            "you cannot. Meanwhile you can keep your own work moving:\n"
            f"- reassign: `delegate` the work to another direct report (or `hire` one), and `retire` `{agent}` if it "
            "is not needed (its open tasks are closed as failed);\n"
            "- or, if you cannot go on without it, `report` the affected task to whoever assigned it with status "
            "`blocked` (or `failed`) and say that `" + agent + "` is crashing, so they can plan around it."
        )

    def nudge(self, task_id: str, title: str) -> str:
        return (
            f"Task {task_id} ({title}) is still open, you are not running or waiting on any delegated work, "
            "and nothing has happened for a while. Finish it and `report` done, "
            "or `report` blocked/failed with the reason."
        )

    def stalled(self, agent: str, task_id: str, title: str, told: Sequence[str]) -> str:
        return (
            f"`{agent}` is stalled on task {task_id} ({title}): it is not running, not waiting on delegated work, "
            f"and has not reported. Already told: {', '.join(f'`{t}`' for t in told)}. "
            "Follow up with it, reassign the work, or escalate further."
        )

    def review_item(self, addr: str, flag: str, reason: str, act: bool = True, branch: str | None = None) -> str:
        """One flagged (agent, flag) pair. ``branch`` = the report whose team contains the flagged ``addr``."""
        if branch:
            line = f"- `{branch}` team: `{addr}` is {flag}: {reason}"
            return line + (f"\n  -> ask `{branch}` to deal with it, or step in via its charter" if act else "")
        line = f"- `{addr}` {flag}: {reason}"
        return line + (f"\n  -> {REVIEW_ACTIONS[flag].format(a=addr)}" if act else "")

    def review_manager(self, manager: str, items: Sequence[str]) -> str:
        return (
            f"Health review: {len(items)} new problem(s) among your direct reports.\n"
            + "\n".join(items)
            + f"\n\nAct within your charter and record your decisions in `{manager}/MEMORY.md`. "
            "Problems that persist are not repeated in later reviews."
        )

    def review_root(self, summary: str, items: Sequence[str], skipped: Mapping[str, str]) -> str:
        """The org-wide summary for root: every flagged agent, with actions for root's own reports."""
        lines = [f"Health review: {summary}"] + list(items)
        if skipped:
            lines.append("Managers not notified: " + ", ".join(f"`{m}` ({why})" for m, why in skipped.items()) + ".")
        return "\n".join(lines)
