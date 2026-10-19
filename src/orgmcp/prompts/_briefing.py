"""The part of a run prompt that does not depend on the run: the memory with its cap notice, and the rules, charter and memory together (moved from ``Org.run_prompt``)."""

from __future__ import annotations

from typing import cast

from ..agents import CharterReader
from ..settings import OrgSettings
from ._ports import Briefing, MemoryText


class CappedMemory(MemoryText):
    def __init__(self, charters: CharterReader, settings: OrgSettings) -> None:
        self._charters = charters
        self._settings = settings

    def memory_text(self, addr: str) -> str:
        memory = self._charters.memory(addr).strip() or "(empty: this may be your first run)"
        cap, words = int(cast("int | str", self._settings.config()["memory_max_words"])), len(memory.split())
        if words > cap:
            memory += (
                f"\n\n**Your memory is {words} words, over the {cap}-word limit, and writes that keep it over "
                f"the limit are refused. This run, condense it: rewrite {addr}/MEMORY.md (not append) with only what "
                "your next run needs; move detail into files under your work/ directory.**"
            )
        return memory


class PromptBriefing(Briefing):
    def __init__(self, settings: OrgSettings, charters: CharterReader, memory: MemoryText) -> None:
        self._settings = settings
        self._charters = charters
        self._memory = memory

    def briefing(self, addr: str) -> str:
        _, charter = self._charters.charter(addr)
        memory = self._memory.memory_text(addr)
        return (
            f"{self._settings.rules()}\n\n# Your charter ({addr}/AGENT.md, owned by your parent)\n{charter}\n\n"
            f"# Your memory ({addr}/MEMORY.md)\n{memory}"
        )
