"""The narrow ports ``review`` composes its reviewer from (private: they are not a surface of the package, ARCHITECTURE.md 3.26)."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol, runtime_checkable

from .api import Note, Review


@dataclass(frozen=True)
class LedgerRecord:
    """What ``.runtime/reviews.json`` says, normalised."""

    at: object  # when the last review ran, as the file has it (an ISO time; anything else is unreadable and counts as no time)
    runs: int  # the organization-wide run count then
    notified: dict[str, list[str]]  # recipient -> "agent:flag" pairs it knows about


@runtime_checkable
class ReviewLedger(Protocol):
    """``.runtime/reviews.json``: when the last review ran, the run count then, and who was told about what."""

    def read(self) -> LedgerRecord | None:
        """The ledger (a ``runs`` that is not an int counts as 0, a ``notified`` entry that is not a list is dropped); ``None`` when it is
        missing, empty or not an object."""
        ...

    def save(self, at: datetime, runs: int, notified: Mapping[str, list[str]]) -> None:
        """Replace the ledger (``at`` in UTC seconds, ISO)."""
        ...


@runtime_checkable
class RunTotal(Protocol):
    def total(self) -> int:
        """Runs ever used: the run logs of every agent plus those inside the retired trees."""
        ...


@runtime_checkable
class ReserveCheck(Protocol):
    def why_not(self, manager: str) -> str:
        """Why a note must not be sent to this manager (``""``: it may be). A note costs a run; the runs a manager holds in reserve (one per
        outstanding delegation, to process the result) are not for review notes."""
        ...


@runtime_checkable
class ReviewPlanner(Protocol):
    def plan(self, now: datetime, previous: Mapping[str, list[str]]) -> Review:
        """What a review at ``now`` would send and record, given who was told about what in the previous one. Changes nothing."""
        ...


@runtime_checkable
class ReviewCadence(Protocol):
    def due(self, now: datetime) -> bool:
        """Is a review due at ``now``? With no usable ledger the clock starts now (the ledger is created) and the answer is no; a run count that
        went down rebases the ledger on the count seen."""
        ...


@runtime_checkable
class NoteOutbox(Protocol):
    def deliver(self, notes: Sequence[Note]) -> None:
        """Write each note to its recipient, in order (a note wakes its recipient and costs it a run)."""
        ...
