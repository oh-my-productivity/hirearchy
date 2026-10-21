"""``FsPauseStore``: the flag file ``<addr>/.paused``."""

from __future__ import annotations

from ..kernel import EventSink, OrgLayout, clip
from .api import PauseStore

REASON_MAX = 500  # the longest reason the ``agent.pause`` event carries (a cut one ends in an ellipsis)
PREVIOUS_MAX = 200  # the longest ``previous`` reason the ``agent.resume`` event carries


class FsPauseStore(PauseStore):
    def __init__(self, paths: OrgLayout, events: EventSink) -> None:
        self._paths = paths
        self._events = events

    def paused(self, addr: str) -> str | None:
        p = self._paths.agent_dir(addr) / ".paused"
        return (p.read_text(encoding="utf-8").strip() or "paused") if p.exists() else None

    def pause(self, addr: str, reason: str, by: str | None = None) -> None:
        (self._paths.agent_dir(addr) / ".paused").write_text(reason, encoding="utf-8")
        self._events.emit("agent.pause", actor=by, agent=addr, reason=clip(reason, REASON_MAX))

    def resume(self, addr: str, reason: str = "", by: str | None = None) -> None:
        was = self.paused(addr)
        (self._paths.agent_dir(addr) / ".paused").unlink(missing_ok=True)
        if was is not None:
            self._events.emit("agent.resume", actor=by, agent=addr, reason=reason or "resumed", previous=clip(was, PREVIOUS_MAX))
