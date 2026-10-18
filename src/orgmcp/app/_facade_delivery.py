"""The one complete-then-store pipeline for every message (delivery).

Moved verbatim from ``core.Org`` in step M2 (ARCHITECTURE.md 5.3 and 6.4); a later step replaces the bodies by calls
to the interfaces of the package named above."""

from __future__ import annotations

from .. import telemetry
from ..kernel import Message, RUNTIME
from ._compat import atomic_write, utcnow


class DeliveryMixin:
    """The one complete-then-store pipeline for every message (delivery)."""

    def deliver(self, msg: Message) -> Message:
        """Low level: assign an id, stamp the trace and write the message. Policy is checked by the callers."""
        msg.id = msg.id or self.new_id(msg.sender)
        msg.created = msg.created or utcnow().isoformat(timespec="seconds")
        try:
            rule, candidates = self.stamp_trace(msg)
        except Exception:  # noqa: BLE001 - a trace is bookkeeping: never worth failing a message for
            rule, candidates = "error", []
        text = msg.to_text()
        # Sender's copy first: it is what charges a budget grant. A failure between the two writes can then only
        # leave a message charged but undelivered (recover() re-delivers it), never delivered but uncharged.
        if msg.sender != RUNTIME:
            atomic_write(self.dir(msg.sender) / "sent" / f"{msg.id}.md", text)
        atomic_write(self.dir(msg.to) / "inbox" / f"{msg.id}.md", text)
        telemetry.note_trace(msg.trace)
        extra = {"trace_candidates": candidates} if candidates else {}
        self.emit(
            "msg.deliver", actor=msg.sender, trace=msg.trace, id=msg.id, type=msg.type, **{"from": msg.sender},
            to=msg.to, title=telemetry.clip(msg.title), status=msg.status, budget=msg.budget, reply_to=msg.reply_to,
            revises=msg.revises, supersedes=msg.supersedes, service=msg.service, feedback=msg.feedback,
            wake=msg.wake, hops=msg.hops, chars=len(msg.body), trace_rule=rule, **extra,
        )
        return msg

    def notify(self, to: str, title: str, body: str, wake: bool = True, trace: str | None = None) -> Message:
        """A notice from the runtime itself (budget, failures, stalls). ``wake=False``: see :meth:`unread`.
        ``trace``: the request the notice is about, when known."""
        return self.deliver(Message(
            sender=RUNTIME, to=self.norm(to), type="note", title=title, body=body, wake=wake, trace=trace or None,
        ))
