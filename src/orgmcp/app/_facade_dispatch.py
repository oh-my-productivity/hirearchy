# mypy: ignore-errors
"""The protocol rules for every message an agent sends (dispatch).

Moved verbatim from ``core.Org`` in step M2 (ARCHITECTURE.md 5.3 and 6.4); a later step replaces the bodies by calls
to the interfaces of the package named above."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from .. import templates
from ..kernel import (
    inside as _inside,
    latest_results,
    Message,
    MESSAGE_TYPES,
    OrgError,
    RESULT_STATUSES,
    ROOT,
    RUNTIME,
    word_count,
)
from ._facade_settings import _message_cap


LESSONS_MAX_CHARS = 800  # longest `lessons` text a report on a service request may carry


class DispatchMixin:
    """The protocol rules for every message an agent sends (dispatch)."""

    def can_message(self, sender: str, to: str, reply_to: str | None = None) -> bool:
        if sender in (ROOT, RUNTIME):
            return True  # the human and the runtime may address anyone
        if to == sender:
            return False
        if to == self.parent(sender) or self.parent(to) == sender or self.parent(to) == self.parent(sender):
            return True
        if reply_to:  # anyone may answer a message they received
            original = self.find_received(sender, reply_to)
            return original is not None and original.sender == to
        return False

    def _next_hops(self, actor: str) -> int:
        if actor in (ROOT, RUNTIME):
            return 0
        return max((m.hops for m in self.messages(actor, "inflight")), default=0) + 1

    def send(
        self,
        actor: str,
        to: str,
        body: str,
        *,
        type: str = "note",
        title: str = "",
        reply_to: str | None = None,
        status: str | None = None,
        budget: int = 0,
        revises: str | None = None,
        supersedes: str | None = None,
        service: str | None = None,
        contract: int | None = None,
        playbook: int | None = None,
        feedback: str | None = None,
        wake: bool = True,
        _skip_route_check: bool = False,
    ) -> Message:
        cap = _message_cap(self.config)
        if len(body.strip()) > cap and self.norm(actor) != ROOT:  # the cap protects agents' runs; the human may paste
            raise OrgError(
                f"message is {len(body.strip())} characters; the limit is {cap} (max_message_chars). Messages are "
                "read in full by the recipient's next run, so keep them short: write the detail to a file inside "
                "your own directory and send a short message that gives its path."
            )
        actor, to = self.require(actor), self.require(to)
        if type not in MESSAGE_TYPES:
            raise OrgError(f"type must be one of {MESSAGE_TYPES}")
        if not body.strip():
            raise OrgError("message body is empty")
        if not _skip_route_check and not self.can_message(actor, to, reply_to):
            raise OrgError(
                f"{actor} cannot message {to}: you may message your parent, your direct reports, "
                "your siblings, or whoever sent you the message you are replying to (reply_to)."
            )
        budget = int(budget or 0)
        if budget < 0:
            raise OrgError("budget cannot be negative")
        if budget and actor != ROOT and self.parent(to) != actor and to != self.parent(actor):
            raise OrgError("budget can only be handed to your direct reports, or returned to your parent")
        self._check_allocation(actor, budget, new_delegation=type == "task")
        hops = self._next_hops(actor)
        if type != "result" and hops > int(self.config["max_hops"]):  # reports always get through
            raise OrgError(
                f"message chain is {hops} hops long (limit {self.config['max_hops']}); this looks like a loop. "
                "Report blocked to whoever assigned your task instead."
            )
        msg = Message(
            sender=actor, to=to, type=type, body=body.strip(), title=title.strip(),
            reply_to=reply_to, status=status, budget=budget, hops=hops, revises=revises,
            supersedes=supersedes, service=service, contract=contract, playbook=playbook, feedback=feedback,
            wake=wake,
        )
        return self.deliver(msg)

    def delegate(
        self,
        actor: str,
        to: str,
        title: str,
        goal: str,
        acceptance: str,
        inputs: list[str] | None = None,
        budget: int | None = None,
        revises: str | None = None,
    ) -> Message:
        actor, to = self.require(actor), self.require(to)
        if actor != ROOT and self.parent(to) != actor:
            reports = ", ".join(self.children(actor)) or "none (hire one first)"
            raise OrgError(f"you can only delegate to your direct reports: {reports}")
        if not title.strip() or not goal.strip() or not acceptance.strip():
            raise OrgError("a task needs a title, a goal and acceptance criteria")
        if budget is None:
            budget = self._default_budget(actor)
        budget = int(budget)
        if budget < 1:
            raise OrgError("a task needs a budget of at least 1 run")
        if revises and not any(m.id == revises and m.type == "task" and m.to == to for m in self.sent(actor)):
            raise OrgError(f"revises must be the id of an earlier task you sent to {to}: {revises}")
        body = templates.task_body(goal, acceptance, list(inputs or []))
        fields: dict = {}
        if revises:  # rework of a service request is still part of its case
            from .. import services

            fields = services.rework_fields(self, actor, revises)
        return self.send(actor, to, body, type="task", title=title, budget=budget, revises=revises or None, **fields)

    def _normalize_artifact(self, actor: str, path: str, since: str = "") -> str:
        """Resolve an artifact path and annotate it with facts a manager can check claims against.

        Inside the organization (paths relative to the org root, or absolute) or, as an absolute path, inside the
        reporter's own workspace. Anything else is refused before existence is checked: no probing of the host.
        """
        p = Path(path).expanduser()
        ws = self.workspace_of(actor)
        if not p.is_absolute():
            p = next((b / p for b in (self.root, self.dir(actor)) if (b / p).exists()), self.root / p)
        p = p.resolve()
        in_org = p == self.root or self.root in p.parents
        if not in_org and not (ws is not None and _inside(p, ws)):
            where = f"inside your workspace ({ws})" if ws is not None else "(you have no workspace)"
            raise OrgError(
                f"artifacts must be inside the organization (paths relative to the org root) or, by absolute path, "
                f"{where}: {path}"
            )
        if not p.exists():
            hint = ""
            if ws is not None and not Path(path).expanduser().is_absolute() and (ws / path).exists():
                hint = f" It exists in your workspace: report it by absolute path ({(ws / path).resolve()})."
            raise OrgError(f"artifact not found: {path} (relative paths are relative to the org root).{hint}")
        shown = str(p.relative_to(self.root)) if in_org else str(p)
        if p.is_dir():
            return f"{shown}/ (directory)"
        modified = datetime.fromtimestamp(p.stat().st_mtime, timezone.utc)
        note = f"{word_count(p.read_text(encoding='utf-8', errors='replace'))} words, modified {modified:%H:%M:%S} UTC"
        if since and modified.isoformat(timespec="seconds") < since:
            note += ", NOT modified since this task was assigned"
        return f"{shown} ({note})"

    def report(
        self,
        actor: str,
        task_id: str,
        status: str,
        summary: str,
        artifacts: list[str] | None = None,
        lessons: str | None = None,
    ) -> Message:
        actor = self.require(actor)
        if status not in RESULT_STATUSES:
            raise OrgError(f"status must be one of {RESULT_STATUSES}")
        task = self.find_received(actor, task_id)
        if task is None or task.type != "task":
            open_ids = ", ".join(t.id for t in self.open_tasks(actor)) or "none"
            raise OrgError(f"no task {task_id} assigned to you. Your open tasks: {open_ids}")
        prior = latest_results(self.sent(actor)).get(task_id)
        if prior is not None and prior.status != "blocked":
            raise OrgError(
                f"task {task_id} was already reported {prior.status}, and {prior.status} is final (rule 6): it cannot be "
                "reported again or changed by a note. Only a task reported `blocked` can be reported again. If you have "
                "information for whoever assigned it, use `send`, as information only: a note does not change the "
                "task's outcome and must not claim that criteria are met."
            )
        lessons = self._check_lessons(task, status, lessons)
        arts = [self._normalize_artifact(actor, a, task.created) for a in (artifacts or [])]
        body = templates.result_body(summary, arts, lessons)
        return self.send(
            actor, task.sender, body, type="result", title=task.title,
            reply_to=task.id, status=status, supersedes=prior.id if prior else None, _skip_route_check=True,
            budget=self._budget_to_return(actor, task, status),
        )

    @staticmethod
    def _check_lessons(task: Message, status: str, lessons: str | None) -> str:
        """The lessons text for a report: required on a service request (done, failed or blocked), 1..800 characters."""
        text = (lessons or "").strip()
        if task.service and status in ("done", "failed", "blocked") and not text:
            raise OrgError(
                f"task {task.id} is a request for service `{task.service}`: pass `lessons` - 1-3 lines for the next "
                "request: what worked, what to change in the playbook, and the evidence (runs, rework, review "
                "findings). Required for done, failed and blocked alike: a blocker is the most informative case, so "
                "say what went wrong and what would have prevented it"
            )
        if len(text) > LESSONS_MAX_CHARS:
            raise OrgError(
                f"lessons are {len(text)} characters; the limit is {LESSONS_MAX_CHARS}. Keep 1-3 lines: what worked, "
                "what to change in the playbook, and the evidence; put detail in a file under your work/ directory."
            )
        return text
