"""The protocol rules for every message an agent sends (dispatch).

The bodies call the ports of ``self.runtime`` (step B-dispatch; ARCHITECTURE.md 5.3 and 6.4). ``send``, ``delegate`` and ``report`` are the ports
``message_sender``, ``task_assigner`` and ``task_reporter``. ``can_message``, ``_next_hops``, ``_normalize_artifact`` and ``_check_lessons`` are the
old spellings of the rules the commands are made of (nothing calls them any more; the signature guard keeps them): the ports ``route_policy``,
``hop_counter`` and ``artifact_normalizer``, and the function ``check_lessons`` (static, as it always was). ``LESSONS_MAX_CHARS`` is re-exported under
its old name for ``hirearchy.core``."""

from __future__ import annotations

from ..dispatch import LESSONS_MAX_CHARS, check_lessons
from ..kernel import Message
from .runtime import OrgRuntime

__all__ = ["DispatchMixin", "LESSONS_MAX_CHARS"]


class DispatchMixin:
    """The protocol rules for every message an agent sends (dispatch)."""

    runtime: OrgRuntime

    def can_message(self, sender: str, to: str, reply_to: str | None = None) -> bool:
        return self.runtime.route_policy.can_message(sender, to, reply_to)

    def _next_hops(self, actor: str) -> int:
        return self.runtime.hop_counter.next_hops(actor)

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
        source: str | None = None,
        criterion: str | None = None,
        wake: bool = True,
        _skip_route_check: bool = False,
    ) -> Message:
        return self.runtime.facade_sender.send(
            actor, to, body, type=type, title=title, reply_to=reply_to, status=status, budget=budget, revises=revises,
            supersedes=supersedes, service=service, contract=contract, playbook=playbook, feedback=feedback, source=source,
            criterion=criterion, wake=wake, skip_route_check=_skip_route_check,
        )

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
        source: str | None = None,
    ) -> Message:
        return self.runtime.task_assigner.delegate(actor, to, title, goal, acceptance, inputs, budget, revises, source)

    def _normalize_artifact(self, actor: str, path: str, since: str = "") -> str:
        """Resolve an artifact path and annotate it with facts a manager can check claims against.

        Inside the organization (paths relative to the org root, or absolute) or, as an absolute path, inside the
        reporter's own workspace. Anything else is refused before existence is checked: no probing of the host.
        """
        return self.runtime.artifact_normalizer.normalize(actor, path, since)

    def report(
        self,
        actor: str,
        task_id: str,
        status: str,
        summary: str,
        artifacts: list[str] | None = None,
        lessons: str | None = None,
    ) -> Message:
        return self.runtime.task_reporter.report(actor, task_id, status, summary, artifacts, lessons)

    @staticmethod
    def _check_lessons(task: Message, status: str, lessons: str | None) -> str:
        """The lessons text for a report: required on a service request (done, failed or blocked), 1..800 characters.

        Static, as it always was: the rule needs no collaborator."""
        return check_lessons(task, status, lessons)
