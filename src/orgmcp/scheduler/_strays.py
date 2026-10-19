"""Org files that a built-in ``write`` leaves in an agent's workspace."""

from __future__ import annotations

from ..strays import StrayProbe, StrayRegistry
from ._ports import Console, StrayWatch
from ._run import RunRecord


class StrayCheck(StrayWatch):
    """Looks before a run and after it; what is new is warned about in the run log and the output, and remembered so the agent's next prompt says so once."""

    def __init__(self, probe: StrayProbe, registry: StrayRegistry, console: Console) -> None:
        raise NotImplementedError("red: D-sched-1")

    def before(self, addr: str) -> dict[str, float]:
        raise NotImplementedError("red: D-sched-1")

    def after(self, run: RunRecord) -> None:
        raise NotImplementedError("red: D-sched-1")
