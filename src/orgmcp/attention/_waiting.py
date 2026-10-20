"""``RootTaskWaitingOnUser``: whether every open root task is unable to progress without the user (moved from ``scheduler.waiting_on_user``)."""

from __future__ import annotations

from collections.abc import Collection

from ..agents import AgentDirectory
from ..budget import BudgetQuery
from ..eligibility import PauseStore, RunnableQuery
from ..kernel import ROOT
from ..mail import MailboxReader, TaskQuery
from ..stalls import NudgeLedger
from .api import Waiting, WaitingOnUser


def names(addrs: list[str]) -> str:
    shown = ", ".join(addrs[:3])
    return shown + (f" and {len(addrs) - 3} more" if len(addrs) > 3 else "")


class RootTaskWaitingOnUser(WaitingOnUser):
    def __init__(
        self, tasks: TaskQuery, agents: AgentDirectory, mail: MailboxReader, pauses: PauseStore, budgets: BudgetQuery, runnable: RunnableQuery,
        nudges: NudgeLedger,
    ) -> None:
        self._tasks = tasks
        self._agents = agents
        self._mail = mail
        self._pauses = pauses
        self._budgets = budgets
        self._runnable = runnable
        self._nudges = nudges

    def analyze(self, *, running: Collection[str] | None = None, blocked: Collection[str] = (), can_start: bool = True) -> Waiting | None:
        tasks = self._tasks.outstanding(ROOT)
        if not tasks:
            return None
        agents = self._agents.agents()
        if (set(running) if running is not None else {a for a in agents if self._mail.has_inflight(a)}) or blocked:
            return None
        if can_start and any(self._runnable.startable(a) for a in agents):
            return None
        nudges = self._nudges
        steps = nudges.entries()
        texts: list[str] = []
        options: list[str] = []
        settled = True
        for t in tasks:
            title = f'"{t.title}"'
            team = [a for a in self._agents.subtree(t.to) if a != ROOT] if self._agents.exists(t.to) else []
            if not team:
                texts.append(f"{title} needs a decision ({t.to} no longer exists)")
                continue
            holding = [a for a in team if self._mail.unread(a) or self._tasks.open_tasks(a)]
            failing = [a for a in holding if self._pauses.paused(a) not in (None, "budget")]
            short = [a for a in holding if a not in failing and (self._budgets.budget(a) or 0) <= 0]
            if failing:
                texts.append(f"{title} needs you to resume {names(failing)} (it keeps failing)")
                options.append(f"a human runs `orgmcp resume {failing[0]}` and you call start()")
            elif short:
                texts.append(f"{title} needs budget ({names(short)} out of runs)")
                options.append(f'grant runs with send(to="{t.to}", body="<why>", budget=N), then call start()')
            else:
                stalled = [a for a in team if self._tasks.open_tasks(a) and not self._tasks.outstanding(a)]
                who = f"{names(stalled)} holds it and nothing is running" if stalled else "nothing is running"
                texts.append(f"{title} needs a decision ({who})")
                options.append(f'send(to="{t.to}", body=<instructions or a changed task>) and call start()')
                for a in stalled:  # the stall ladder (reminder, then escalation up to root) may still wake the holder
                    for task in self._tasks.open_tasks(a):
                        last = steps.get(task.id)
                        if (last["step"] if last else -1) < len(nudges.chain(a, task)) - 1:
                            settled = False
        if not can_start:
            texts.append("the run cap (max_runs) was reached")
            options.append("start() again with a higher max_runs")
        choices = "; or ".join(dict.fromkeys(options + ["accept what exists so far (the task stays open: tell the user, and stop() the scheduler)"]))
        return Waiting("waiting on you: " + "; ".join(texts), "Your options: " + choices + ".", settled)
