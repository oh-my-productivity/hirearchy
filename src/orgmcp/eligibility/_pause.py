"""``FsPauseStore``: the flag file ``<addr>/.paused``."""

from __future__ import annotations

from ..kernel import EventSink, OrgLayout
from .api import PauseStore


class FsPauseStore(PauseStore):
    def __init__(self, paths: OrgLayout, events: EventSink) -> None:
        raise NotImplementedError("red: B-eligibility")

    def paused(self, addr: str) -> str | None:
        raise NotImplementedError("red: B-eligibility")

    def pause(self, addr: str, reason: str, by: str | None = None) -> None:
        raise NotImplementedError("red: B-eligibility")

    def resume(self, addr: str, reason: str = "", by: str | None = None) -> None:
        raise NotImplementedError("red: B-eligibility")
