"""The sender the ``Org`` facade hands out: ``check_root_send``, then the sender it guards."""

from __future__ import annotations

from ..kernel import Message
from ._root_send import check_root_send
from .api import GuardedSender, MessageSender


class GuardedRootSender(GuardedSender):
    """Refuses what ``check_root_send`` refuses and sends every other message through ``inner`` with every argument unchanged. The rule classes
    (``RuleServiceRequester``, ``RuleTaskAssigner``, ``RuleClientFeedback``) hold ``inner`` itself: they apply their own rules to the same shapes."""

    def __init__(self, inner: MessageSender) -> None:
        self._inner = inner

    def send(
        self, actor: str, to: str, body: str, *, type: str = "note", title: str = "", reply_to: str | None = None,
        status: str | None = None, budget: int = 0, revises: str | None = None, supersedes: str | None = None,
        service: str | None = None, contract: int | None = None, playbook: int | None = None, feedback: str | None = None,
        source: str | None = None, criterion: str | None = None, wake: bool = True, skip_route_check: bool = False,
        inherited: str | None = None, acknowledges: str | None = None,
    ) -> Message:
        check_root_send(actor, type, service, revises, feedback, criterion, acknowledges)
        return self._inner.send(
            actor, to, body, type=type, title=title, reply_to=reply_to, status=status, budget=budget, revises=revises, supersedes=supersedes,
            service=service, contract=contract, playbook=playbook, feedback=feedback, source=source, criterion=criterion, wake=wake,
            skip_route_check=skip_route_check, inherited=inherited, acknowledges=acknowledges,
        )
