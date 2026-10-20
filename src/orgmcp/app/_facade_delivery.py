"""The one complete-then-store pipeline for every message (delivery).

The bodies call the ports of ``self.runtime`` (step B-delivery; ARCHITECTURE.md 5.3 and 6.4)."""

from __future__ import annotations

from ..kernel import Message
from .runtime import OrgRuntime


class DeliveryMixin:
    """The one complete-then-store pipeline for every message (delivery)."""

    runtime: OrgRuntime

    def deliver(self, msg: Message) -> Message:
        """Low level: assign an id, stamp the trace and write the message. Policy is checked by the callers."""
        return self.runtime.delivery.deliver(msg)

    def notify(self, to: str, title: str, body: str, wake: bool = True, trace: str | None = None) -> Message:
        """A notice from the runtime itself (budget, failures, stalls). ``wake=False``: see :meth:`unread`.
        ``trace``: the request the notice is about, when known."""
        return self.runtime.delivery.notify(to, title, body, wake, trace)
