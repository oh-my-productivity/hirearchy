"""The one state of an agent, in words."""

from __future__ import annotations

from dataclasses import dataclass

from ..kernel import fmt_dur
from ._text import pause_text


@dataclass(frozen=True)
class AgentState:
    """The one state of an agent, in words. ``main`` + ``note`` is the whole text (``word``); the tree may shorten
    ``main`` to fit and always keeps ``note`` (the mail waiting)."""

    kind: str  # one of STATE_KINDS
    main: str
    note: str = ""
    reason: str = ""  # why mail waits (running: for the next run; queued: why it does not run yet)
    short: str = ""  # ``main`` in fewer characters, for a narrow tree (empty: no shorter form)

    @property
    def word(self) -> str:
        return self.main + self.note


def classify(*, running: bool, unread: int, paused: str | None, budget: int, open_tasks: int, delegated: int,
             scheduler_up: bool, free_slots: int, max_parallel: int, elapsed_s: float | None = None) -> AgentState:
    """The state of one agent. Exactly one applies, in this precedence (an agent is never two of them):

    1. running - a run is in flight (mail that arrived meanwhile waits for the next run; a pause is noted);
    2. paused - ``paused: <reason>`` (+ ``N unread``): a paused agent is not started, whatever else is true;
    3. out of budget - no runs left (``out of budget`` + ``N unread``): it is not started either;
    4. queued - it has mail, may run, and has not started yet - the reason says why: the scheduler is not running,
       all ``max_parallel`` slots are busy, or it starts on the next tick;
    5. waiting on its reports / working on tasks / idle.

    A ``budget`` pause with budget granted since is no pause (the scheduler starts such an agent)."""
    pause = paused if (paused and not (paused == "budget" and budget > 0)) else None
    if running:
        main = "running" + (f" {fmt_dur(elapsed_s * 1000)}" if elapsed_s is not None else "")
        if not scheduler_up:
            main += " (scheduler not running)"
        notes = []
        reason = ""
        if unread:
            notes.append(f"+{unread} unread")
            reason = "its current run is still going; the next run starts after it"
        if pause:
            notes.append("then out of budget" if pause == "budget" else "then " + pause_text(pause))
        return AgentState("running", main, "".join(f", {n}" for n in notes), reason)
    if pause and pause != "budget":
        return AgentState("paused", pause_text(pause), f", {unread} unread" if unread else "")
    if pause == "budget" or (budget <= 0 and (unread or open_tasks or delegated)):
        return AgentState("budget", "out of budget", f", {unread} unread" if unread else "")
    if unread:
        if not scheduler_up:
            reason, short = "scheduler is not running", "scheduler off"
        elif free_slots <= 0:
            reason, short = f"max_parallel ({max_parallel}) runs are busy", "all slots busy"
        else:
            reason, short = "ready: starts on the next tick", "next tick"  # the reason has the wording of observe.now_view
        return AgentState("queued", f"queued: {reason.removeprefix('ready: ')}", f", {unread} unread", reason, f"queued: {short}")
    if delegated:
        return AgentState("waiting", f"waiting on {delegated} report(s)")
    if open_tasks:
        return AgentState("working", f"working on {open_tasks} task(s)")
    return AgentState("idle", "idle")
