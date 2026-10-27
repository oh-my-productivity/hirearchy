"""``StepsPlaybookWriter``: playbook v1 of a service that the blueprint gives none."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from ._protocols import BudgetPlanning, PlaybookWriting
from ._view import s, svc_deliverable
from .api import Agent


class StepsPlaybookWriter(PlaybookWriting):
    def __init__(self, budgets: BudgetPlanning) -> None:
        self._budgets = budgets

    def default_playbook(self, owner: Agent, agents: Sequence[Agent], service: Mapping[str, object], budget: int) -> str:
        """Playbook v1 of a service when the blueprint gives none: the lead charter's procedure for THIS team, as steps.

        Built from the same facts as ``_charter`` and the manager template: who produces, who verifies, the sequencing
        (a step is delegated when its inputs exist), author-routed rework with ``revises``, the runs held back for one
        rework cycle, the final check of every criterion and the report with ``lessons``. The owner improves it later.
        """
        by = {x.addr: x for x in agents}
        split = self._budgets.budget_split(agents, budget)
        est = self._budgets.estimate(agents)["per"]
        kids = [by[c] for c in owner.children]
        makers = [k for k in kids if k.kind != "verifier"]
        checkers = [k for k in kids if k.kind == "verifier"]
        path = s(svc_deliverable(service).get("path"))

        def grant(k: Agent) -> int:
            return split[k.addr]["grant"]

        steps = ["Read the request in your prompt: its inputs, every acceptance criterion and the deliverable. The criteria come from the contract "
                 "and can only be met, never changed; copy the relevant ones verbatim into every task you delegate."]
        if not kids:
            steps.append("Do the work yourself, following the request's deliverable and criteria exactly.")
        for i, k in enumerate(makers):
            what = f"`{k.name}` ({k.role})"
            if i == 0:
                steps.append(f"Delegate to {what} with `budget={grant(k)}`: its part of the request, with the criteria it must meet.")
            else:
                steps.append(f"When the previous result is in, read its artifact yourself, then delegate to {what} with `budget={grant(k)}`, naming the artifact it builds on. "
                             "Never delegate a step before its inputs exist, and send no status messages: results wake you.")
        for k in checkers:
            steps.append(f"When the work exists, delegate to `{k.name}` ({k.role}) with `budget={grant(k)}` to check the final file independently against every criterion. "
                         "It reports findings and required changes to you and never edits the author's file.")
        if checkers:
            usual = f"; for the deliverable usually `{makers[-1].name}`" if makers else ""
            steps.append("If a check fails: send the required changes, quoted verbatim, to the AUTHOR of the failing file "
                         f"(`delegate(to=<author>, revises=<that author's task id>, budget=1)`{usual}), then have the checker re-check that same file "
                         "(`delegate(to=<checker>, revises=<the checker's task id>)`). One rework and one re-check; if it still fails, report `blocked` with options "
                         "and the checker's final line instead of starting another cycle.")
        steps.append("Read the final artifact yourself and check it against EVERY criterion of the request, quoting counts from your own `read` output"
                     + (", and paste the checker's final coverage line verbatim." if checkers else "."))
        steps.append("Report: `done` only if every criterion is met (else `blocked` with the deviation and a recommended decision). Name the deliverable's path"
                     + (f" (the assistant copies it to {path})" if path else "")
                     + " and pass `lessons` as an after-action review: Expected / Happened / Caught at / Cause / Prevent (the system cause, not a person), "
                     "or Near miss when nothing went wrong.")
        budget_lines = [f"Request budget: {budget} runs (the contract's). Hand down no more than this up front, each with `budget=` set explicitly:"]
        for k in kids:
            e = est[k.addr]
            budget_lines.append(f"- {k.name}: {grant(k)} runs ({e['pass']} work + {e['rework']} rework or re-check" + (", plus its team" if k.children else "") + ")")
        own = est[owner.addr]["total"]
        keeps = split[owner.addr]["keeps"]
        budget_lines.append(f"- you ({owner.name}): keep {keeps} runs: your own {own} (plan, process each result, final check, report, one rework cycle)"
                            + (f" and {keeps - own} of slack" if keeps - own > 0 else "") + ".")
        budget_lines.append("Unspent runs return to your parent with your final report.")
        text = ("## Steps\n" + "\n".join(f"{i}. {x}" for i, x in enumerate(steps, 1))
                + "\n\n## Budget plan\n" + "\n".join(budget_lines))
        return text
