"""``RuntimeNotices``: the one-time stray notice and the sections of a service owner (moved from ``Org.run_prompt``)."""

from __future__ import annotations

from collections.abc import Sequence

from ..kernel import Message
from ..reflection import ServicePromptSections
from ..strays import StrayRegistry
from ._ports import RunNotices, ServiceNames


class RuntimeNotices(RunNotices):
    def __init__(self, strays: StrayRegistry, services: ServiceNames, sections: ServicePromptSections) -> None:
        self._strays = strays
        self._services = services
        self._sections = sections

    def notices(self, addr: str, batch: Sequence[Message]) -> str:
        raise NotImplementedError("red: C-prompts")
