"""The public surface of ``eligibility``: whether an agent may run, and the one word that says what it is doing.

An agent is *paused* when its flag file ``<addr>/.paused`` exists (the reason is the text in it: ``budget`` and ``failures`` are the
runtime's, anything else a human's), it has *failed* as many times in a row as ``.runtime/failures.json`` counts, and its *state* is
derived, never stored: running, paused(reason), pending or idle. ``RunnableQuery`` combines those with the mail and the budget into the
one rule the scheduler, ``progress`` and the waiting-on-you analysis start agents by.
"""

from __future__ import annotations

from collections.abc import Collection
from typing import Protocol, runtime_checkable

__all__ = [
    "AgentStates",
    "FailureCounter",
    "PauseStore",
    "RunnableQuery",
]


@runtime_checkable
class PauseStore(Protocol):
    def paused(self, addr: str) -> str | None:
        """The reason the agent is paused (the text of its flag file, stripped; ``"paused"`` when the file is empty), or ``None`` when it is not."""
        ...

    def pause(self, addr: str, reason: str, by: str | None = None) -> None:
        """Write the flag file (the reason exactly as given) and emit ``agent.pause``. ``by`` names who did it in the event (default: the acting process)."""
        ...

    def resume(self, addr: str, reason: str = "", by: str | None = None) -> None:
        """Remove the flag file. Emits ``agent.resume`` (with ``previous``, the reason it was paused for) only if the agent was paused."""
        ...


@runtime_checkable
class FailureCounter(Protocol):
    def record(self, addr: str) -> int:
        """One more consecutive failed run of the agent (kept in ``.runtime/failures.json``, so it survives restarts); returns the count."""
        ...

    def clear(self, addr: str) -> None:
        """The agent's count starts again (the ledger is not written when it had none)."""
        ...

    def repair(self) -> bool:
        """Drop what is not a count (anything but a whole number) from the ledger, or the whole ledger when it is not a JSON object; ``True`` if
        the ledger changed. A ledger that cannot be parsed, or is not there, is left alone: it reads as empty."""
        ...


@runtime_checkable
class AgentStates(Protocol):
    def state(self, addr: str) -> str:
        """``"running"`` (a batch is in flight), else ``"paused(<reason>)"``, else ``"pending"`` (mail that wakes it waits), else ``"idle"``."""
        ...


@runtime_checkable
class RunnableQuery(Protocol):
    def runnable(self, exclude: Collection[str] = ()) -> list[str]:
        """The agents (parents before children) that have mail that wakes them and budget left and are not paused, ``exclude`` left out. A
        pause for ``budget`` does not count once budget is back. Whether an agent already runs is the caller's to say, in ``exclude``."""
        ...

    def startable(self, addr: str) -> bool:
        """Could a run of the agent be started now: mail that wakes it, budget above 0, and not paused for anything but ``budget``."""
        ...
