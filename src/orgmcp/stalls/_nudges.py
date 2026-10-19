"""``LedgerNudgeLedger``: the steps the ladder has taken, in ``.runtime/nudges.json`` (moved from ``scheduler._nudge_entries`` and ``scheduler._chain``)."""

from __future__ import annotations

from collections.abc import Mapping

from ..agents import AgentDirectory
from ..kernel import LedgerStore, Message
from ._ports import LedgerShape, NudgeRecorder
from .api import NudgeLedger

LEDGER = "nudges"  # .runtime/nudges.json


def normalized(raw: object) -> dict[str, dict[str, float]]:
    """The entries of a ledger in the current shape; malformed entries (or a malformed ledger) are dropped."""
    raise NotImplementedError("red: C-stalls")


def chain_of(agents: AgentDirectory, addr: str, task: Message) -> list[str]:
    """Who hears about a stalled task, in order: the assignee, its assigner, then up the tree to root."""
    raise NotImplementedError("red: C-stalls")


class LedgerNudgeLedger(NudgeLedger, NudgeRecorder):
    def __init__(self, ledgers: LedgerStore, shape: LedgerShape, agents: AgentDirectory) -> None:
        self._ledgers = ledgers
        self._shape = shape
        self._agents = agents

    def entries(self) -> dict[str, dict[str, float]]:
        raise NotImplementedError("red: C-stalls")

    def chain(self, addr: str, task: Message) -> list[str]:
        raise NotImplementedError("red: C-stalls")

    def save(self, entries: Mapping[str, Mapping[str, float]]) -> None:
        raise NotImplementedError("red: C-stalls")
