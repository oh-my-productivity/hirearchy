"""Whether an agent may run: pause, failures, state (eligibility).

Moved verbatim from ``core.Org`` in step M2 (ARCHITECTURE.md 5.3 and 6.4); a later step replaces the bodies by calls
to the interfaces of the package named above."""

from __future__ import annotations

from .. import telemetry


class EligibilityMixin:
    """Whether an agent may run: pause, failures, state (eligibility)."""

    def paused(self, addr: str) -> str | None:
        p = self.dir(addr) / ".paused"
        return (p.read_text(encoding="utf-8").strip() or "paused") if p.exists() else None

    def pause(self, addr: str, reason: str, by: str | None = None) -> None:
        """Pause an agent. ``by`` names who did it in the event (default: the acting process)."""
        (self.dir(addr) / ".paused").write_text(reason, encoding="utf-8")
        self.emit("agent.pause", actor=by, agent=addr, reason=telemetry.clip(reason, telemetry.ERROR_MAX))

    def resume(self, addr: str, reason: str = "", by: str | None = None) -> None:
        was = self.paused(addr)
        (self.dir(addr) / ".paused").unlink(missing_ok=True)
        if was is not None:
            self.emit("agent.resume", actor=by, agent=addr, reason=reason or "resumed", previous=telemetry.clip(was, 200))

    def record_failure(self, addr: str) -> int:
        """Count one more consecutive failed run (kept in .runtime/failures.json, so it survives restarts)."""
        counts = self.ledger("failures")
        counts[addr] = int(counts.get(addr, 0)) + 1
        self.save_ledger("failures", counts)
        return counts[addr]

    def clear_failures(self, addr: str) -> None:
        counts = self.ledger("failures")
        if counts.pop(addr, None) is not None:
            self.save_ledger("failures", counts)

    def state(self, addr: str) -> str:
        if self.running(addr):
            return "running"
        reason = self.paused(addr)
        if reason:
            return f"paused({reason})"
        return "pending" if self.unread(addr) else "idle"
