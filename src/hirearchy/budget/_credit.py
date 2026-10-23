"""The run credit: the note with which the runtime returns a run it does not charge."""

from __future__ import annotations

from ..kernel import RUNTIME, Message, run_credit_title


def run_credit(addr: str, stem: str) -> Message:
    """The note from the runtime to ``addr`` that returns the run whose log is ``<stem>.log`` (budget is derived: received runs are credits).

    It carries one run, does not wake ``addr``, and is delivered like any other note."""
    return Message(
        sender=RUNTIME, to=addr, type="note", budget=1, wake=False, title=run_credit_title(addr, stem),
        body=f"Your run {addr}@{stem} ended on a model-service throttle (retryErrorType THROTTLING) before any tool effect, so it is not "
             "charged: this note returns its run. Your messages are back in your inbox; the run is started again.",
    )
