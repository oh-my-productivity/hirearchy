"""The ports ``stalls`` defines for what it consumes or hands to its own classes (consumer-owned, narrower than the provider's)."""

from __future__ import annotations

from collections.abc import Collection, Mapping
from typing import Protocol, runtime_checkable

from ..kernel import Message, OrgLayout


@runtime_checkable
class TaskViews(Protocol):
    def open_tasks(self, addr: str) -> list[Message]:
        """The tasks ``addr`` received that it has not answered, recomputed only when its set of message files changes."""
        ...

    def outstanding(self, addr: str) -> list[Message]:
        """The tasks ``addr`` sent that have not been answered, recomputed only when its set of message files changes."""
        ...

    def retain(self, agents: Collection[str]) -> None:
        """Forget what is remembered of every agent that is not in ``agents``."""
        ...


@runtime_checkable
class NudgeRecorder(Protocol):
    def save(self, entries: Mapping[str, Mapping[str, float]]) -> None:
        """Make ``entries`` the ledger; nothing is written when the ledger already holds exactly that (a damaged one, JSON that is not an object,
        is replaced)."""
        ...


@runtime_checkable
class CreationTimes(Protocol):
    def of(self, task: Message) -> float:
        """When the task was created, in epoch seconds: its ``created`` stamp, else (it does not read) the modification time of its file."""
        ...


@runtime_checkable
class LedgerShape(Protocol):
    def damaged(self, name: str) -> bool:
        """The ledger file holds JSON that is not an object (``LedgerStore.read`` shows such a ledger as empty, hiding the damage)."""
        ...


class FsCreationTimes(CreationTimes):
    def of(self, task: Message) -> float:
        raise NotImplementedError("red: C-stalls")


class FsLedgerShape(LedgerShape):
    def __init__(self, paths: OrgLayout) -> None:
        self._paths = paths

    def damaged(self, name: str) -> bool:
        raise NotImplementedError("red: C-stalls")

