"""What root's free-form ``send`` (the ``Org`` facade's) may not send: a service task, a rework (P4, design 7.5)."""

from __future__ import annotations

from ..kernel import ROOT, OrgError, norm

FACADE_ROOT_TASK = (  # FACADE-ROOT-TASK
    "refused: a root task for a service, or a rework, goes through request(...) or delegate(...), which apply the case rules (the contract, the "
    "base, the verdicts). Nothing was sent."
)


def check_root_send(actor: str, type: str, service: str | None, revises: str | None, feedback: str | None, criterion: str | None) -> None:
    """Refuse, for root, a task that names a ``service`` or ``revises`` another (``request`` and ``delegate`` send those, after the rules of a case).
    Every other message passes: root's notes, budget grants and one-off tasks, and every message of an agent."""
    if norm(actor) != ROOT:
        return
    if type == "task" and (service or revises):
        raise OrgError(FACADE_ROOT_TASK)
