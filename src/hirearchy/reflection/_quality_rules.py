"""The pure rules of the quality view: deliveries, who signed them off, the verdicts that are on none, the cases without a verdict (0b 3, 4.3, 4.4).

They read values (cases, messages), never files. ``reflection.api`` re-exports them from its end, because this module needs the types above them."""

from __future__ import annotations

from collections.abc import Collection, Mapping, Sequence

from ..kernel import Message
from .api import Case, Delivery


def signer_of(owner: str, task_id: str, done_id: str, owner_sent: Sequence[Message], owner_received: Sequence[Message], reports: Collection[str]) -> str:
    """The agent that signed off the delivery of ``task_id`` (pure; 0a 5.5, moved from ``health``): the sender of the latest ``done`` result that
    ``owner`` received from one of its direct ``reports``, answering a task ``owner`` sent after ``task_id`` and received before ``done_id`` (the id
    of the owner's own ``done``); ``owner`` itself when there is none."""
    later = {m.id for m in owner_sent if m.type == "task" and m.id > task_id}
    signed = [
        r for r in owner_received
        if r.type == "result" and r.status == "done" and r.sender in reports and r.reply_to in later and r.id < done_id
    ]
    return max(signed, key=lambda r: r.id).sender if signed else owner


def deliveries_of(case: Case, results: Mapping[str, Message], signers: Mapping[str, str]) -> tuple[Delivery, ...]:
    """The deliveries of ``case`` (pure), oldest first: its tasks whose latest result in ``results`` (task id to result, as the client received
    them) is ``done``. A verdict is on a delivery only when its note is newer than the delivery's result: one given on an earlier (blocked) result,
    or before the result arrived, is on none (``not_on_a_delivery``). ``signers`` maps a task id to its signer; the case's owner signs when
    the map has none."""
    out = []
    for step, t in enumerate(case.tasks):
        done = results.get(t.id)
        if done is None or done.status != "done":
            continue
        verdicts = tuple(v for v in case.verdicts if v.task_id == t.id and v.message.id > done.id)
        later = next((x.id for x in case.tasks if x.id > done.id), "")
        superseded = "" if any(v.tier == "human" for v in verdicts) else later
        out.append(Delivery(case.id, t, done, step, signers.get(t.id, case.owner), verdicts, superseded))
    return tuple(out)


def _given(case: Case, deliveries: Sequence[Delivery]) -> Delivery | None:
    """The delivery of ``case`` the user was given: the one flagged ``given``, else the latest (OQ-2)."""
    mine = [d for d in deliveries if d.case == case.id]
    return next((d for d in mine if d.given), mine[-1] if mine else None)


def unjudged_cases(cases: Sequence[Case], deliveries: Sequence[Delivery], *, relayed_only: bool = False) -> tuple[str, ...]:
    """The ids of the cases in state ``done`` whose given delivery has no human-tier verdict on it, counted or voided (pure; D18, OQ-2): defined by
    the ``Delivery`` alone, never by ``rated``, which counts any tier. With ``relayed_only``, only those whose given delivery has a relayed- or
    agent-tier verdict (the assistant or an agent judged it, the user did not)."""
    out = []
    for c in cases:
        d = _given(c, deliveries) if c.state == "done" else None
        if d is None or any(v.tier == "human" for v in d.verdicts):
            continue
        if not relayed_only or d.verdicts:
            out.append(c.id)
    return tuple(out)


def not_on_a_delivery(case: Case, deliveries: Sequence[Delivery]) -> tuple[Message, ...]:
    """The notes of the human-tier verdicts of ``case`` that are on no delivery (pure; D4): given on a blocked or failed result, on a task with no
    result, or before the ``done`` result arrived. Counted apart, never read as the verdict on a later delivery. Oldest first."""
    on_one = {v.message.id for d in deliveries for v in d.verdicts}
    return tuple(v.message for v in case.verdicts if v.tier == "human" and v.message.id not in on_one)
