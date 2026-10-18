"""``CharterToolNaming`` reads one charter, and none for root."""

from __future__ import annotations

from orgmcp.access import ToolNaming
from orgmcp.access._naming import CharterToolNaming
from orgmcp.agents import CharterReader
from orgmcp.agents.testing import MemoryAgents
from orgmcp.kernel import JsonObject


class RecordingCharters(CharterReader):
    def __init__(self, agents: MemoryAgents) -> None:
        self._agents = agents
        self.asked: list[str] = []

    def charter(self, addr: str) -> tuple[JsonObject, str]:
        self.asked.append(addr)
        return self._agents.charter(addr)

    def memory(self, addr: str) -> str:
        return self._agents.memory(addr)


def test_it_is_a_tool_naming() -> None:
    assert isinstance(CharterToolNaming(MemoryAgents()), ToolNaming)


def test_root_is_answered_without_reading_a_charter() -> None:
    charters = RecordingCharters(MemoryAgents())
    assert CharterToolNaming(charters).tool_names("root") == {"read": "read", "write": "write"}
    assert charters.asked == []


def test_the_charter_asked_for_is_the_one_of_the_address_as_given() -> None:
    agents = MemoryAgents()
    agents.put("dev/AGENT.md", "---\nrole: R\ntools: [read]\n---\nb\n")
    charters = RecordingCharters(agents)
    assert CharterToolNaming(charters).tool_names("dev") == {"read": "org_read", "write": "write"}
    assert charters.asked == ["dev"]
