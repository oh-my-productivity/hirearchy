"""What root's free-form ``send`` (the ``Org`` facade's) may not send: a service task, a rework, a verdict, a link (P4, design 7.5)."""

from __future__ import annotations

from ..kernel import ROOT, OrgError, norm

FACADE_ROOT_TASK = (  # FACADE-ROOT-TASK
    "refused: a root task for a service, or a rework, goes through request(...) or delegate(...), which apply the case rules (the contract, the "
    "base, the verdicts). Nothing was sent."
)

FACADE_ROOT_VERDICT = (  # FACADE-ROOT-VERDICT
    "refused: a verdict or a link from root goes through feedback(...), which applies the rules of a case (a delivered request, one answer per "
    "rejection). Nothing was sent."
)


def check_root_send(actor: str, type: str, service: str | None, revises: str | None, feedback: str | None, criterion: str | None) -> None:
    """Refuse, for root, a task that names a ``service`` or ``revises`` another (``request`` and ``delegate`` send those, after the rules of a case) and a
    note that carries a ``feedback`` verdict or a ``criterion`` link (``feedback`` sends those). Every other message passes: root's notes, budget grants
    and one-off tasks, and every message of an agent (provenance refuses an agent's ``criterion``)."""
    if norm(actor) != ROOT:
        return
    if type == "task" and (service or revises):
        raise OrgError(FACADE_ROOT_TASK)
    if type == "note" and (feedback or criterion):
        raise OrgError(FACADE_ROOT_VERDICT)
