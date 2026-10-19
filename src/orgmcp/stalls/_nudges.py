"""``LedgerNudgeLedger``: the steps the ladder has taken, in ``.runtime/nudges.json`` (moved from ``scheduler._nudge_entries`` and ``scheduler._chain``)."""

from __future__ import annotations

from collections.abc import Mapping

from ..agents import AgentDirectory
from ..kernel import JsonObject, LedgerStore, Message, parent
from ._ports import LedgerShape, NudgeRecorder
from .api import NudgeLedger

LEDGER = "nudges"  # .runtime/nudges.json


def normalized(raw: object) -> dict[str, dict[str, float]]:
    """The entries of a ledger in the current shape; malformed entries (or a malformed ledger) are dropped."""
    out: dict[str, dict[str, float]] = {}
    for key, value in (raw.items() if isinstance(raw, dict) else ()):
        if isinstance(value, str):  # legacy ledger: "nudged" / "escalated"
            out[key] = {"step": 0 if value == "nudged" else 1, "at": 0}
        elif isinstance(value, dict):
            try:
                out[key] = {"step": max(0, int(value["step"])), "at": float(value.get("at") or 0)}
            except (KeyError, TypeError, ValueError):
                continue
    return out


def chain_of(agents: AgentDirectory, addr: str, task: Message) -> list[str]:
    """Who hears about a stalled task, in order: the assignee, its assigner, then up the tree to root."""
    chain = [addr]
    up = task.sender if agents.exists(task.sender) else parent(addr)
    while up:
        chain.append(up)
        up = parent(up)
    return chain


class LedgerNudgeLedger(NudgeLedger, NudgeRecorder):
    def __init__(self, ledgers: LedgerStore, shape: LedgerShape, agents: AgentDirectory) -> None:
        self._ledgers = ledgers
        self._shape = shape
        self._agents = agents

    def entries(self) -> dict[str, dict[str, float]]:
        return normalized(self._ledgers.read(LEDGER))

    def chain(self, addr: str, task: Message) -> list[str]:
        return chain_of(self._agents, addr, task)

    def save(self, entries: Mapping[str, Mapping[str, float]]) -> None:
        if self._shape.damaged(LEDGER) or entries != self._ledgers.read(LEDGER):
            data: JsonObject = {key: value for key, value in entries.items()}
            self._ledgers.write(LEDGER, data)
