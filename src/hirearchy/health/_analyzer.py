"""``FileHealthAnalyzer``: the metrics and flags of each agent, from its message files and run logs."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime

from ..agents import AgentDirectory
from ..budget import BudgetQuery
from ..eligibility import AgentStates, PauseStore
from ..kernel import ROOT, Clock, OrgError, aware, depth, fmt_duration, latest_results, msg_time, parent, parse_time
from ..mail import MailboxReader
from ..runs import RunLogReader
from ._branches import branch_totals
from ._ports import ClientRework, EscapeCounter, HireDates, RunCount
from .api import AgentHealth, HealthAnalyzer, HealthThresholds, OrgHealth


class FileHealthAnalyzer(HealthAnalyzer):
    def __init__(
        self, agents: AgentDirectory, mail: MailboxReader, runs: RunLogReader, run_count: RunCount, budgets: BudgetQuery,
        pauses: PauseStore, states: AgentStates, thresholds: HealthThresholds, rework: ClientRework, escapes: EscapeCounter, hired: HireDates,
        clock: Clock,
    ) -> None:
        self._agents = agents
        self._mail = mail
        self._runs = runs
        self._run_count = run_count
        self._budgets = budgets
        self._pauses = pauses
        self._states = states
        self._thresholds = thresholds
        self._rework = rework
        self._escapes = escapes
        self._hired = hired
        self._clock = clock

    def agent_health(self, addr: str, now: datetime | None = None, limits: Mapping[str, float] | None = None) -> AgentHealth:
        a = self._agents.require(addr)
        if a == ROOT:
            raise OrgError("root is the human; only agents have health data")
        now, cfg = aware(now) or self._clock.now(), limits or self._thresholds.thresholds()

        received, sent = self._mail.received(a), self._mail.sent(a)
        tasks = [m for m in received if m.type == "task"]
        results = latest_results(sent)  # task id -> its latest result: each task counts once, by its latest status
        answered = set(results)
        open_tasks = [t for t in tasks if t.id not in answered]
        answered_out = {m.reply_to for m in received if m.type == "result"}
        waiting = any(m.type == "task" and m.id not in answered_out for m in sent)
        by_status = {s: sum(1 for r in results.values() if r.status == s) for s in ("done", "failed", "blocked")}
        client_driven = self._rework.driven(tasks, results)
        rework = sum(1 for t in tasks if t.revises and t.id not in client_driven)
        unread, running, paused = self._mail.unread(a), self._mail.has_inflight(a), self._pauses.paused(a)
        budget_left, runs_used = self._budgets.budget(a), self._run_count.count(a)

        windows = self._runs.windows(a)
        sent_at = [t for t in map(msg_time, sent) if t]
        outcomes = self._runs.outcomes(a)
        failed, runtime_only = outcomes.failed, outcomes.runtime_only
        excluded = failed | runtime_only  # run starts that say nothing about the agent's own efficiency
        judged = sum(1 for start, _ in windows if start not in excluded)
        candidates = windows[:-1] if running else windows  # a run in progress is not (yet) empty
        empty = sum(
            1 for start, end in candidates
            if start not in excluded and not any(start <= t <= end for t in sent_at)
        )
        activity = [end for _, end in windows] + sent_at
        last = max(activity, default=None)
        since = max(0.0, (now - last).total_seconds()) if last else None

        ages = [max(0.0, (now - c).total_seconds()) for t in open_tasks if (c := parse_time(t.created))]
        oldest = max(ages, default=None)
        result_times = [t for t in map(msg_time, (m for m in sent if m.type == "result")) if t]
        last_result = max(result_times, default=None)
        # Runs that say nothing about the agent's own efficiency (failed, or woken only by runtime notes) are not charged.
        since_result = sum(
            1 for start, _ in windows if start not in excluded and (last_result is None or start > last_result)
        )
        runs_per_task = (runs_used - len(excluded)) / len(results) if results else None
        escapes = self._escapes.counts(a)

        flags: dict[str, str] = {}
        if oldest is not None and oldest > cfg["stuck_after_seconds"] and not (waiting or running or unread):
            flags["stuck"] = f"open task is {fmt_duration(oldest)} old and nothing is in progress"
        if budget_left is not None and budget_left <= 0 and (unread or open_tasks):
            flags["out_of_budget"] = "no budget left but has unread mail or open tasks"
        if paused:
            flags["paused"] = f"paused: {paused}"
        if escapes.judged and escapes.judged >= cfg["min_judged_for_quality"] and escapes.escapes / escapes.judged > cfg["max_escape_ratio"]:
            flags["low_quality"] = (
                f"{escapes.escapes} of {escapes.judged} judged deliveries it signed off were rejected by the client after `done` (escapes); "
                f"{escapes.rechecks} re-check(s) after a FAIL, costing {escapes.rework_runs} author rework run(s)"
            )
        reasons = []
        if runs_per_task is not None and runs_per_task > cfg["max_runs_per_task"]:
            reasons.append(f"{runs_per_task:.1f} runs per completed task (max {cfg['max_runs_per_task']})")
        if open_tasks and since_result > cfg["max_runs_without_result"]:
            reasons.append(f"{since_result} runs without a result on an open task (max {cfg['max_runs_without_result']})")
        if reasons:
            flags["expensive"] = "; ".join(reasons)
        if judged and judged >= cfg["min_runs_for_waste"] and empty / judged > cfg["max_empty_run_ratio"]:
            flags["wasteful"] = f"{empty} of {judged} runs sent no message"
        quiet = (since if last else self._since_hired(a, now)) or 0.0
        if (
            budget_left is not None and budget_left > 0 and parent(a) != ROOT and quiet > cfg["stranded_after_seconds"]
            and not (open_tasks or waiting or running or unread)
        ):  # root has no limit, so budget parked in its direct reports starves nobody
            flags["stranded_budget"] = (
                f"{budget_left} unused run(s) and no work or activity for {fmt_duration(quiet)}; "
                "they belong with its parent"
            )
        if not (open_tasks or waiting or running or unread) and quiet > cfg["idle_after_seconds"]:
            flags["idle"] = f"no open tasks and no activity for {fmt_duration(quiet)}; candidate to retire"

        return AgentHealth(
            addr=a, depth=depth(a), state=self._states.state(a), budget_left=budget_left,
            budget_received=sum(m.budget for m in received), runs_used=runs_used, tasks_received=len(tasks),
            open_tasks=len(open_tasks), oldest_open_age=oldest, rework=rework, client_rework=len(client_driven), empty_runs=empty,
            runs_per_task=runs_per_task, last_activity=last, since_activity=since, flags=flags,
            done=by_status["done"], failed=by_status["failed"], blocked=by_status["blocked"],
            failed_runs=len(failed), runtime_runs=len(runtime_only - failed), escapes=escapes.escapes, judged=escapes.judged,
            rechecks=escapes.rechecks, rework_runs=escapes.rework_runs,
        )

    def org_health(self, root: str = ROOT, now: datetime | None = None) -> OrgHealth:
        top = self._agents.require(root)
        now, cfg = aware(now) or self._clock.now(), self._thresholds.thresholds()
        addrs = self._agents.agents() if top == ROOT else self._agents.subtree(top)
        agents = [self.agent_health(a, now, cfg) for a in addrs]
        by_addr = {h.addr: h for h in agents}
        return OrgHealth(root=top, now=now, agents=agents, branches=branch_totals(top, addrs, by_addr))

    def _since_hired(self, addr: str, now: datetime) -> float:
        """Seconds since the agent was hired, for agents that never did anything."""
        return max(0.0, (now - self._hired.hired(addr)).total_seconds())
