"""Org files that a built-in ``write`` leaves in an agent's workspace."""

from __future__ import annotations

from ..runs import log_note
from ..strays import StrayProbe, StrayRegistry
from ._ports import Console, StrayWatch
from ._run import RunRecord


class StrayCheck(StrayWatch):
    """Looks before a run and after it; what is new is warned about in the run log and the output, and remembered so the agent's next prompt says so once."""

    def __init__(self, probe: StrayProbe, registry: StrayRegistry, console: Console) -> None:
        self._probe, self._registry, self._console = probe, registry, console

    def before(self, addr: str) -> dict[str, float]:
        return self._probe.probe(addr)

    def after(self, run: RunRecord) -> None:
        if run.strays is None:
            return
        found = self._probe.found_since(run.strays, self._probe.probe(run.addr))
        if not found:
            return
        rel = ", ".join(found[:5])
        run.logf.write(log_note(f"warning: {run.addr} created org files in its workspace with the built-in `write` "
                                f"(not in the org, so they are not its memory): {rel}"))
        self._console.say(f"{run.addr}: warning: org files in its workspace (built-in write shadows hirearchy write?): {rel}")
        self._registry.record(run.addr, found)  # told once per agent: later strays are only logged
