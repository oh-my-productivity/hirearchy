"""The part of a run prompt that does not depend on the run: the memory with its cap notice, and the rules, charter and memory together (moved from ``Org.run_prompt``)."""

from __future__ import annotations

from ..agents import CharterReader
from ..settings import OrgSettings
from ._ports import Briefing, MemoryText


class CappedMemory(MemoryText):
    def __init__(self, charters: CharterReader, settings: OrgSettings) -> None:
        self._charters = charters
        self._settings = settings

    def memory_text(self, addr: str) -> str:
        raise NotImplementedError("red: C-prompts")


class PromptBriefing(Briefing):
    def __init__(self, settings: OrgSettings, charters: CharterReader, memory: MemoryText) -> None:
        self._settings = settings
        self._charters = charters
        self._memory = memory

    def briefing(self, addr: str) -> str:
        raise NotImplementedError("red: C-prompts")
