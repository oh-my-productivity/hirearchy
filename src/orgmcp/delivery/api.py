"""The public surface of ``delivery``: the one complete-then-store pipeline for every message.

Every message of the organization (a task, a result, a note of the human or of an agent, a notice of the runtime) is delivered through
``MessageDelivery``; the rules that decide whether it may be sent at all are the callers' (``dispatch``, ``hierarchy``, ``budget``).
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from ..kernel import Message

__all__ = [
    "MessageDelivery",
]


@runtime_checkable
class MessageDelivery(Protocol):
    def deliver(self, msg: Message) -> Message:
        """Complete ``msg`` in place and store it; returns ``msg``. In this order (a contract): the ``id`` and ``created`` it does not have
        yet; the trace stamp (an exception while stamping is not worth a message: the rule is then ``error`` and the trace stays unset);
        the sender's ``sent/`` copy, then the recipient's ``inbox/`` copy (the runtime has no sent copy); the trace noted on the running
        tool call; the ``msg.deliver`` event. A failed write raises: nothing after it happens, and the sent copy that may already be
        there is finished by ``BatchStore.recover``."""
        ...

    def notify(self, to: str, title: str, body: str, wake: bool = True, trace: str | None = None) -> Message:
        """Deliver a note from the runtime itself (budget, failures, stalls) to ``to``. ``wake=False`` holds it in the inbox until the
        agent's next real run; ``trace`` is the request the notice is about, when known."""
        ...
