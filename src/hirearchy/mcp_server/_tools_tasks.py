"""Work down and results up: ``delegate`` and ``report``."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..budget import BudgetQuery
from ..dispatch import TaskAssigner, TaskReporter
from ..kernel import ROOT, Provider
from ..mail import MailboxReader
from ..services import ServiceHints
from ._ports import ToolGroup

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP


class TaskTools(ToolGroup):
    def __init__(
        self, assigner: Provider[TaskAssigner], reporter: Provider[TaskReporter], budgets: Provider[BudgetQuery], mail: Provider[MailboxReader],
        hints: Provider[ServiceHints],
    ) -> None:
        self._assigner = assigner
        self._reporter = reporter
        self._budgets = budgets
        self._mail = mail
        self._hints = hints

    def register(self, mcp: FastMCP, me: str) -> None:
        if me == ROOT:  # only root records where a rework comes from: the agents' tool has no `source`
            self._register_root_delegate(mcp, me)
        else:
            self._register_agent_delegate(mcp, me)

        @mcp.tool()
        def report(
            task_id: str, status: str, summary: str, artifacts: list[str] | None = None, lessons: str | None = None
        ) -> str:
            """Answer a task assigned to you. Goes to whoever assigned it.

        status: "done" (every acceptance criterion verifiably met), "failed", or "blocked" (say what would unblock it).
        `done` and `failed` are final: a second report is refused. `blocked` is not: once the blocker is resolved
        you may report the task again, once per blocked report (any status; the new report supersedes the old one),
        under the same rules. A `send` note never changes a task's outcome and must not claim criteria are met.
        summary: at most ~10 lines; this is all your manager reads by default. artifacts: paths of the
        files that hold the work; they must exist. Files in the organization: path relative to the org root.
        Files in your workspace: the ABSOLUTE path (anything else outside the organization is refused). The runtime
        annotates each with its word count and whether it changed since the task was assigned.
        lessons: required when the task is a request for a service, whatever the status - done, failed or blocked
        (1-3 lines, at most 800 characters: what worked or went wrong, what to change in the playbook, the evidence:
        runs, rework, review findings); it is recorded in the result and reviewed before the next request. Optional
        otherwise.
        """
            msg = self._reporter().report(me, task_id, status, summary, artifacts or [], lessons)
            returned = f"; returned {msg.budget} unspent run(s) of budget to {msg.to}" if msg.budget else ""
            task = self._mail().find_received(me, task_id)
            hint = self._hints().report_hint(me, task, status) if task is not None else ""
            return f"reported {status} on {task_id} to {msg.to}{returned}" + (f". {hint}" if hint else "")

    def _register_root_delegate(self, mcp: FastMCP, me: str) -> None:
        @mcp.tool()
        def delegate(
            to: str,
            title: str,
            goal: str,
            acceptance: str,
            inputs: list[str] | None = None,
            budget: int | None = None,
            revises: str | None = None,
            source: str | None = None,
        ) -> str:
            """Assign a task to one of your direct reports.

        to: the report's address (e.g. "ceo/cto"). title: a few words. goal: what outcome is needed and why.
        acceptance: concrete, checkable criteria for "done". inputs: paths (relative to the org root) the
        report should read. budget: runs handed to the report from your own budget. If you omit it, the default is
        min(default_budget from ORG.md, your budget - reserve), where the reserve keeps one run per outstanding
        delegation plus one for this one; if that is below 1 the call fails and tells you your options.
        An explicit budget must leave that same reserve.
        Copy the relevant acceptance criteria verbatim from the task you are working on; never paraphrase or relax them.
        revises: when sending work back for rework, the id of the earlier task you sent to the same report.
        source (with revises): "human" when the user asked for this rework
        (a rework after their own rejection, carrying their corrections, is one), "relayed" (the default) when it is your
        own reading; the owner sees which.
        Returns the task id. Do not wait for the result: end your run, the result will wake you.
        """
            msg = self._assigner().delegate(me, to, title, goal, acceptance, inputs or [], budget, revises, source)
            return f"delegated {msg.id} to {msg.to} with budget {msg.budget}. Your budget is now {self._budgets().budget(me)}."

    def _register_agent_delegate(self, mcp: FastMCP, me: str) -> None:
        @mcp.tool()
        def delegate(
            to: str,
            title: str,
            goal: str,
            acceptance: str,
            inputs: list[str] | None = None,
            budget: int | None = None,
            revises: str | None = None,
        ) -> str:
            """Assign a task to one of your direct reports.

        to: the report's address (e.g. "ceo/cto"). title: a few words. goal: what outcome is needed and why.
        acceptance: concrete, checkable criteria for "done". inputs: paths (relative to the org root) the
        report should read. budget: runs handed to the report from your own budget. If you omit it, the default is
        min(default_budget from ORG.md, your budget - reserve), where the reserve keeps one run per outstanding
        delegation plus one for this one; if that is below 1 the call fails and tells you your options.
        An explicit budget must leave that same reserve.
        Copy the relevant acceptance criteria verbatim from the task you are working on; never paraphrase or relax them.
        revises: when sending work back for rework, the id of the earlier task you sent to the same report.
        Returns the task id. Do not wait for the result: end your run, the result will wake you.
        """
            msg = self._assigner().delegate(me, to, title, goal, acceptance, inputs or [], budget, revises)
            return f"delegated {msg.id} to {msg.to} with budget {msg.budget}. Your budget is now {self._budgets().budget(me)}."
