"""Whether an agent may run: pause, failures, state (eligibility).

The bodies call the ports of ``self.runtime`` (step B-eligibility; ARCHITECTURE.md 5.3 and 6.4)."""

from __future__ import annotations

from .runtime import OrgRuntime


class EligibilityMixin:
    """Whether an agent may run: pause, failures, state (eligibility)."""

    runtime: OrgRuntime

    def paused(self, addr: str) -> str | None:
        return self.runtime.pause_store.paused(addr)

    def pause(self, addr: str, reason: str, by: str | None = None) -> None:
        """Pause an agent. ``by`` names who did it in the event (default: the acting process)."""
        self.runtime.pause_store.pause(addr, reason, by)

    def resume(self, addr: str, reason: str = "", by: str | None = None) -> None:
        self.runtime.pause_store.resume(addr, reason, by)

    def record_failure(self, addr: str) -> int:
        """Count one more consecutive failed run (kept in .runtime/failures.json, so it survives restarts)."""
        return self.runtime.failure_counter.record(addr)

    def clear_failures(self, addr: str) -> None:
        self.runtime.failure_counter.clear(addr)

    def state(self, addr: str) -> str:
        return self.runtime.agent_states.state(addr)
