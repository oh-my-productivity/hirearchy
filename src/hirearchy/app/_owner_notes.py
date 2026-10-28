"""The note an agent gets from the runtime when a verifier joins its team (design 5.5 step 9)."""

from __future__ import annotations

from ..blueprint._protocols import OwnerNotes
from ..delivery import MessageDelivery


class RuntimeOwnerNotes(OwnerNotes):
    """A note from the runtime itself, delivered to the agent's inbox; it wakes the agent."""

    def __init__(self, delivery: MessageDelivery) -> None:
        self._delivery = delivery

    def tell(self, to: str, title: str, body: str) -> None:
        self._delivery.notify(to, title, body, wake=True)
