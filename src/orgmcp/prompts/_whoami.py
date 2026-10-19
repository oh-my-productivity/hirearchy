"""``TextWhoami``: the state summary and the charter (moved from ``Org.whoami``)."""

from __future__ import annotations

from ..agents import AgentDirectory, CharterReader
from .api import StateSummarizer, Whoami


class TextWhoami(Whoami):
    def __init__(self, agents: AgentDirectory, charters: CharterReader, summary: StateSummarizer) -> None:
        self._agents = agents
        self._charters = charters
        self._summary = summary

    def whoami(self, addr: str) -> str:
        raise NotImplementedError("red: C-prompts")
