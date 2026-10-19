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
        a = self._agents.require(addr)
        _, charter = self._charters.charter(a)
        return f"{self._summary.state_summary(a)}\n\n## Charter\n{charter or '(root has no charter)'}"
